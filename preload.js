const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Window Controls
  platform: process.platform,
  minimize: () => ipcRenderer.send('minimize'),
  maximize: () => ipcRenderer.send('maximize'),
  close: () => ipcRenderer.send('close'),
  onWindowStateChange: (callback) => ipcRenderer.on('window-state', (_, isMaximized) => callback(isMaximized)),
  toggleDevTools: () => ipcRenderer.send('toggle-devtools'),

  // File Operations
  startFileDrag: (filePath) => ipcRenderer.send('start-drag', filePath),
  openExternal: (url) => ipcRenderer.send('open-external', url),
  openFileLocation: (filePath) => ipcRenderer.invoke('open-file-location', filePath),
  fileExists: (filePath) => ipcRenderer.invoke('file-exists', filePath),
  deleteFile: (filePath) => ipcRenderer.invoke('delete-file', filePath),
  renameFile: (filePath, newName) => ipcRenderer.invoke('rename-file', { filePath, newName }),
  copyFile: (src, dest) => ipcRenderer.invoke('copy-file', src, dest),
  moveFileRaw: (fileBuffer, fileName, destinationDir) => ipcRenderer.invoke('move-file-raw', fileBuffer, fileName, destinationDir),

  // Directory Operations
  openDirectory: () => ipcRenderer.invoke('dialog:openDirectory'),
  saveDirectory: (data) => ipcRenderer.invoke('save-directory', data),
  getDirectory: () => ipcRenderer.invoke('get-directory'),
  removeDirectory: (section, dirName) => ipcRenderer.invoke('remove-directory', section, dirName),
  getSectionForPath: (filePath) => ipcRenderer.invoke('get-section-for-path', filePath),
  checkIfExists: (data) => ipcRenderer.invoke('check-if-exists', data),

  // Metadata Operations
  getMetadata: (filePath) => ipcRenderer.invoke('get-metadata', filePath),
  setMetadata: (filePath, metadata) => ipcRenderer.invoke('set-metadata', { filePath, metadata }),

  // Recently Viewed
  getRecentlyViewed: () => ipcRenderer.invoke('get-recently-viewed'),
  recentlyViewedDelete: (fileName) => ipcRenderer.invoke('recently-viewed-delete', fileName),

  // Starred Files
  getStars: () => ipcRenderer.invoke('get-stars'),
  addStar: (filePath) => ipcRenderer.invoke('add-star', filePath),
  removeStar: (filePath) => ipcRenderer.invoke('remove-star', filePath),

  // User Settings
  getUserSettings: () => ipcRenderer.invoke('get-user-settings'),
  updateUserSettings: (key, value) => ipcRenderer.invoke('update-user-settings', key, value),

  // Symphony File Commands
  getSymphonyFiles: (directoryPath) => ipcRenderer.invoke('get-symphony-files', directoryPath),
  openNativeApp: (filePath) => ipcRenderer.invoke('open-native-app', filePath),

  // Editor Program
  openEditorProgram: () => ipcRenderer.invoke('open-editor-program'),
  doProcessCommand: (event, symphonyFilePath, command, extraArgs) => ipcRenderer.invoke('do-process-command', event, symphonyFilePath, command, extraArgs),
});