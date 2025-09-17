const { app, BrowserWindow, ipcMain, dialog, shell, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const userDataPath = app.getPath('userData');
const directoryPath = path.join(userDataPath, 'directory.json');
const sourcePath = path.join(__dirname, 'inner', 'src');
const RECENTLY_VIEWED_PATH = path.join(userDataPath, 'recently-viewed.json');
const RETRIEVE_OUTPUT_PATH = path.join(userDataPath, 'response.json');
const STARRED_PATH = path.join(userDataPath, 'starred.json');
const USER_SETTINGS_PATH = path.join(userDataPath, 'user-settings.json');

const DEFAULT_SETTINGS = {
  "needs_onboarding": true,
  "search_for_updates": true,
  "close_project_manager_when_editing": false,
  "show_splash_screen": true,
  "user_name": "",
  "fancy_graphics" : true,
  "show_console": false,
  "disable_auto_save": false,
  "disable_delete_confirm": false
};

let mainWindow;

app.whenReady().then(() => {
  // On first run, copy default JSONs from asar to userData if missing
  function ensureFile(src, dest, defaultContent) {
    if (!fs.existsSync(dest)) {
      try {
        if (fs.existsSync(src)) {
          fs.copyFileSync(src, dest);
        } else if (defaultContent !== undefined) {
          fs.writeFileSync(dest, JSON.stringify(defaultContent, null, 2), 'utf-8');
        }
      } catch (e) {
        console.error('Failed to copy default file:', src, '->', dest, e);
      }
    }
  }
  const assetDir = path.join(__dirname, 'src', 'assets');
  ensureFile(path.join(assetDir, 'user-settings.json'), USER_SETTINGS_PATH, DEFAULT_SETTINGS);
  ensureFile(path.join(assetDir, 'directory.json'), directoryPath, {"Projects":[],"Exports":[],"Symphony Auto-Save":[]});
  ensureFile(path.join(assetDir, 'starred.json'), STARRED_PATH, []);
  ensureFile(path.join(assetDir, 'recently-viewed.json'), RECENTLY_VIEWED_PATH, []);
  mainWindow = new BrowserWindow({
    width: 1300,
    height: 800,
    minWidth: 800,
    minHeight: 800,
    frame: false,
    icon: path.join(__dirname, 'src/assets', 'icon-dark32x32.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false, // best for security
    },
  });

  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile('dist/index.html');
  }
  // mainWindow.webContents.openDevTools();


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
      if (!isDev) mainWindow.webContents.openDevTools();
    }
  });
  ipcMain.on('start-drag', (event, filePath) => {
    console.log('start-drag', filePath);
    mainWindow.webContents.startDrag({
      file: filePath,
      icon: nativeImage.createFromPath(path.join(__dirname, 'src', 'assets', 'icon-dark32x32.png'))
    });
  });

  ipcMain.on('open-external', (event, url) => {
    shell.openExternal(url);
  });

  ipcMain.handle('move-file-raw', async (event, arrayBuffer, fileName, destinationDir) => {
    const destPath = path.join(destinationDir, fileName);
    try {
      // Convert ArrayBuffer to Node.js Buffer here
      const buffer = Buffer.from(arrayBuffer);

      await fs.promises.writeFile(destPath, buffer);
      return { success: true };
    } catch (error) {
      console.error("Failed to save file:", error);
      return { success: false, error: error.message };
    }
  });


  ipcMain.handle('get-symphony-files', async (event, directoryPath) => {
    let files = null
    try { files = fs.readdirSync(directoryPath); } catch(error) { return 'not a valid dir' }

    const validFileExts = ['.symphony', '.wav', '.mid', '.mp3'];
    
    const symphonyFiles = files.filter(file => validFileExts.includes(path.extname(file)));
    return symphonyFiles || 'no files';
  });

  ipcMain.handle('open-native-app', async (event, filePath) => {
    const result = await shell.openPath(filePath);
    if (result) {
      console.error(`Error: "get-symphony-files" in main.js \n Unable to locate ${filePath}`);
      return { success: false, error: result };
    }
    try {
      let recent = [];
      if (fs.existsSync(RECENTLY_VIEWED_PATH)) {
        recent = JSON.parse(fs.readFileSync(RECENTLY_VIEWED_PATH, 'utf-8'));
      }
      // Compose new entry
      const fileName = path.basename(filePath);
      const fileType = path.extname(fileName).replace('.', '').toLowerCase();
      const entry = {
        type: fileType,
        name: fileName,
        fileLocation: path.dirname(filePath)
      };
      // Remove any existing entry with same name and location
      recent = recent.filter(r => !(r.name === entry.name && r.fileLocation === entry.fileLocation));
      // Add to top
      recent.unshift(entry);
      // Limit to 20 entries
      if (recent.length > 20) recent = recent.slice(0, 20);
      fs.writeFileSync(RECENTLY_VIEWED_PATH, JSON.stringify(recent, null, 2), 'utf-8');
    } catch (e) {
      //console.error('Failed to update recently viewed:', e);
      console.log('Failed to open file:', e);
      return { success: false, error: e }
    }
    return { success: true };
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
          if (folderPath.replace(/\\/g, '/') === filePath.replace(/\\/g, '/')) {
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
    console.log(JSON.stringify(argsArray));

    const isOpenCommand = argsArray[0] === 'open';
    let closeManager = false;
    let openConsole = false;

    // const absSourcePath = path.resolve(sourcePath);
    const absSourcePath = path.join(process.resourcesPath, 'app.asar.unpacked', 'inner', 'dist');
    argsArray.push(absSourcePath);

    // Pass userData path to Python for response.json
    //argsArray.push(userDataPath);

    // Update Recently Viewed
    if (isOpenCommand) {
      try {
        let recent = [];
        if (fs.existsSync(RECENTLY_VIEWED_PATH)) {
          recent = JSON.parse(fs.readFileSync(RECENTLY_VIEWED_PATH, 'utf-8'));
        }

        const fileName = argsArray[1] || '';
        const fileType = path.extname(fileName).replace('.', '').toLowerCase();
        const entry = {
          type: fileType,
          name: fileName,
          fileLocation: argsArray[2] || ''
        };

        // Remove duplicates and prepend new entry
        recent = recent.filter(r => !(r.name === entry.name && r.fileLocation === entry.fileLocation));
        recent.unshift(entry);
        if (recent.length > 20) recent = recent.slice(0, 20);

        fs.writeFileSync(RECENTLY_VIEWED_PATH, JSON.stringify(recent, null, 2), 'utf-8');
      } catch (e) {
        console.error('Failed to update recently viewed:', e);
      }

      try {
        const settings = JSON.parse(fs.readFileSync(USER_SETTINGS_PATH, 'utf-8'));
        closeManager = !!settings["close_project_manager_when_editing"];
        openConsole = !!settings["open_console"];
      } catch (e) {
        console.error('Failed to read user settings:', e);
      }
      // Append absolute autosave and user settings paths for 'open' command
      const absAutoSave = path.resolve(directoryPath);
      const absUserSettings = path.resolve(USER_SETTINGS_PATH);
      argsArray.push(absAutoSave, absUserSettings);
    }

    // Always use main.exe in asar.unpacked
    const exePath = path.join(process.resourcesPath, 'app.asar.unpacked', 'inner', 'dist', 'main.exe');
    console.log(`${argsArray.map(arg => `'${arg}'`).join(' ')}`)

    if (closeManager) {
      // Run detached process
      const detachedProcess = spawn(exePath, argsArray, {
        detached: true,
        stdio: 'ignore',
      });
      detachedProcess.unref(); // Let it live independently

      // Close project manager window
      const windows = BrowserWindow.getAllWindows();
      if (windows.length > 0) windows[0].close(); // Adjust if you have a window reference

      return { success: true, output: 'Script launched in background' };
    } else {
      // Run attached process with output capture
      return new Promise((resolve, reject) => {
        const pythonProcess = spawn(exePath, argsArray);

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
    }
  });

  ipcMain.handle('run-python-retrieve', async (event, filePath) => {
    const id = crypto.randomUUID();

    return new Promise((resolve, reject) => {
      const exePath = path.join(process.resourcesPath, 'app.asar.unpacked', 'inner', 'dist', 'main.exe');
      const absSourcePath = path.join(process.resourcesPath, 'app.asar.unpacked', 'inner', 'dist');
      //argsArray.push(userDataPath);
      console.log(`'retrieve' '${filePath}' '${id}' '${absSourcePath}' '${userDataPath}'`)

      const pythonProcess = spawn(exePath, ['retrieve', filePath, id, absSourcePath, userDataPath]);

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
          console.log(RETRIEVE_OUTPUT_PATH);
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

  ipcMain.handle('rename-file', async (event, { filePath, newName }) => {
    const dir = path.dirname(filePath);
    let baseName = newName;
    let ext = path.extname(newName);
    if (!ext) ext = '.symphony';

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

      // Also rename the metadata JSON if it exists
      const originalJsonPath = filePath.replace(/\.symphony$/, '.json');
      const newJsonPath = newFilePath.replace(/\.symphony$/, '.json');

      if (fs.existsSync(originalJsonPath)) {
        fs.renameSync(originalJsonPath, newJsonPath);
      }

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
      // Try to delete the corresponding .json metadata file
      const metadataPath = filePath.replace(/\.symphony$/, '.json');
      if (fs.existsSync(metadataPath)) {
        fs.unlinkSync(metadataPath);
      }
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

  ipcMain.handle('get-user-settings', async () => {
    try {
      let userSettings = {};

      if (fs.existsSync(USER_SETTINGS_PATH)) {
        const data = fs.readFileSync(USER_SETTINGS_PATH, 'utf-8');
        userSettings = JSON.parse(data);
      }

      // Merge defaults with user settings
      const updatedSettings = { ...DEFAULT_SETTINGS, ...userSettings };

      // Save merged settings back to file (in case new keys were added)
      fs.writeFileSync(USER_SETTINGS_PATH, JSON.stringify(updatedSettings, null, 2));

      return updatedSettings;
    } catch (err) {
      console.error("Error reading or updating user settings:", err);
      return DEFAULT_SETTINGS; // fallback to defaults if something breaks
    }
  });

  ipcMain.handle('update-user-settings', async (_event, key, value) => {
    try {
      const data = fs.readFileSync(USER_SETTINGS_PATH, 'utf-8');
      const settings = JSON.parse(data);

      settings[key] = value;

      fs.writeFileSync(USER_SETTINGS_PATH, JSON.stringify(settings, null, 2));

      return { success: true, settings };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  ipcMain.handle('get-stars', async () => {
    try {
      if (!fs.existsSync(STARRED_PATH)) {
        fs.writeFileSync(STARRED_PATH, '[]', 'utf-8');
      }
      const data = fs.readFileSync(STARRED_PATH, 'utf-8');
      return JSON.parse(data);
    } catch (err) {
      return [];
    }
  });

  ipcMain.handle('add-star', async (event, filePath) => {
    try {
      if (!fs.existsSync(STARRED_PATH)) {
        fs.writeFileSync(STARRED_PATH, '[]', 'utf-8');
      }
      const data = fs.readFileSync(STARRED_PATH, 'utf-8');
      const stars = JSON.parse(data);
      const normalizeSlashes = (p) => p.replace(/\\/g, '/');

      const normalizedFilePath = normalizeSlashes(filePath);
      const normalizedStars = stars.map(p => normalizeSlashes(p));
      // console.log(normalizedFilePath);
      // console.log(normalizedStars);

      if (!normalizedStars.includes(normalizedFilePath)) {
        stars.push(filePath);
        fs.writeFileSync(STARRED_PATH, JSON.stringify(stars, null, 2), 'utf-8');
      }

      return stars;
    } catch (err) {
      console.error('Error in add-star:', err);
      return [];
    }
  });

  ipcMain.handle('remove-star', async (event, filePath) => {
    try {
      if (!fs.existsSync(STARRED_PATH)) {
        fs.writeFileSync(STARRED_PATH, '[]', 'utf-8');
      }
      const data = fs.readFileSync(STARRED_PATH, 'utf-8');
      let stars = JSON.parse(data);

      stars = stars.filter(star => star.replace(/\\/g, '/') !== filePath.replace(/\\/g, '/'));
      fs.writeFileSync(STARRED_PATH, JSON.stringify(stars, null, 2), 'utf-8');

      return stars;
    } catch (err) {
      console.error('Error in remove-star:', err);
      return [];
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
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
