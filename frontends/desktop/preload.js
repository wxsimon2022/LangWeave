const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,

  // 获取桌面端版本号
  getAppVersion: () => ipcRenderer.invoke("get-app-version"),

  // 手动检查更新
  checkForUpdate: () => ipcRenderer.invoke("check-for-update"),

  // 打开下载地址（浏览器）
  openReleaseUrl: (url) => ipcRenderer.invoke("open-release-url", url),

  // 监听主进程推送的更新检查结果（启动时自动检查 / 定时检查）
  onUpdateCheckResult: (callback) => {
    const handler = (_event, info) => callback(info);
    ipcRenderer.on("update-check-result", handler);
    // Return an unsubscribe function
    return () => ipcRenderer.removeListener("update-check-result", handler);
  },
});
