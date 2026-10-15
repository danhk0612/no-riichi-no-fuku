const { app, BrowserWindow, dialog, session } = require('electron')
const { spawn } = require('node:child_process')
const { createServer } = require('node:net')
const { mkdirSync, writeFileSync, existsSync } = require('node:fs')
const { join, resolve } = require('node:path')
const { randomUUID } = require('node:crypto')
const readline = require('node:readline')

const args = process.argv.slice(1)
const valueAfter = name => {
  const index = args.indexOf(name)
  return index >= 0 ? args[index + 1] : undefined
}
const smoke = args.includes('--smoke')
const explicitDataRoot = valueAfter('--data')
const evidencePath = valueAfter('--evidence')
let dataRoot
let child
let childLines
let origin
let capability
let window
let quitting = false
let closeRequested = false
let rendererExternalRequestBlocked = false
const evidence = { platform: process.platform, arch: process.arch, checks: [] }
const delay = ms => new Promise(resolveDelay => setTimeout(resolveDelay, ms))
let bootstrapError

function addCheck(name, detail = 'passed') {
  evidence.checks.push({ name, detail })
  writeEvidence()
}

function writeEvidence() {
  if (!smoke || !evidencePath) return
  try {
    mkdirSync(require('node:path').dirname(resolve(evidencePath)), { recursive: true })
    writeFileSync(resolve(evidencePath), JSON.stringify({ ...evidence, argv: process.argv }, null, 2))
  } catch { /* preserve the original launch error */ }
}

if (smoke) {
  evidence.startup = 'main module loaded'
  writeEvidence()
  process.on('uncaughtException', error => {
    evidence.passed = false
    evidence.error = error.stack || error.message
    writeEvidence()
    app.exit(1)
  })
  process.on('unhandledRejection', error => {
    evidence.passed = false
    evidence.error = error?.stack || String(error)
    writeEvidence()
    app.exit(1)
  })
}

function resolveDataRoot() {
  if (explicitDataRoot) return resolve(explicitDataRoot)
  if (!process.env.LOCALAPPDATA) throw new Error('Windows LocalAppData is unavailable')
  return join(process.env.LOCALAPPDATA, 'NoRiichiNoFuku')
}

function enginePath() {
  const candidate = join(__dirname, 'engine', 'no-riichi-engine.exe')
  if (!existsSync(candidate)) throw new Error('bundled local engine is missing')
  return candidate
}

function engineEnvironment() {
  return {
    ...process.env,
    PATH: process.env.SystemRoot ? join(process.env.SystemRoot, 'System32') : '',
    PYTHONPATH: '',
    PYTHONHOME: '',
  }
}

async function waitFor(check, timeoutMs = 45000) {
  const until = Date.now() + timeoutMs
  while (Date.now() < until) {
    const result = await check()
    if (result) return result
    await delay(50)
  }
  throw new Error('local engine startup timed out')
}

function readMessage(childProcess, wantedType, timeoutMs = 30000) {
  return new Promise((resolveMessage, rejectMessage) => {
    const timeout = setTimeout(() => {
      childLines.removeListener('message', onMessage)
      rejectMessage(new Error(`local engine ${wantedType} response timed out`))
    }, timeoutMs)
    const onMessage = message => {
      if (message.type !== wantedType) return
      clearTimeout(timeout)
      childLines.removeListener('message', onMessage)
      resolveMessage(message)
    }
    childLines.on('message', onMessage)
    childProcess.once('close', (code, signal) => {
      clearTimeout(timeout)
      childLines.removeListener('message', onMessage)
      rejectMessage(new Error(`local engine exited before ${wantedType} (code=${code}, signal=${signal})`))
    })
  })
}

