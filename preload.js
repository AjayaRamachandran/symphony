const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('minimize'),
  maximize: () => ipcRenderer.send('maximize'),
  close: () => ipcRenderer.send('close'),
  onWindowStateChange: (callback) => ipcRenderer.on('window-state', (_, isMaximized) => callback(isMaximized)),
  openDirectory: () => ipcRenderer.invoke('dialog:openDirectory'),
  toggleDevTools: () => ipcRenderer.send('toggle-devtools'),
  saveDirectory: (data) => ipcRenderer.invoke('save-directory', data),
  getDirectory: () => ipcRenderer.invoke('get-directory'),
  getSymphonyFiles: (directoryPath) => ipcRenderer.invoke('get-symphony-files', directoryPath),
  runPythonScript: (args) => ipcRenderer.invoke('run-python-script', args),
  renameFile: (filePath, newName) => ipcRenderer.invoke('rename-file', { filePath, newName }),
  getMetadata: (filePath) => ipcRenderer.invoke('get-metadata', filePath),
  setMetadata: (filePath, metadata) => ipcRenderer.invoke('set-metadata', { filePath, metadata })
});