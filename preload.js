const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('minimize'),
  maximize: () => ipcRenderer.send('maximize'),
  close: () => ipcRenderer.send('close'),
  onWindowStateChange: (callback) => ipcRenderer.on('window-state', (_, isMaximized) => callback(isMaximized)),
});