async function spawnEngine(root, port = 0) {
  if (child) throw new Error('host already owns a local engine')
  const identity = randomUUID()
  const processChild = spawn(enginePath(), ['--data', root, '--identity', identity, '--port', String(port)], {
    cwd: root,
    windowsHide: true,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: engineEnvironment(),
  })
  const lines = readline.createInterface({ input: processChild.stdout, crlfDelay: Infinity })
  childLines = lines
  lines.on('line', line => {
    try { lines.emit('message', JSON.parse(line)) } catch { /* stderr is the only diagnostic channel */ }
  })
  let stderr = ''
  processChild.stderr.on('data', chunk => { stderr = (stderr + chunk.toString('utf8')).slice(-4000) })
  processChild.on('error', error => lines.emit('message', { type: 'spawn-error', detail: error.message }))
  const record = { process: processChild, lines, stderr: () => stderr }
  child = record
  try {
    const ready = await readMessage(processChild, 'ready')
    if (ready.identity !== identity || ready.pid !== processChild.pid || !Number.isInteger(ready.port)) {
      throw new Error('local engine identity/port readiness check failed')
    }
    const candidateOrigin = `http://127.0.0.1:${ready.port}`
    const health = await waitFor(async () => {
      try {
        const [identityResponse, healthResponse, uiResponse] = await Promise.all([
          fetch(`${candidateOrigin}/_local/identity`), fetch(`${candidateOrigin}/api/health`),
          fetch(`${candidateOrigin}/`),
        ])
        if (!identityResponse.ok || !healthResponse.ok || !uiResponse.ok) return false
        const [identityBody, healthBody, uiHtml] = await Promise.all([
          identityResponse.json(), healthResponse.json(), uiResponse.text(),
        ])
        if (identityBody.identity !== identity) throw new Error('a foreign loopback listener answered readiness')
        return healthBody.status === 'ok' && uiHtml.includes('<div id="root">')
      } catch (error) {
        if (error.message === 'a foreign loopback listener answered readiness') throw error
        return false
      }
    })
    if (!health) throw new Error('local engine health check failed')
    processChild.stdin.write(`${JSON.stringify({ type: 'capability' })}\n`)
    const privateMessage = await readMessage(processChild, 'capability')
    if (typeof privateMessage.value !== 'string' || privateMessage.value.length < 32) {
      throw new Error('local engine private channel did not provide a capability')
    }
    origin = candidateOrigin
    capability = privateMessage.value
    return ready
  } catch (error) {
    await stopSpecificChild(record, 5000).catch(() => {})
    if (child === record) child = undefined
    throw new Error(`${error.message}${stderr ? `; ${stderr}` : ''}`)
  }
}

async function verifyDuplicateEngineIsRejected(root) {
  const duplicate = spawn(enginePath(), ['--data', root, '--identity', randomUUID(), '--port', '0'], {
    cwd: root,
    windowsHide: true,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: engineEnvironment(),
  })
  duplicate.stdin.end()
  const code = await new Promise((resolveExit, rejectExit) => {
    const timeout = setTimeout(() => { duplicate.kill(); rejectExit(new Error('duplicate engine did not exit')) }, 10000)
    duplicate.once('close', exitCode => { clearTimeout(timeout); resolveExit(exitCode) })
    duplicate.once('error', rejectExit)
  })
  if (code === 0) throw new Error('duplicate engine acquired an already-owned data root')
}

async function stopSpecificChild(record, timeoutMs = 15000) {
  if (record.process.exitCode !== null || record.process.signalCode !== null) return false
  const closed = new Promise(resolveClosed => record.process.once('close', resolveClosed))
  let forced = false
  try { record.process.stdin.write(`${JSON.stringify({ type: 'shutdown' })}\n`) } catch { /* process already closing */ }
  try {
    await Promise.race([closed, delay(timeoutMs).then(() => { throw new Error('graceful shutdown timed out') })])
  } catch {
    forced = true
    record.process.kill()
    await Promise.race([closed, delay(10000)])
    if (record.process.exitCode === null && record.process.signalCode === null) {
      throw new Error('owned local engine could not be reaped')
    }
  } finally {
    record.lines.close()
  }
  return forced
}

async function stopEngine() {
  const owned = child
  if (!owned) return
  const forced = await stopSpecificChild(owned)
  if (forced && smoke) throw new Error('owned local engine required forced termination')
  if (forced) evidence.shutdownForced = true
  child = undefined
  capability = undefined
}

