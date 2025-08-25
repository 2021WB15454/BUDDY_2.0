const { contextBridge, ipcRenderer } = require('electron');

console.log('=== PRELOAD SCRIPT STARTING ===');

try {
  console.log('contextBridge available:', typeof contextBridge);
  console.log('ipcRenderer available:', typeof ipcRenderer);
  
  // Expose electronAPI
  contextBridge.exposeInMainWorld('electronAPI', {
    // Backend communication
    backendRequest: (method, endpoint, data) => {
      console.log('PreloadScript: backendRequest called', method, endpoint, data);
      return ipcRenderer.invoke('backend:request', { method, endpoint, data });
    },

    // Voice control
    startListening: () => ipcRenderer.invoke('voice:start-listening'),
    stopListening: () => ipcRenderer.invoke('voice:stop-listening'),

    // Settings
    getSettings: () => ipcRenderer.invoke('settings:get'),
    setSettings: (settings) => ipcRenderer.invoke('settings:set', settings),

    // File operations
    openFileDialog: () => ipcRenderer.invoke('dialog:open-file'),

    // App information
    getAppVersion: () => ipcRenderer.invoke('app:get-version'),
    showAbout: () => ipcRenderer.invoke('app:show-about'),

    // Event listeners
    onShowPreferences: (callback) => {
      ipcRenderer.on('show-preferences', callback);
      return () => ipcRenderer.removeListener('show-preferences', callback);
    },

    // Utility
    platform: process.platform,
    isDev: process.argv.includes('--dev'),
    
    // IPC invoke function (generic)
    invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args)
  });

  console.log('electronAPI exposed successfully');

  // Expose buddy API - calling ipcRenderer directly instead of window.electronAPI
  contextBridge.exposeInMainWorld('buddy', {
    // Chat API
    sendMessage: async (message, context = {}) => {
      return ipcRenderer.invoke('backend:request', { 
        method: 'POST', 
        endpoint: '/chat', 
        data: { message, context }
      });
    },

    // Voice API
    voice: {
      startListening: () => ipcRenderer.invoke('voice:start-listening'),
      stopListening: () => ipcRenderer.invoke('voice:stop-listening')
    },

    // Skills API
    getSkills: () => ipcRenderer.invoke('backend:request', { 
      method: 'GET', 
      endpoint: '/skills' 
    }),
    getSkillSchema: (skillName) => ipcRenderer.invoke('backend:request', { 
      method: 'GET', 
      endpoint: `/skills/${skillName}/schema` 
    }),

    // Status API
    getStatus: () => ipcRenderer.invoke('backend:request', { 
      method: 'GET', 
      endpoint: '/health' 
    }),
    getMetrics: () => ipcRenderer.invoke('backend:request', { 
      method: 'GET', 
      endpoint: '/system/stats' 
    }),

    // Settings API
    settings: {
      get: () => ipcRenderer.invoke('settings:get'),
      set: (settings) => ipcRenderer.invoke('settings:set', settings)
    },

    // App API
    app: {
      getVersion: () => ipcRenderer.invoke('app:get-version'),
      showAbout: () => ipcRenderer.invoke('app:show-about'),
      platform: process.platform,
      isDev: process.argv.includes('--dev')
    }
  });

  console.log('buddy API exposed successfully');

} catch (error) {
  console.error('Error in preload script:', error);
}

console.log('=== PRELOAD SCRIPT LOADED ===');
