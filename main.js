const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const directoryPath = path.join(__dirname, 'src', 'assets', 'directory.json');

let mainWindow;

app.whenReady().then(() => {
  mainWindow = new BrowserWindow({
    width: 1265,
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
  //mainWindow.webContents.openDevTools();

  // Respond to frontend window control events
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

  ipcMain.on('toggle-devtools', () => {
    if (mainWindow.webContents.isDevToolsOpened()) {
      mainWindow.webContents.closeDevTools();
    } else {
      mainWindow.webContents.openDevTools();
    }
  });

  ipcMain.handle('save-directory', async (event, { destination, projectName, sourceLocation }) => {
    try {
      // Read current directory.json
      const data = fs.readFileSync(directoryPath, 'utf-8');
      const directory = JSON.parse(data);

      // Add new entry
      if (!directory[destination]) directory[destination] = [];
      directory[destination].push({ [projectName]: sourceLocation });

      // Write back to file
      fs.writeFileSync(directoryPath, JSON.stringify(directory, null, 2), 'utf-8');
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  ipcMain.handle('dialog:openDirectory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory']
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    } else {
      return result.filePaths[0];
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
