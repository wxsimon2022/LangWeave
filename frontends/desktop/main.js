const { app, BrowserWindow, ipcMain, shell, Notification } = require("electron");
const path = require("path");
const https = require("https");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const APP_URL = process.env.LANGWEAVE_URL || "https://chat.mybfs.cn/app.html";
const GITHUB_REPO = "wxsimon2022/LangWeave";
const CURRENT_VERSION = app.getVersion();
const UPDATE_CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000; // 每 6 小时检查一次

// ---------------------------------------------------------------------------
// GitHub Release helpers
// ---------------------------------------------------------------------------
function fetchLatestRelease() {
  return new Promise((resolve, reject) => {
    const req = https.get(
      `https://api.github.com/repos/${GITHUB_REPO}/releases/latest`,
      { headers: { "User-Agent": "LangWeave-Desktop", Accept: "application/vnd.github.v3+json" } },
      (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          try {
            const json = JSON.parse(data);
            resolve({
              tagName: json.tag_name || "",
              htmlUrl: json.html_url || `https://github.com/${GITHUB_REPO}/releases/latest`,
              publishedAt: json.published_at || "",
              body: json.body || "",
            });
          } catch {
            reject(new Error("Failed to parse release data"));
          }
        });
      }
    );
    req.on("error", reject);
    req.setTimeout(10000, () => {
      req.destroy();
      reject(new Error("Request timed out"));
    });
  });
}

/**
 * Compare two semantic versions.
 * Returns: 1 if a > b, -1 if a < b, 0 if equal.
 */
function compareVersions(a, b) {
  const pa = a.replace(/^v/, "").split(".").map(Number);
  const pb = b.replace(/^v/, "").split(".").map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] || 0;
    const nb = pb[i] || 0;
    if (na > nb) return 1;
    if (na < nb) return -1;
  }
  return 0;
}

/**
 * Check for a new version.
 * Returns { hasUpdate, currentVersion, latestVersion, releaseUrl, releaseNotes }.
 */
async function checkForUpdate() {
  try {
    const release = await fetchLatestRelease();
    const latestTag = release.tagName;
    const hasUpdate = compareVersions(latestTag, `v${CURRENT_VERSION}`) > 0;
    return {
      hasUpdate,
      currentVersion: CURRENT_VERSION,
      latestVersion: latestTag.replace(/^v/, ""),
      releaseUrl: release.htmlUrl,
      releaseNotes: release.body,
    };
  } catch (err) {
    return { hasUpdate: false, error: err.message };
  }
}

// ---------------------------------------------------------------------------
// Send update info to the renderer
// ---------------------------------------------------------------------------
function notifyRendererOfUpdate(info) {
  const wins = BrowserWindow.getAllWindows();
  for (const win of wins) {
    if (!win.isDestroyed()) {
      win.webContents.send("update-check-result", info);
    }
  }
}

async function performUpdateCheck(silent = false) {
  const info = await checkForUpdate();
  if (info.hasUpdate) {
    notifyRendererOfUpdate(info);

    // Show native notification if the renderer isn't ready yet
    if (silent && Notification.isSupported()) {
      const notif = new Notification({
        title: "LangWeave 有新版本",
        body: `版本 ${info.latestVersion} 已发布，点击查看详情`,
      });
      notif.on("click", () => {
        const wins = BrowserWindow.getAllWindows();
        if (wins.length > 0 && !wins[0].isDestroyed()) {
          wins[0].focus();
        }
      });
      notif.show();
    }
  }
  return info;
}

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------
ipcMain.handle("check-for-update", async () => {
  return performUpdateCheck();
});

ipcMain.handle("get-app-version", () => {
  return CURRENT_VERSION;
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
    performUpdateCheck(true);
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
setInterval(() => performUpdateCheck(true), UPDATE_CHECK_INTERVAL_MS);
