const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,

  // 检查更新
  checkForUpdate: () => ipcRenderer.invoke("check-for-update"),

  // 打开下载地址（浏览器）
  openReleaseUrl: (url) => ipcRenderer.invoke("open-release-url", url),
});
