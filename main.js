const { app, BrowserWindow, ipcMain, dialog, shell, nativeImage } = require('electron');
const yaml = require('js-yaml');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const USER_DATA_PATH = app.getPath('userData');
const DIRECTORY_PATH = path.join(USER_DATA_PATH, 'directory.json');
const RECENTLY_VIEWED_PATH = path.join(USER_DATA_PATH, 'recently-viewed.json');
const STARRED_PATH = path.join(USER_DATA_PATH, 'starred.json');
const USER_SETTINGS_PATH = path.join(USER_DATA_PATH, 'user-settings.json');
let EXECUTABLE_NAME = process.platform === 'win32' ? 'main.exe' : 'main';
let INNER_DIST_PATH = path.join(process.resourcesPath, 'app.asar.unpacked', 'inner', 'dist');

let config = {}
try {
  const filePath = path.join(__dirname, 'config.yaml');
  const fileContents = fs.readFileSync(filePath, 'utf8');
  config = yaml.load(fileContents);
} catch (err) {
  console.error('Failed to load YAML:', err);
  config = null;
}
console.log(config)
if (!app.isPackaged) {
  INNER_DIST_PATH = path.join(__dirname, 'inner', 'src');
}
if (config && !config.editorIsExe) {
  EXECUTABLE_NAME = 'main.py'
}
const EXECUTABLE_PATH = path.join(INNER_DIST_PATH, EXECUTABLE_NAME);
console.log(EXECUTABLE_PATH);
const PROCESS_COMMAND_PATH = path.join(USER_DATA_PATH, 'process-command.json');

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
  ensureFile(path.join(assetDir, 'directory.json'), DIRECTORY_PATH, {"Projects":[],"Exports":[],"Symphony Auto-Save":[]});
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


  // Window Controls
  ipcMain.on('minimize', () => mainWindow.minimize());
  ipcMain.on('maximize', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });
  ipcMain.on('close', () => mainWindow.close());
  ipcMain.on('toggle-devtools', () => {
    if (mainWindow.webContents.isDevToolsOpened()) {
      mainWindow.webContents.closeDevTools();
    } else {
      if (isDev) mainWindow.webContents.openDevTools();
    }
  });
  mainWindow.on('maximize', () => {
    mainWindow.webContents.send('window-state', true);
  });
  mainWindow.on('unmaximize', () => {
    mainWindow.webContents.send('window-state', false);
  });


  // function to spawn the editor program
  function runEditorProgram() {
    try {
      // Ensure the process command file exists
      if (!fs.existsSync(PROCESS_COMMAND_PATH)) {
        fs.writeFileSync(PROCESS_COMMAND_PATH, JSON.stringify({}, null, 2));
      }

      // Determine if the target is a Python script
      const isPythonScript = EXECUTABLE_PATH.endsWith('.py');

      // Resolve absolute paths
      const scriptPath = path.resolve(EXECUTABLE_PATH);
      const commandPath = path.resolve(PROCESS_COMMAND_PATH);
      const sourcePath = path.resolve(INNER_DIST_PATH)

      // Build command and arguments
      let command, args;
      if (isPythonScript) {
        command = process.platform === 'win32' ? 'python' : 'python3';
        args = [scriptPath, sourcePath, commandPath];
      } else {
        command = scriptPath;
        args = [sourcePath, commandPath];
      }

      // Spawn the process
      const child = spawn(command, args, {
        detached: false,  // keep attached to Node terminal for debugging
        stdio: 'pipe',    // capture stdout and stderr
        shell: false
      });

      let stdoutData = '';
      let stderrData = '';

      // Capture stdout
      child.stdout.on('data', (data) => {
        const text = data.toString();
        stdoutData += text;
        process.stdout.write(text); // live print
      });

      // Capture stderr
      child.stderr.on('data', (data) => {
        const text = data.toString();
        stderrData += text;
        process.stderr.write(text); // live print
      });

      // Handle process exit
      child.on('exit', (code) => {
        if (code !== 0) {
          console.error(`Editor process crashed with code ${code}`);
          if (stderrData) {
            const lastErrorLine = stderrData.trim().split('\n').pop();
            console.error('Last error:', lastErrorLine);
          }
        } else {
          console.log('Editor process exited successfully.');
        }
      });

      return { success: true, message: 'Editor daemon started' };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }
  console.log(runEditorProgram());

  // File Operations
  ipcMain.on('start-drag', (event, filePath) => {
    mainWindow.webContents.startDrag({
      file: filePath,
      icon: nativeImage.createFromPath(path.join(__dirname, 'src', 'assets', 'icon-dark32x32.png'))
    });
  });
  ipcMain.on('open-external', (event, url) => {
    shell.openExternal(url);
  });
  ipcMain.handle('file-exists', async (event, filePath) => fs.existsSync(filePath));
  ipcMain.handle('delete-file', async (event, filePath) => {
    try {
      fs.unlinkSync(filePath);
      const metadataPath = filePath.replace(/\.symphony$/, '.json');
      if (fs.existsSync(metadataPath)) {
        fs.unlinkSync(metadataPath);
      }
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });
  ipcMain.handle('rename-file', async (event, { filePath, newName }) => {
    const dir = path.dirname(filePath);
    let baseName = newName;
    let ext = path.extname(newName);
    if (!ext) ext = '.symphony';
    let candidate = baseName + ext;
    let counter = 1;
    const files = fs.readdirSync(dir);
    while (files.includes(candidate)) {
      candidate = `${baseName} (${counter})${ext}`;
      counter++;
    }
    try {
      const newFilePath = path.join(dir, candidate);
      fs.renameSync(filePath, newFilePath);
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
  ipcMain.handle('copy-file', async (event, src, dest) => {
    return new Promise((resolve, reject) => {
      fs.copyFile(src, dest, (err) => {
        if (err) reject(err);
        else resolve('success');
      });
    });
  });
  ipcMain.handle('move-file-raw', async (event, arrayBuffer, fileName, destinationDir) => {
    const destPath = path.join(destinationDir, fileName);
    try {
      const buffer = Buffer.from(arrayBuffer);
      await fs.promises.writeFile(destPath, buffer);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // Directory Operations
  ipcMain.handle('dialog:openDirectory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory']
    });
    return result.canceled || result.filePaths.length === 0 ? null : result.filePaths[0];
  });
  ipcMain.handle('save-directory', async (event, { destination, projectName, sourceLocation }) => {
    try {
      const data = fs.readFileSync(DIRECTORY_PATH, 'utf-8');
      const directory = JSON.parse(data);
      if (!directory[destination]) {
        directory[destination] = [];
      }
      const nameExists = directory[destination].some(entry => entry[projectName]);
      const locationExists = directory[destination].some(entry => Object.values(entry).includes(sourceLocation));
      if (nameExists || locationExists) {
        return { success: false, error: 'Duplicate entry' };
      }
      directory[destination].push({ [projectName]: sourceLocation });
      fs.writeFileSync(DIRECTORY_PATH, JSON.stringify(directory, null, 2), 'utf-8');
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });
  ipcMain.handle('get-directory', async () => {
    try {
      if (!fs.existsSync(DIRECTORY_PATH)) {
        const defaultDirectory = { Projects: [], Exports: [], 'Symphony Auto-Save': [] };
        fs.writeFileSync(DIRECTORY_PATH, JSON.stringify(defaultDirectory, null, 2));
        return defaultDirectory;
      }
      return JSON.parse(fs.readFileSync(DIRECTORY_PATH, 'utf-8'));
    } catch (err) {
      return { error: err.message };
    }
  });
  ipcMain.handle('remove-directory', async (event, section, dirName) => {
    try {
      if (!fs.existsSync(DIRECTORY_PATH)) return { success: false, error: 'directory.json not found' };
      const data = fs.readFileSync(DIRECTORY_PATH, 'utf-8');
      const directory = JSON.parse(data);
      if (!directory[section]) return { success: false, error: 'Section not found' };
      directory[section] = directory[section].filter(obj => Object.keys(obj)[0] !== dirName);
      fs.writeFileSync(DIRECTORY_PATH, JSON.stringify(directory, null, 2), 'utf-8');
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });
  ipcMain.handle('get-section-for-path', async (event, filePath) => {
    try {
      if (!fs.existsSync(DIRECTORY_PATH)) {
        return { error: 'Directory data not found.' };
      }
      const directoryData = JSON.parse(fs.readFileSync(DIRECTORY_PATH, 'utf-8'));

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


  // Metadata Operations
  ipcMain.handle('get-metadata', async (event, filePath) => {
    try {
      const metaPath = filePath.replace(/\.symphony$/, '.json');
      return fs.existsSync(metaPath) ? JSON.parse(fs.readFileSync(metaPath, 'utf-8')) : {};
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

  // Recently Viewed
  ipcMain.handle('get-recently-viewed', async () => {
    try {
      if (!fs.existsSync(RECENTLY_VIEWED_PATH)) {
        fs.writeFileSync(RECENTLY_VIEWED_PATH, '[]', 'utf-8');
      }
      return JSON.parse(fs.readFileSync(RECENTLY_VIEWED_PATH, 'utf-8'));
    } catch (err) {
      return [];
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

  // Starred Files
  ipcMain.handle('get-stars', async () => {
    try {
      if (!fs.existsSync(STARRED_PATH)) {
        fs.writeFileSync(STARRED_PATH, '[]', 'utf-8');
      }
      return JSON.parse(fs.readFileSync(STARRED_PATH, 'utf-8'));
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
      const normalizedFilePath = filePath.replace(/\\/g, '/');
      if (!stars.includes(normalizedFilePath)) {
        stars.push(filePath);
        fs.writeFileSync(STARRED_PATH, JSON.stringify(stars, null, 2), 'utf-8');
      }
      return stars;
    } catch (err) {
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
      return [];
    }
  });

  // User Settings
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

  // Symphony File Commands
  ipcMain.handle('get-symphony-files', async (event, directoryPath) => {
    try {
      const files = fs.readdirSync(directoryPath);
      const validFileExts = ['.symphony', '.wav', '.mid', '.mp3'];
      return files.filter(file => validFileExts.includes(path.extname(file)));
    } catch (error) {
      return 'not a valid dir';
    }
  });
  ipcMain.handle('open-native-app', async (event, filePath) => {
    const result = await shell.openPath(filePath);
    if (result) {
      return { success: false, error: result };
    }
    try {
      let recent = [];
      if (fs.existsSync(RECENTLY_VIEWED_PATH)) {
        recent = JSON.parse(fs.readFileSync(RECENTLY_VIEWED_PATH, 'utf-8'));
      }
      const fileName = path.basename(filePath);
      const fileType = path.extname(fileName).replace('.', '').toLowerCase();
      const entry = { type: fileType, name: fileName, fileLocation: path.dirname(filePath) };
      recent = recent.filter(r => !(r.name === entry.name && r.fileLocation === entry.fileLocation));
      recent.unshift(entry);
      if (recent.length > 20) recent = recent.slice(0, 20);
      fs.writeFileSync(RECENTLY_VIEWED_PATH, JSON.stringify(recent, null, 2), 'utf-8');
    } catch (e) {
      return { success: false, error: e };
    }
    return { success: true };
  });

  // Editor Program
  ipcMain.handle('run-editor-program', async () => {
    runEditorProgram();
  });
  ipcMain.handle('do-process-command', async (event, symphonyFilePath, command, extraArgs = {}) => {
    const id = crypto.randomUUID();
    const projectFolderPath = path.dirname(symphonyFilePath);
    const projectFileName = path.basename(symphonyFilePath, '.symphony');
    const processCommand = {
      command,
      id,
      pc_file_path: PROCESS_COMMAND_PATH,
      args: {
        project_file_name: projectFileName,
        project_folder_path: projectFolderPath,
        symphony_data_path: USER_DATA_PATH,
        ...extraArgs
      }
    };
    fs.writeFileSync(PROCESS_COMMAND_PATH, JSON.stringify(processCommand, null, 2), 'utf-8');
    await new Promise(res => setTimeout(res, 1000));
    const maxWaitMs = 15000;
    const pollIntervalMs = 100;
    let waited = 0;
    return new Promise((resolve) => {
      const poll = () => {
        try {
          if (!fs.existsSync(PROCESS_COMMAND_PATH)) {
            waited += pollIntervalMs;
            return waited >= maxWaitMs
              ? resolve({ timeout: true })
              : setTimeout(poll, pollIntervalMs);
          }
          const data = JSON.parse(fs.readFileSync(PROCESS_COMMAND_PATH, 'utf-8'));
          if (data.id === id && data.status) {
            return resolve(data);
          }
        } catch (e) {}
        waited += pollIntervalMs;
        if (waited >= maxWaitMs) {
          resolve(JSON.parse(fs.readFileSync(PROCESS_COMMAND_PATH, 'utf-8')));
        } else {
          setTimeout(poll, pollIntervalMs);
        }
      };
      poll();
    });
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
