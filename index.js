const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const axios = require('axios');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let backendProcess = null;
const BACKEND_BASE_URL = 'http://localhost:8082';

async function waitForBackend(maxAttempts = 30) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      await axios.get(`${BACKEND_BASE_URL}/health`, { timeout: 1500 });
      return true;
    } catch (e) {
      await new Promise(r => setTimeout(r, 1000));
    }
  }
  return false;
}

function startBackend() {
  // Try to spawn the simple backend if it's not already running
  try {
    const repoRoot = __dirname;
    const backendScript = path.join(repoRoot, 'simple_backend.py');
    const haveBackend = fs.existsSync(backendScript);
    if (!haveBackend) {
      console.warn('simple_backend.py not found; skipping auto-start');
      return;
    }

    // Detect Python command reliably
    const { spawnSync } = require('child_process');
    const isWin = process.platform === 'win32';
    const testCmd = (cmd, args) => {
      try {
        const res = spawnSync(cmd, args, { stdio: 'ignore' });
        return res.status === 0;
      } catch {
        return false;
      }
    };
    let pyCmd = null; let pyArgs = [];
    if (isWin) {
      if (testCmd('where', ['py'])) { pyCmd = 'py'; pyArgs = ['-3']; }
      else if (testCmd('where', ['python'])) { pyCmd = 'python'; pyArgs = []; }
      else if (testCmd('where', ['python3'])) { pyCmd = 'python3'; pyArgs = []; }
    } else {
      if (testCmd('which', ['python3'])) { pyCmd = 'python3'; pyArgs = []; }
      else if (testCmd('which', ['python'])) { pyCmd = 'python'; pyArgs = []; }
    }

    if (!pyCmd) {
      console.warn('No Python interpreter found on PATH; please start simple_backend.py manually.');
      return;
    }

    const args = [...pyArgs, backendScript];
  const env = { ...process.env, BUDDY_DEV: '1', BUDDY_DEBUG: process.env.BUDDY_DEBUG || '1' };
  backendProcess = spawn(pyCmd, args, { cwd: repoRoot, env });
    backendProcess.stdout.on('data', d => console.log('[backend]', d.toString().trim()));
    backendProcess.stderr.on('data', d => console.warn('[backend:err]', d.toString().trim()));
    backendProcess.on('error', (err) => {
      console.warn(`Backend spawn error with ${pyCmd}:`, err.message);
    });
    backendProcess.on('exit', (code, signal) => {
      console.log('Backend exited:', { code, signal });
    });
    console.log('Backend started with command:', pyCmd, pyArgs.join(' '));
  } catch (err) {
    console.error('Failed to start backend:', err.message);
  }
}

function createWindow() {
  // Debug: Log paths
  console.log('__dirname:', __dirname);
  console.log('process.cwd():', process.cwd());
  // Prefer src/preload.js during development/runtime if build/preload.js doesn't exist
  let preloadPath = path.join(__dirname, 'apps', 'desktop', 'build', 'preload.js');
  if (!fs.existsSync(preloadPath)) {
    const srcPreload = path.join(__dirname, 'apps', 'desktop', 'src', 'preload.js');
    if (fs.existsSync(srcPreload)) {
      preloadPath = srcPreload;
    }
  }
  console.log('Preload script path:', preloadPath);
  console.log('Preload script exists:', fs.existsSync(preloadPath));
  
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: preloadPath,
      // Enable media permissions for microphone access
      webSecurity: true,
      allowRunningInsecureContent: false,
      experimentalFeatures: false
    },
    icon: path.join(__dirname, 'assets/icon.png'), // Optional: Add an icon
    show: false // Don't show until ready
  });

  // Load the HTML file
  mainWindow.loadFile('apps/desktop/build/index.html');

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    // Always open DevTools to debug connection issues
    mainWindow.webContents.openDevTools();
  });
  
  // After content loads, inject minimal CSS for a compact status bar without altering layout
  mainWindow.webContents.on('did-finish-load', () => {
    const injectedCss = `
      /* Compact status bar */
      .status-bar { margin-top: auto !important; padding: 8px 12px !important; font-size: 12px !important; gap: 12px !important; }
      .status-item { gap: 6px !important; }
      /* Sidebar responsiveness */
      @media (max-width: 1024px) { .app-sidebar { width: 220px !important; } }
      @media (max-width: 768px) {
        .status-bar { position: fixed !important; bottom: 0; left: 0; right: 0; z-index: 9999; }
      }
      @media (max-width: 480px) {
        .status-bar { padding: 6px 10px !important; font-size: 11px !important; gap: 8px !important; }
      }
    `;
    try { mainWindow.webContents.insertCSS(injectedCss); } catch (e) { console.warn('Failed to inject CSS:', e.message); }
  });

  // Open DevTools in development
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// This method will be called when Electron has finished initialization
app.whenReady().then(async () => {
  // Start backend (best-effort) and wait briefly for readiness
  startBackend();
  const ready = await waitForBackend(8);
  if (!ready) {
    console.warn('Backend not ready yet; UI may show Connecting...');
  }
  createWindow();
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
  // On macOS, keep the app running even when all windows are closed
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  // On macOS, re-create a window when the dock icon is clicked
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', () => {
  if (backendProcess) {
    try { backendProcess.kill('SIGTERM'); } catch (e) { /* ignore */ }
  }
});

