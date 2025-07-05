const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const directoryPath = path.join(__dirname, 'src', 'assets', 'directory.json');
const RECENTLY_VIEWED_PATH = path.join(__dirname, 'src', 'assets', 'recently-viewed.json');
const RETRIEVE_OUTPUT_PATH = path.join(__dirname, 'inner', 'src', 'response.json');
const STARRED_PATH = path.join(__dirname, 'src', 'assets', 'starred.json');

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
      const data = fs.readFileSync(directoryPath, 'utf-8');
      const directory = JSON.parse(data);

      if (!directory[destination]) {
        directory[destination] = [];
      }

      const nameExists = directory[destination].some(entry => entry[projectName]);
      if (nameExists) {
        return {
          success: false,
          error: `Project name "${projectName}" already exists in "${destination}".`,
          errorType: 409,
        };
      }

      const locationExists = directory[destination].some(entry =>
        Object.values(entry).includes(sourceLocation)
      );
      if (locationExists) {
        return {
          success: false,
          error: `Source location "${sourceLocation}" already exists in "${destination}".`,
          errorType: 409,
        };
      }

      directory[destination].push({ [projectName]: sourceLocation });
      fs.writeFileSync(directoryPath, JSON.stringify(directory, null, 2), 'utf-8');

      return { success: true };
    } catch (err) {
      return {
        success: false,
        error: err.message,
        errorType: 400
      };
    }
  });

  ipcMain.handle('check-if-exists', async (event, { destination, projectName, sourceLocation }) => {
    try {
      const data = fs.readFileSync(directoryPath, 'utf-8');
      const directory = JSON.parse(data);
      console.log(JSON.stringify(directory))

      if (!directory[destination]) {
        return { success: true };
      }
      const entries = directory[destination];

      const nameCount = entries.filter(entry => entry[projectName] !== undefined).length;
      const locationCount = entries.filter(entry =>
        Object.values(entry).includes(sourceLocation)
      ).length;

      const isDuplicate = nameCount > 0 || locationCount > 0;
      console.log(isDuplicate);

      return {
        success: isDuplicate,
      };

    } catch (err) {
      return {
        success: false
      };
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

  // Add handler for get-section-for-path
  ipcMain.handle('get-section-for-path', async (event, filePath) => {
    try {
      if (!fs.existsSync(directoryPath)) {
        return { error: 'Directory data not found.' };
      }

      const directoryData = JSON.parse(fs.readFileSync(directoryPath, 'utf-8'));

      for (const [section, entries] of Object.entries(directoryData)) {
        for (const entry of entries) {
          const folderPath = Object.values(entry)[0];
          if (folderPath === filePath) {
            return { section };
          }
        }
      }

      return { section: null, message: 'Path not found in any section.' };
    } catch (err) {
      return { error: err.message };
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
    //console.log('Instantiating new .symphony file...');
    console.log(JSON.stringify(argsArray));
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
    const dir = path.dirname(filePath);
    let baseName = newName;
    let ext = path.extname(newName);
    if (!ext) ext = '.symphony';
    //baseName = (ext === '.symphony') ? newName.slice(0, -9) : newName;
    console.log(`main.js::ipcMain.handle('rename-file') - baseName: ${baseName}`);
    let candidate = baseName + ext;
    let counter = 1;
    const files = fs.readdirSync(dir);
    console.log(files);
    while (files.includes(candidate)) {
      candidate = `${baseName} (${counter})${ext}`;
      counter++;
    }
    try {
      const newFilePath = path.join(dir, candidate);
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

  ipcMain.handle('recently-viewed-delete', async (event, fileName, fileLocation = null) => {
    try {
      if (!fs.existsSync(RECENTLY_VIEWED_PATH)) {
        return { success: false, error: 'recently-viewed.json not found' };
      }

      const data = fs.readFileSync(RECENTLY_VIEWED_PATH, 'utf-8');
      let recentlyViewed = JSON.parse(data);

      const originalLength = recentlyViewed.length;
      recentlyViewed = recentlyViewed.filter(item => {
        if (fileLocation) {
          return !(item.name === fileName && item.fileLocation === fileLocation);
        }
        return item.name !== fileName;
      });

      if (recentlyViewed.length === originalLength) {
        return { success: false, error: 'Entry not found' };
      }

      fs.writeFileSync(RECENTLY_VIEWED_PATH, JSON.stringify(recentlyViewed, null, 2), 'utf-8');
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

  ipcMain.handle('open-file-location', async (event, filePath) => {
    const folder = path.dirname(filePath);
    // Windows: explorer, Mac: open, Linux: xdg-open
    const command = process.platform === 'win32' ? 'explorer' : process.platform === 'darwin' ? 'open' : 'xdg-open';
    const arg = process.platform === 'win32' ? folder.replace(/\//g, '\\') : folder;
    require('child_process').spawn(command, [arg], { detached: true });
    return true;
  });

  ipcMain.handle('remove-directory', async (event, section, dirName) => {
    try {
      if (!fs.existsSync(directoryPath)) return { success: false, error: 'directory.json not found' };
      const data = fs.readFileSync(directoryPath, 'utf-8');
      const directory = JSON.parse(data);
      if (!directory[section]) return { success: false, error: 'Section not found' };
      directory[section] = directory[section].filter(obj => Object.keys(obj)[0] !== dirName);
      fs.writeFileSync(directoryPath, JSON.stringify(directory, null, 2), 'utf-8');
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  ipcMain.handle('run-python-retrieve', async (event, filePath) => {
    const id = crypto.randomUUID();

    return new Promise((resolve, reject) => {
      const scriptPath = path.join(__dirname, 'inner', 'src', 'main.py');
      console.log(`${scriptPath}, 'retrieve', ${filePath}, ${id}`)
      const pythonProcess = spawn('python', [scriptPath, 'retrieve', filePath, id]);

      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          reject({ success: false, error: `Python exited with code ${code}` });
          return;
        }

        // Wait for file to contain matching ID
        const maxWaitMs = 10000;
        const intervalMs = 100;
        let waited = 0;

        const check = () => {
          if (!fs.existsSync(RETRIEVE_OUTPUT_PATH)) {
            waited += intervalMs;
            if (waited >= maxWaitMs) {
              reject({ success: false, error: 'Timeout waiting for response.json' });
            } else {
              setTimeout(check, intervalMs);
            }
            return;
          }
          //console.log(RETRIEVE_OUTPUT_PATH);
          const data = JSON.parse(fs.readFileSync(RETRIEVE_OUTPUT_PATH, 'utf-8'));
          if (data.id === id) {
            resolve(data);
          } else {
            waited += intervalMs;
            if (waited >= maxWaitMs) {
              reject({ success: false, error: 'ID mismatch or timeout' });
            } else {
              setTimeout(check, intervalMs);
            }
          }
        };

        check();
      });
    });
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
