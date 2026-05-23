const { app, BrowserWindow, ipcMain, shell } = require("electron");
const path = require("path");
const https = require("https");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const APP_URL = process.env.LANGWEAVE_URL || "https://chat.mybfs.cn/app.html";
const GITHUB_REPO = "wxsimon2022/LangWeave";
const CURRENT_VERSION = app.getVersion(); // 从 package.json version 读取

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

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------
ipcMain.handle("check-for-update", async () => {
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
    minWidth: 800,
    minHeight: 600,
    title: "LangWeave",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(APP_URL);

  mainWindow.on("closed", () => {
    mainWindow = null;
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
