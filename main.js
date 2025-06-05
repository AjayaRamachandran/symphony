const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let mainWindow;

app.whenReady().then(() => {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 700,
    minHeight: 800,
    frame: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false, // best for security
    },
  });

  mainWindow.loadURL('http://localhost:5173');
  // mainWindow.webContents.openDevTools();

// Respond to frontend button events
  ipcMain.on('minimize', () => mainWindow.minimize());
  ipcMain.on('maximize', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });
  ipcMain.on('close', () => mainWindow.close());

  mainWindow.on('maximize', () => {
    mainWindow.webContents.send('window-state', true);
  });

  mainWindow.on('unmaximize', () => {
    mainWindow.webContents.send('window-state', false);
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
