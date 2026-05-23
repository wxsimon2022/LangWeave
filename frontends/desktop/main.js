const { app, BrowserWindow, ipcMain, shell, Notification } = require("electron");
const path = require("path");
const { autoUpdater } = require("electron-updater");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const APP_URL = process.env.LANGWEAVE_URL || "https://chat.mybfs.cn/app.html";
const UPDATE_CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000; // 每 6 小时检查一次

// ---------------------------------------------------------------------------
// Auto-updater setup
// ---------------------------------------------------------------------------
autoUpdater.autoDownload = false; // 让用户确认后再下载
autoUpdater.autoInstallOnAppQuit = false; // 下载后用户手动触发安装
autoUpdater.allowPrerelease = false;

// Forward autoUpdater events to the renderer
function sendToRenderer(channel, data) {
  const wins = BrowserWindow.getAllWindows();
  for (const win of wins) {
    if (!win.isDestroyed()) {
      win.webContents.send(channel, data);
    }
  }
}

autoUpdater.on("checking-for-update", () => {
  sendToRenderer("update-status", { status: "checking" });
});

autoUpdater.on("update-available", (info) => {
  sendToRenderer("update-available", {
    version: info.version,
    releaseNotes: info.releaseNotes || "",
    releaseDate: info.releaseDate || "",
  });

  // Native notification
  if (Notification.isSupported()) {
    const notif = new Notification({
      title: "LangWeave 有新版本",
      body: `版本 ${info.version} 已发布，点击更新`,
    });
    notif.on("click", () => {
      const wins = BrowserWindow.getAllWindows();
      if (wins.length > 0 && !wins[0].isDestroyed()) {
        wins[0].focus();
      }
    });
    notif.show();
  }
});

autoUpdater.on("update-not-available", () => {
  sendToRenderer("update-status", { status: "up-to-date" });
});

autoUpdater.on("download-progress", (progress) => {
  sendToRenderer("update-download-progress", {
    percent: Math.round(progress.percent),
    bytesPerSecond: progress.bytesPerSecond,
    total: progress.total,
    transferred: progress.transferred,
  });
});

autoUpdater.on("update-downloaded", () => {
  sendToRenderer("update-status", { status: "downloaded" });
});

autoUpdater.on("error", (err) => {
  sendToRenderer("update-error", { message: err.message });
});

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------

/** Manual check for update. */
ipcMain.handle("check-for-update", async () => {
  autoUpdater.checkForUpdates();
  return { checking: true };
});

/** Start downloading the update. */
ipcMain.handle("download-update", async () => {
  autoUpdater.downloadUpdate();
  return { downloading: true };
});

/** Quit and install the downloaded update. */
ipcMain.handle("install-update", async () => {
  setImmediate(() => autoUpdater.quitAndInstall());
  return { installing: true };
});

ipcMain.handle("get-app-version", () => {
  return app.getVersion();
});

ipcMain.handle("open-release-url", async (_event, url) => {
  if (url) {
    shell.openExternal(url);
  }
});

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------
let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 500,
    minHeight: 400,
    title: "LangWeave",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.maximize();
  mainWindow.loadURL(APP_URL);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // After the window loads, check for updates silently
  mainWindow.webContents.on("did-finish-load", () => {
    autoUpdater.checkForUpdates();
  });
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Periodic background update check
setInterval(() => autoUpdater.checkForUpdates(), UPDATE_CHECK_INTERVAL_MS);
