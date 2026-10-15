const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('nrnfDesktop', Object.freeze({ isDesktop: true }))
