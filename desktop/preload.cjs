const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('nrnfDesktop', Object.freeze({ isDesktop: true, quit: () => ipcRenderer.send('quit-from-menu') }))
