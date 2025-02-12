const { app, BrowserWindow } = require('electron');
const path = require('path');

let mainWindow;

app.on('ready', () => {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    frame: false,
    webPreferences: {
      nodeIntegration: true,
    },
  });

  // During development, load Vite's dev server URL
  mainWindow.loadURL('http://localhost:5173');
  
  mainWindow.on('closed', () => (mainWindow = null));
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