ipcMain.handle('backend:restart', async () => {
  if (backendProcess) {
    try { backendProcess.kill('SIGTERM'); } catch (e) { /* ignore */ }
    backendProcess = null;
  }
  startBackend();
  const ready = await waitForBackend(10);
  return { success: ready };
});

// Handle IPC messages (for future use with voice interface, etc.)
ipcMain.handle('app-version', () => {
  return app.getVersion();
});

ipcMain.handle('minimize-window', () => {
  if (mainWindow) {
    mainWindow.minimize();
  }
});

ipcMain.handle('maximize-window', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.handle('close-window', () => {
  if (mainWindow) {
    mainWindow.close();
  }
});

// Backend communication handlers

ipcMain.handle('backend:request', async (event, { method, endpoint, data }) => {
  console.log(`Backend request: ${method} ${endpoint}`, data);
  try {
    const url = `${BACKEND_BASE_URL}${endpoint}`;
    console.log(`Making request to: ${url}`);
    
    let response;
    switch (method.toUpperCase()) {
      case 'GET':
        response = await axios.get(url);
        break;
      case 'POST':
        response = await axios.post(url, data);
        break;
      case 'PUT':
        response = await axios.put(url, data);
        break;
      case 'DELETE':
        response = await axios.delete(url);
        break;
      default:
        throw new Error(`Unsupported HTTP method: ${method}`);
    }
    
    console.log(`Backend response:`, response.data);
    return {
      success: true,
      data: response.data,
      status: response.status
    };
  } catch (error) {
    console.error('Backend request failed:', error.message);
    return {
      success: false,
      error: error.message,
      status: error.response?.status || 500
    };
  }
});

// Settings handlers (placeholder - in a real app these would persist to disk)
let appSettings = {};

ipcMain.handle('settings:get', () => {
  return { success: true, data: appSettings };
});

ipcMain.handle('settings:set', (event, settings) => {
  appSettings = { ...appSettings, ...settings };
  return { success: true, data: appSettings };
});

// Voice handlers (placeholder)
ipcMain.handle('voice:start-listening', async () => {
  console.log('Voice listening started');
  try {
    // Check if microphone access is available
    // Note: In Electron, we need to handle microphone permissions
    // For now, return success and let the renderer handle Web Speech API
    return { 
      success: true, 
      message: 'Voice listening started - using Web Speech API in renderer',
      method: 'web-speech-api' 
    };
  } catch (error) {
    console.error('Voice start error:', error);
    return { 
      success: false, 
      error: error.message,
      message: 'Failed to start voice recognition'
    };
  }
});

ipcMain.handle('voice:stop-listening', async () => {
  console.log('Voice listening stopped');
  try {
    return { 
      success: true, 
      message: 'Voice listening stopped',
      method: 'web-speech-api'
    };
  } catch (error) {
    console.error('Voice stop error:', error);
    return { 
      success: false, 
      error: error.message 
    };
  }
});

// Check microphone permissions
ipcMain.handle('voice:check-permissions', async () => {
  try {
    // In Electron, we need to check if we have microphone permissions
    // This is a simplified check - in production you'd want more robust permission handling
    return {
      success: true,
      hasPermission: true,
      message: 'Microphone permissions available'
    };
  } catch (error) {
    return {
      success: false,
      hasPermission: false,
      error: error.message
    };
  }
});

// App info handlers
ipcMain.handle('app:get-version', () => {
  return app.getVersion();
});

ipcMain.handle('app:show-about', () => {
  console.log('About dialog requested');
  return { success: true };
});

// File dialog handler
ipcMain.handle('dialog:open-file', async () => {
  const { dialog } = require('electron');
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  return result;
});

// System stats handler
ipcMain.handle('get-system-stats', () => {
  const os = require('os');
  
  return {
    success: true,
    data: {
      platform: os.platform(),
      architecture: os.arch(),
      cpus: os.cpus().length,
      totalMemory: Math.round(os.totalmem() / 1024 / 1024 / 1024) + ' GB',
      freeMemory: Math.round(os.freemem() / 1024 / 1024 / 1024) + ' GB',
      uptime: Math.round(os.uptime() / 3600) + ' hours',
      loadAverage: os.loadavg(),
      nodeVersion: process.version,
      electronVersion: process.versions.electron
    }
  };
});

// Skills handler - forwards to backend
ipcMain.handle('get-skills', async () => {
  try {
    const url = `${BACKEND_BASE_URL}/skills`;
    console.log(`Getting skills from: ${url}`);
    const response = await axios.get(url);
    console.log('Skills response:', response.data);
    return {
      success: true,
      data: response.data,
      status: response.status
    };
  } catch (error) {
    console.error('Failed to get skills:', error.message);
    return {
      success: false,
      error: error.message,
      status: error.response?.status || 500
    };
  }
});

// Settings handler - forwards to backend or uses local storage
ipcMain.handle('get-settings', async () => {
  try {
    // For now, return the local app settings
    // In a full implementation, this might also fetch from backend
    return {
      success: true,
      data: appSettings
    };
  } catch (error) {
    console.error('Failed to get settings:', error.message);
    return {
      success: false,
      error: error.message
    };
  }
});
