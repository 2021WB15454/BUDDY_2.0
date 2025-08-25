const { app, BrowserWindow, ipcMain, Menu, shell, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const log = require('electron-log');

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = 'debug';

class BuddyApp {
  constructor() {
    this.mainWindow = null;
    this.backendProcess = null;
    this.isDev = process.argv.includes('--dev');
    this.backendPort = 8082;
    this.backendUrl = `http://localhost:${this.backendPort}`;
    
    log.info('BUDDY Desktop starting...', { isDev: this.isDev });
  }

  async initialize() {
    // Set up app event handlers
    app.whenReady().then(() => this.onReady());
    app.on('window-all-closed', () => this.onWindowAllClosed());
    app.on('activate', () => this.onActivate());
    app.on('before-quit', () => this.onBeforeQuit());

    // Set up IPC handlers
    this.setupIpcHandlers();
  }

  async onReady() {
    try {
      // Start backend if not in dev mode
      if (!this.isDev) {
        await this.startBackend();
      }

      // Create main window
      await this.createMainWindow();

      // Set up menu
      this.setupMenu();

      log.info('BUDDY Desktop ready');
    } catch (error) {
      log.error('Failed to initialize app:', error);
      app.quit();
    }
  }

  async startBackend() {
    return new Promise((resolve, reject) => {
      try {
        const pythonPath = this.getPythonPath();
        // Prefer simple_backend.py at repo root during development-like usage without --dev
        const repoRoot = path.join(__dirname, '..', '..');
        const simpleBackend = path.join(repoRoot, 'simple_backend.py');
        const hasSimpleBackend = fs.existsSync(simpleBackend);
        const backendCwd = hasSimpleBackend ? repoRoot : this.getBackendPath();
        const spawnArgs = hasSimpleBackend
          ? [simpleBackend]
          : ['-m', 'buddy.main', '--port', this.backendPort.toString(), '--host', 'localhost'];
        
        log.info('Starting backend:', { pythonPath, backendCwd, hasSimpleBackend, spawnArgs: spawnArgs.join(' ') });

        // Start Python backend
        this.backendProcess = spawn(pythonPath, spawnArgs, {
          cwd: backendCwd,
          env: { ...process.env, PYTHONPATH: backendCwd }
        });

        this.backendProcess.stdout.on('data', (data) => {
          log.info('Backend stdout:', data.toString());
        });

        this.backendProcess.stderr.on('data', (data) => {
          log.warn('Backend stderr:', data.toString());
        });

        this.backendProcess.on('error', (error) => {
          log.error('Backend process error:', error);
          reject(error);
        });

        this.backendProcess.on('exit', (code, signal) => {
          log.info('Backend process exited:', { code, signal });
          if (code !== 0 && code !== null) {
            reject(new Error(`Backend exited with code ${code}`));
          }
        });

        // Wait for backend to be ready
        this.waitForBackend().then(resolve).catch(reject);

      } catch (error) {
        log.error('Failed to start backend:', error);
        reject(error);
      }
    });
  }

  async waitForBackend(maxAttempts = 30) {
    const axios = require('axios');
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
  await axios.get(`${this.backendUrl}/health`, { timeout: 2000 });
        log.info('Backend is ready');
        return;
      } catch (error) {
        log.debug(`Backend not ready, attempt ${attempt}/${maxAttempts}`);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    throw new Error('Backend failed to start within timeout');
  }

  getBackendPath() {
    if (this.isDev) {
      return path.join(__dirname, '../../packages/core');
    } else {
      return path.join(process.resourcesPath, 'backend');
    }
  }

  getPythonPath() {
    // Try to find Python executable
    const candidates = ['python', 'python3', 'py'];
    
    if (process.platform === 'win32') {
      candidates.unshift('py.exe', 'python.exe');
    }
    
    // In production, we might bundle Python or use a specific path
    return candidates[0]; // Simplified for now
  }

  async createMainWindow() {
    // Create the browser window
    this.mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      minWidth: 800,
      minHeight: 600,
      show: false,
      icon: this.getIconPath(),
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: this.isDev
          ? path.join(__dirname, 'preload.js')
          : path.join(__dirname, '../build/preload.js')
      }
    });

    // Load the app
    if (this.isDev) {
      // In development, load the React dev server for live reload
      await this.mainWindow.loadURL('http://localhost:3000');
    } else {
      // In production, load from built files
      await this.mainWindow.loadFile('build/index.html');
    }

    // Show window when ready
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow.show();
      
      if (this.isDev) {
        this.mainWindow.webContents.openDevTools();
      }
    });

    // Handle window closed
    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // Log load failures to help diagnose dev server/build issues
    this.mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
      log.error('Renderer failed to load:', { errorCode, errorDescription, validatedURL });
    });

    // Handle external links
    this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
      shell.openExternal(url);
      return { action: 'deny' };
    });
  }

  getIconPath() {
    const iconName = {
      win32: 'icon.ico',
      darwin: 'icon.icns',
      linux: 'icon.png'
    }[process.platform] || 'icon.png';
    
    return path.join(__dirname, 'assets', iconName);
  }

  setupMenu() {
    const template = [
      {
        label: 'BUDDY',
        submenu: [
          {
            label: 'About BUDDY',
            click: () => this.showAbout()
          },
          { type: 'separator' },
          {
            label: 'Preferences...',
            accelerator: 'CmdOrCtrl+,',
            click: () => this.showPreferences()
          },
          { type: 'separator' },
          {
            label: 'Quit',
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
            click: () => app.quit()
          }
        ]
      },
      {
        label: 'Edit',
        submenu: [
          { role: 'undo' },
          { role: 'redo' },
          { type: 'separator' },
          { role: 'cut' },
          { role: 'copy' },
          { role: 'paste' },
          { role: 'selectall' }
        ]
      },
      {
        label: 'View',
        submenu: [
          { role: 'reload' },
          { role: 'forceReload' },
          { role: 'toggleDevTools' },
          { type: 'separator' },
          { role: 'resetZoom' },
          { role: 'zoomIn' },
          { role: 'zoomOut' },
          { type: 'separator' },
          { role: 'togglefullscreen' }
        ]
      },
      {
        label: 'Window',
        submenu: [
          { role: 'minimize' },
          { role: 'close' }
        ]
      },
      {
        label: 'Help',
        submenu: [
          {
            label: 'Documentation',
            click: () => shell.openExternal('https://github.com/buddy-ai/buddy')
          },
          {
            label: 'Report Issue',
            click: () => shell.openExternal('https://github.com/buddy-ai/buddy/issues')
          }
        ]
      }
    ];

    // macOS specific menu adjustments
    if (process.platform === 'darwin') {
      template[0].submenu.unshift(
        { role: 'about' },
        { type: 'separator' }
      );
      
      template[4].submenu = [
        { role: 'close' },
        { role: 'minimize' },
        { role: 'zoom' },
        { type: 'separator' },
        { role: 'front' }
      ];
    }

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  setupIpcHandlers() {
    // Backend communication
    ipcMain.handle('backend:request', async (event, { method, endpoint, data }) => {
      try {
        const axios = require('axios');
        const response = await axios({
          method,
          url: `${this.backendUrl}${endpoint}`,
          data,
          timeout: 30000
        });
        return { success: true, data: response.data };
      } catch (error) {
        log.error('Backend request failed:', error);
        return { 
          success: false, 
          error: error.message,
          details: error.response?.data 
        };
      }
    });

    // Voice control
    ipcMain.handle('voice:start-listening', async () => {
      // Trigger voice listening
      return this.sendBackendRequest('POST', '/voice/listen');
    });

    ipcMain.handle('voice:stop-listening', async () => {
      // Stop voice listening
      return this.sendBackendRequest('POST', '/voice/stop');
    });

    // Settings
    ipcMain.handle('settings:get', async () => {
      return this.sendBackendRequest('GET', '/settings');
    });

    ipcMain.handle('settings:set', async (event, settings) => {
      return this.sendBackendRequest('POST', '/settings', settings);
    });

    // File operations
    ipcMain.handle('dialog:open-file', async () => {
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openFile'],
        filters: [
          { name: 'All Files', extensions: ['*'] }
        ]
      });
      return result;
    });

    // App control
    ipcMain.handle('app:get-version', () => {
      return app.getVersion();
    });

    ipcMain.handle('app:show-about', () => {
      this.showAbout();
    });
  }

  async sendBackendRequest(method, endpoint, data = null) {
    try {
      const axios = require('axios');
      const response = await axios({
        method,
        url: `${this.backendUrl}${endpoint}`,
        data,
        timeout: 10000
      });
      return { success: true, data: response.data };
    } catch (error) {
      log.error('Backend request failed:', error);
      return { 
        success: false, 
        error: error.message 
      };
    }
  }

  showAbout() {
    dialog.showMessageBox(this.mainWindow, {
      type: 'info',
      title: 'About BUDDY',
      message: 'BUDDY - Your JARVIS-style Personal AI Assistant',
      detail: `Version: ${app.getVersion()}\n\nA privacy-first, voice+text, multi-device assistant that learns you, syncs across your ecosystem, and self-optimizes.`
    });
  }

  showPreferences() {
    // Send message to renderer to show preferences
    if (this.mainWindow) {
      this.mainWindow.webContents.send('show-preferences');
    }
  }

  onWindowAllClosed() {
    if (process.platform !== 'darwin') {
      app.quit();
    }
  }

  onActivate() {
    if (BrowserWindow.getAllWindows().length === 0) {
      this.createMainWindow();
    }
  }

  onBeforeQuit() {
    log.info('App is quitting, cleaning up...');
    
    if (this.backendProcess) {
      log.info('Stopping backend process...');
      this.backendProcess.kill('SIGTERM');
      
      // Force kill after 5 seconds
      setTimeout(() => {
        if (this.backendProcess && !this.backendProcess.killed) {
          log.warn('Force killing backend process');
          this.backendProcess.kill('SIGKILL');
        }
      }, 5000);
    }
  }
}

// Create and initialize the app
const buddyApp = new BuddyApp();
buddyApp.initialize().catch((error) => {
  log.error('Failed to initialize app:', error);
  app.quit();
});

// Export for testing
module.exports = BuddyApp;