function configureRequestBoundary() {
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    const allowed = origin && (details.url.startsWith(`${origin}/`) || details.url.startsWith(`${origin.replace('http:', 'ws:')}/`))
    if (!allowed && details.webContentsId === window?.webContents.id && details.url.startsWith('https://example.com/')) {
      rendererExternalRequestBlocked = true
    }
    callback({ cancel: !allowed })
  })
  session.defaultSession.webRequest.onBeforeSendHeaders((details, callback) => {
    const isApiOrigin = origin && (details.url.startsWith(`${origin}/api/`) || details.url.startsWith(`${origin.replace('http:', 'ws:')}/api/`))
    if (isApiOrigin && details.webContentsId === window?.webContents.id && capability) {
      details.requestHeaders['X-Local-Capability'] = capability
    }
    callback({ requestHeaders: details.requestHeaders })
  })
}

function makeWindow(show = true) {
  window = new BrowserWindow({
    show,
    width: 1360,
    height: 960,
    minWidth: 1000,
    minHeight: 720,
    webPreferences: {
      preload: join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  })
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('console-message', (_event, level, message) => {
    evidence.rendererConsole = [...(evidence.rendererConsole || []), { level, message }].slice(-30)
    writeEvidence()
  })
  window.webContents.on('render-process-gone', (_event, details) => {
    evidence.rendererGone = details
    writeEvidence()
  })
  window.webContents.on('will-navigate', (event, url) => {
    if (!origin || !url.startsWith(`${origin}/`)) event.preventDefault()
  })
  window.on('close', event => {
    if (quitting || closeRequested) return
    event.preventDefault()
    closeRequested = true
    void finishQuit()
  })
  return window
}

async function loadApplication() {
  await window.loadURL(origin)
}

async function waitForRenderer(expression, timeoutMs = 60000) {
  return waitFor(async () => {
    try { return await window.webContents.executeJavaScript(expression) } catch { return false }
  }, timeoutMs)
}

async function rendererSnapshot() {
  return window.webContents.executeJavaScript(`(() => ({
    table: (() => { const node = document.querySelector('.mahjong-table')?.cloneNode(true); node?.querySelectorAll('.speech-bubble').forEach(item => item.remove()); return node?.innerText ?? '' })(),
    hand: document.querySelector('.hand')?.innerText ?? '',
    round: document.querySelector('.round-status')?.innerText ?? '',
    result: document.querySelector('.match-result')?.innerText ?? '',
  }))()`)
}

async function clickHumanAction() {
  await waitForRenderer("document.querySelector('.human-controls .hand button:not([disabled])') || document.querySelector('.human-controls .action-bar button:not([disabled])')", 90000)
  const before = await rendererSnapshot()
  await window.webContents.executeJavaScript("(document.querySelector('.human-controls .hand button:not([disabled])') || document.querySelector('.human-controls .action-bar button:not([disabled])'))?.click()")
  await waitFor(async () => {
    const next = await rendererSnapshot()
    return next.result || (next.table !== before.table || next.hand !== before.hand || next.round !== before.round) ? next : false
  }, 90000)
}

async function startMatchFromRenderer() {
  evidence.phase = 'click new match'
  writeEvidence()
  await window.webContents.executeJavaScript(`(() => {
    document.querySelector('.match-result button')?.click()
  })()`)
  await waitForRenderer("Boolean(document.querySelector('.selection-panel'))", 90000)
  await window.webContents.executeJavaScript(`(() => {
    Array.from(document.querySelectorAll('button.cpu-card:not([disabled])')).slice(0, 3).forEach(button => button.click())
  })()`)
  evidence.phase = 'wait for three CPU selections to render'
  writeEvidence()
  await waitForRenderer("document.querySelectorAll('button.cpu-card.selected').length === 3 && document.querySelector('button.start-button:not([disabled])')", 30000)
  evidence.phase = 'click enabled match start'
  writeEvidence()
  await window.webContents.executeJavaScript("document.querySelector('button.start-button:not([disabled])')?.click()")
  await waitForRenderer("Boolean(document.querySelector('.human-controls') || document.querySelector('.match-result'))", 90000)
}

async function smokePreflight() {
  evidence.smokeStarted = true
  evidence.phase = 'preflight before engine startup'
  writeEvidence()
  const scratch = join(dataRoot, 'w05-ci-scratch')
  mkdirSync(scratch, { recursive: true })
  const stuckChild = spawn('ping.exe', ['-t', '127.0.0.1'], {
    windowsHide: true,
    stdio: ['pipe', 'ignore', 'ignore'],
  })
  await new Promise((resolveSpawn, rejectSpawn) => {
    stuckChild.once('spawn', resolveSpawn)
    stuckChild.once('error', rejectSpawn)
  })
  const forcedStop = await stopSpecificChild({ process: stuckChild, lines: { close() {} } }, 150)
  if (!forcedStop || (stuckChild.exitCode === null && stuckChild.signalCode === null)) {
    throw new Error('owned child shutdown fallback did not reap the exact child')
  }
  addCheck('nonresponsive owned child was force-reaped after graceful timeout')

  const failingRoot = join(scratch, 'not-a-directory')
  writeFileSync(failingRoot, 'owned test input')
  let readyFailure = false
  try { await spawnEngine(failingRoot) } catch { readyFailure = true }
  if (!readyFailure) throw new Error('ready failure injection unexpectedly started')
  addCheck('ready failure surfaced and engine child reaped')

  const occupied = createServer()
  await new Promise((resolveListen, rejectListen) => occupied.once('error', rejectListen).listen(0, '127.0.0.1', resolveListen))
  const occupiedPort = occupied.address().port
  let collisionRejected = false
  try { await spawnEngine(join(scratch, 'collision-data'), occupiedPort) } catch { collisionRejected = true }
  if (!collisionRejected || !occupied.listening) throw new Error('port collision affected an unrelated listener')
  addCheck('occupied port rejected; unrelated listener remained open')
  await new Promise(resolveClose => occupied.close(resolveClose))
}

async function smokeRun() {
  evidence.phase = 'renderer smoke'
  writeEvidence()
  await verifyDuplicateEngineIsRejected(dataRoot)
  addCheck('duplicate engine could not acquire the active local data root')
  makeWindow(false)
  await loadApplication()
  await waitForRenderer("Boolean(document.querySelector('.selection-panel') || document.querySelector('.human-controls') || document.querySelector('.match-result'))")
  if (await window.webContents.executeJavaScript("document.body.innerText.includes('로그인') || document.body.innerText.includes('새 회원으로 시작')")) {
    throw new Error('desktop renderer showed web login')
  }
  addCheck('same-origin React loaded without login')
  const externalBlocked = await window.webContents.executeJavaScript(
    "fetch('https://example.com').then(() => false, () => true)",
  )
  if (!externalBlocked || !rendererExternalRequestBlocked) throw new Error('renderer external network request was not blocked')
  addCheck('renderer external request cancelled by host; OS-level offline was not simulated')

  const profileName = 'W05 검증 플레이어'
  await window.webContents.executeJavaScript(`(() => {
    const input = document.querySelector('.profile-editor input')
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
    setter.call(input, ${JSON.stringify(profileName)})
    input.dispatchEvent(new Event('input', { bubbles: true }))
    document.querySelector('.profile-editor button')?.click()
  })()`)
  const saved = await waitFor(async () => {
    const profile = await fetch(`${origin}/api/profile/me`, { headers: { 'X-Local-Capability': capability } }).then(response => response.json())
    return profile.player_name === profileName ? profile : false
  })
  if (saved.player_name !== profileName || saved.role !== 'member') throw new Error('local profile name update failed')
  addCheck('renderer name editor persisted the local profile')

  evidence.phase = 'inspect saved renderer match state'
  writeEvidence()
  const hasActiveOrResult = await window.webContents.executeJavaScript("Boolean(document.querySelector('.human-controls') || document.querySelector('.match-result'))")
  if (!hasActiveOrResult) {
    await startMatchFromRenderer()
  }
  await waitForRenderer("Boolean(document.querySelector('.human-controls') || document.querySelector('.match-result'))", 90000)
  if (await window.webContents.executeJavaScript("Boolean(document.querySelector('.human-controls'))")) {
    let recoveryCheckpoint = false
    for (let attempt = 0; attempt < 5 && !recoveryCheckpoint; attempt += 1) {
      for (let action = 0; action < 12; action += 1) {
        if (await window.webContents.executeJavaScript("Boolean(document.querySelector('.match-result'))")) break
        await clickHumanAction()
      }
      if (await window.webContents.executeJavaScript("Boolean(document.querySelector('.match-result'))")) {
        if (attempt < 4) await startMatchFromRenderer()
        continue
      }
      recoveryCheckpoint = true
    }
    if (!recoveryCheckpoint) throw new Error('normal matches ended before the active-recovery checkpoint could be exercised')
    const before = await rendererSnapshot()
    window.destroy()
    window = undefined
    await delay(100)
    await stopEngine()
    await spawnEngine(dataRoot)
    makeWindow(false)
    await loadApplication()
    await waitForRenderer("Boolean(document.querySelector('.human-controls'))")
    const after = await rendererSnapshot()
    if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('active match did not restore the same renderer state')
    addCheck('active match restored after engine shutdown/restart at committed turn')
    let turns = 0
    while (!(await window.webContents.executeJavaScript("Boolean(document.querySelector('.match-result'))")) && turns < 600) {
      await clickHumanAction()
      turns += 1
    }
    if (!(await window.webContents.executeJavaScript("Boolean(document.querySelector('.match-result h2'))"))) {
      throw new Error('real renderer match did not complete')
    }
    addCheck('real renderer completed a normal local match')
  }

  const resultBefore = await window.webContents.executeJavaScript("document.querySelector('.match-result')?.innerText ?? ''")
  window.destroy()
  window = undefined
  await delay(100)
  await stopEngine()
  await spawnEngine(dataRoot)
  makeWindow(false)
  await loadApplication()
  await waitForRenderer("Boolean(document.querySelector('.match-result h2'))", 90000)
  const resultAfter = await window.webContents.executeJavaScript("document.querySelector('.match-result')?.innerText ?? ''")
  if (resultBefore !== resultAfter) throw new Error('completed result changed after engine restart')
  addCheck('completed result reconnected after engine restart without duplicate settlement')
  evidence.passed = true
  evidence.phase = 'smoke passed; closing host'
  writeEvidence()
  window.close()
}

async function finishQuit() {
  if (quitting) return
  quitting = true
  if (window && !window.isDestroyed()) {
    window.destroy()
    window = undefined
    await delay(100)
  }
  const hadOwnedEngine = Boolean(child)
  try {
    await stopEngine()
    if (smoke && hadOwnedEngine) addCheck('window close gracefully stopped the owned local engine')
  } catch (error) {
    evidence.shutdownError = error.message
    if (smoke) evidence.passed = false
  }
  writeEvidence()
  if (smoke) app.exit(evidence.passed ? 0 : 1)
  else app.quit()
}

try {
  dataRoot = resolveDataRoot()
  const electronData = join(dataRoot, 'config', 'electron')
  mkdirSync(electronData, { recursive: true })
  app.setPath('userData', electronData)
} catch (error) {
  bootstrapError = error
}

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) app.quit()
else {
  app.on('window-all-closed', () => {
    evidence.windowAllClosed = true
    writeEvidence()
    if (!smoke && process.platform !== 'darwin') app.quit()
  })
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.focus() } })
  app.whenReady().then(async () => {
    try {
      evidence.startup = 'app ready'
      writeEvidence()
      if (bootstrapError) throw bootstrapError
      mkdirSync(dataRoot, { recursive: true })
      if (smoke) await smokePreflight()
      await spawnEngine(dataRoot)
      evidence.startup = 'engine ready'
      writeEvidence()
      configureRequestBoundary()
      makeWindow(!smoke)
      await loadApplication()
      evidence.startup = 'renderer loaded'
      writeEvidence()
      if (smoke) {
        await smokeRun()
        await finishQuit()
      }
    } catch (error) {
      if (smoke) {
        evidence.passed = false
        evidence.error = error.stack || error.message
        await finishQuit()
      } else {
        dialog.showErrorBox('No Riichi No Fuku 시작 실패', error.message)
        await finishQuit()
      }
    }
  })
  app.on('before-quit', event => {
    if (quitting) return
    event.preventDefault()
    void finishQuit()
  })
}
