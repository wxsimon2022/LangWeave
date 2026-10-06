const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,

  // 获取桌面端版本号
  getAppVersion: () => ipcRenderer.invoke("get-app-version"),

  // 手动检查更新
  checkForUpdate: () => ipcRenderer.invoke("check-for-update"),

  // 下载更新
  downloadUpdate: () => ipcRenderer.invoke("download-update"),

  // 安装已下载的更新
  installUpdate: () => ipcRenderer.invoke("install-update"),

  // 打开下载地址（浏览器）
  openReleaseUrl: (url) => ipcRenderer.invoke("open-release-url", url),

  // ── 监听主进程推送的事件 ──

  // 发现新版本（有更新可用）
  onUpdateAvailable: (callback) => {
    const handler = (_event, info) => callback(info);
    ipcRenderer.on("update-available", handler);
    return () => ipcRenderer.removeListener("update-available", handler);
  },

  // 下载进度
  onUpdateDownloadProgress: (callback) => {
    const handler = (_event, progress) => callback(progress);
    ipcRenderer.on("update-download-progress", handler);
    return () => ipcRenderer.removeListener("update-download-progress", handler);
  },

  // 状态变更（checking / up-to-date / downloaded）
  onUpdateStatus: (callback) => {
    const handler = (_event, status) => callback(status);
    ipcRenderer.on("update-status", handler);
    return () => ipcRenderer.removeListener("update-status", handler);
  },

  // 更新错误
  onUpdateError: (callback) => {
    const handler = (_event, err) => callback(err);
    ipcRenderer.on("update-error", handler);
    return () => ipcRenderer.removeListener("update-error", handler);
  },
});
