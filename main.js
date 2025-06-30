const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const directoryPath = path.join(__dirname, 'src', 'assets', 'directory.json');
const RECENTLY_VIEWED_PATH = path.join(__dirname, 'src', 'assets', 'recently-viewed.json');

let mainWindow;

app.whenReady().then(() => {
  mainWindow = new BrowserWindow({
    width: 1300,
    height: 800,
    minWidth: 800,
    minHeight: 800,
    frame: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false, // best for security
    },
  });

  mainWindow.loadURL('http://localhost:5173');
  mainWindow.webContents.openDevTools();

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

  ipcMain.handle('get-symphony-files', async (event, directoryPath) => {
    let files = null
    try { files = fs.readdirSync(directoryPath); } catch(error) { return 'not a valid dir' }
    
    const symphonyFiles = files.filter(file => path.extname(file) === '.symphony');
    return symphonyFiles || 'no files';
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

  ipcMain.handle('copy-file', async (event, src, dest) => {
    return new Promise((resolve, reject) => {
      fs.copyFile(src, dest, (err) => {
        if (err) reject(err);
        else resolve('success');
      });
    });
  });

  ipcMain.handle('file-exists', async (event, filePath) => {
    try {
      return fs.existsSync(filePath);
    } catch (err) {
      return false;
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

  // Add handler for get-directory
  ipcMain.handle('get-directory', async () => {
    try {
      if (!fs.existsSync(directoryPath)) {
        const defaultDirectory = {
          "Projects": [],
          "Exports": [],
          "Symphony Auto-Save": []
        };
        fs.writeFileSync(directoryPath, JSON.stringify(defaultDirectory, null, 2));
        return defaultDirectory;
      } else {
        return JSON.parse(fs.readFileSync(directoryPath, 'utf-8'));
      }
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('run-python-script', async (event, argsArray) => {
    console.log('Instantiating new .symphony file...');
    // Add to recently viewed
    if (argsArray[0] === 'open') {
      try {
        let recent = [];
        if (fs.existsSync(RECENTLY_VIEWED_PATH)) {
          recent = JSON.parse(fs.readFileSync(RECENTLY_VIEWED_PATH, 'utf-8'));
        }
        // Compose new entry
        const fileName = argsArray[1] || '';
        const fileType = path.extname(fileName).replace('.', '').toLowerCase();
        const entry = {
          type: fileType,
          name: fileName,
          fileLocation: argsArray[2] || ''
        };
        // Remove any existing entry with same name and location
        recent = recent.filter(r => !(r.name === entry.name && r.fileLocation === entry.fileLocation));
        // Add to top
        recent.unshift(entry);
        // Limit to 20 entries
        if (recent.length > 20) recent = recent.slice(0, 20);
        fs.writeFileSync(RECENTLY_VIEWED_PATH, JSON.stringify(recent, null, 2), 'utf-8');
      } catch (e) {
        console.error('Failed to update recently viewed:', e);
      }
    }
    
    return new Promise((resolve, reject) => {
      const scriptPath = path.join(__dirname, 'inner', 'src', 'main.py'); // Adjust if needed
      const pythonProcess = spawn('python', [scriptPath, ...argsArray]);

      let output = '';
      let errorOutput = '';

      pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          resolve({ success: true, output });
        } else {
          reject({ success: false, error: errorOutput || `Process exited with code ${code}` });
        }
      });
    });
  });

  ipcMain.handle('rename-file', async (event, { filePath, newName }) => {
    try {
      const dir = path.dirname(filePath);
      const newFilePath = path.join(dir, newName + '.symphony');
      fs.renameSync(filePath, newFilePath);
      return { success: true, newFilePath };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  // Add metadata read/write handlers for .symphony files using a sidecar .json file
  ipcMain.handle('get-metadata', async (event, filePath) => {
    try {
      // Use a .json file next to the .symphony file
      const metaPath = filePath.replace(/\.symphony$/, '.json');
      if (fs.existsSync(metaPath)) {
        return JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
      } else {
        return {};
      }
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('set-metadata', async (event, { filePath, metadata }) => {
    try {
      const metaPath = filePath.replace(/\.symphony$/, '.json');
      fs.writeFileSync(metaPath, JSON.stringify(metadata, null, 2), 'utf-8');
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  ipcMain.handle('delete-file', async (event, filePath) => {
    try {
      fs.unlinkSync(filePath);
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  ipcMain.handle('get-recently-viewed', async () => {
    try {
      if (!fs.existsSync(RECENTLY_VIEWED_PATH)) {
        fs.writeFileSync(RECENTLY_VIEWED_PATH, '[]', 'utf-8');
      }
      const data = fs.readFileSync(RECENTLY_VIEWED_PATH, 'utf-8');
      return JSON.parse(data);
    } catch (err) {
      return [];
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
