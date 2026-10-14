// Isolated W02 probe. No production imports or policy changes.
const { app, BrowserWindow, dialog, session } = require('electron')
const { spawn, spawnSync } = require('node:child_process')
const { mkdtempSync, readFileSync, writeFileSync, existsSync } = require('node:fs')
const { tmpdir } = require('node:os')
const { join } = require('node:path')
const { randomUUID } = require('node:crypto')
const { createServer } = require('node:net')
const assert = require('node:assert/strict')
const smoke = process.argv.includes('--smoke')
const data = mkdtempSync(join(tmpdir(), 'nrnf-w02-'))
app.setPath('userData', join(data, 'electron'))
const binary = join(__dirname, 'engine', 'w02-engine.exe')
const evidence = { platform: process.platform, arch: process.arch, versions: process.versions,
  smoke, data, internet: 'not blocked at OS level; renderer non-loopback requests denied', lifecycle: [], measurements: [] }
let owned, window, stopping = false, origin, foreign
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
const save = () => writeFileSync(join(data, 'evidence.json'), JSON.stringify(evidence, null, 2))
async function until(check, ms = 60000) {
  const deadline = Date.now() + ms
  while (!await check()) {
    if (Date.now() >= deadline) throw new Error('W02 wait timed out')
    await delay(50)
  }
}
async function start(port = 0) {
  const identity = randomUUID(), ready = join(data, `${identity}.json`), started = Date.now()
  const child = spawn(binary, ['serve', '--data', data, '--ready', ready, '--identity', identity,
    '--port', String(port), ...(smoke ? ['--smoke'] : [])],
    { cwd: data, windowsHide: true, env: { ...process.env, PATH: process.env.SystemRoot + '\\System32', PYTHONPATH: '', PYTHONHOME: '' } })
  let log = '', failure
  child.on('error', error => { failure = error })
  child.stdout.on('data', chunk => { log += chunk })
  child.stderr.on('data', chunk => { log += chunk })
  child.testLog = () => log
  owned = child
  await until(async () => {
    if (failure) throw failure
    if (child.exitCode !== null) throw new Error(log || `engine exit ${child.exitCode}`)
    if (!existsSync(ready)) return false
    let record
    try { record = JSON.parse(readFileSync(ready, 'utf8')) } catch { return false }
    assert.equal(record.identity, identity)
    assert.equal(record.pid, child.pid)
    origin = `http://127.0.0.1:${record.port}`
    try {
      const actual = await (await fetch(origin + '/_spike/identity')).json()
      if (actual.identity !== identity) throw new Error('foreign engine identity')
      assert.deepEqual(await (await fetch(origin + '/api/health')).json(), { status: 'ok' })
      return true
    } catch (error) { if (error.message === 'foreign engine identity') throw error; return false }
  })
  evidence.measurements.push({ readyMs: Date.now() - started, pid: child.pid, origin })
  return origin
}
async function stop() {
  if (!owned) return
  const child = owned
  const started = Date.now()
  child.stdin.end()
  let forced = false
  try { await until(() => child.exitCode !== null || child.signalCode !== null, 15000) }
  catch {
    forced = true
    child.kill() // This exact owned child only, never image-name/taskkill.
    await until(() => child.exitCode !== null || child.signalCode !== null, 10000)
  }
  evidence.lifecycle.push({ pid: child.pid, exit: child.exitCode, signal: child.signalCode,
    forced, stopMs: Date.now() - started, log: child.testLog() })
  owned = undefined
  if (smoke) assert.equal(forced, false, 'graceful shutdown failed')
}
function engineCommand(mode) {
  const result = spawnSync(binary, [mode, '--data', data], {
    cwd: data, encoding: 'utf8', windowsHide: true,
    env: { ...process.env, PATH: process.env.SystemRoot + '\\System32', PYTHONPATH: '', PYTHONHOME: '' } })
  assert.equal(result.status, 0, result.stderr || result.error?.message)
  return result.stdout
}
// Executed in sandboxed renderer: real same-origin REST + WS, no response mocks.
async function rendererBegin(register) {
  window.w02errors = []
  const credentials = { login_id: 'w02-member', password: 'w02-test-password' }
  async function rest(path, body) {
    const response = await fetch(path, { method: body ? 'POST' : 'GET',
      headers: { 'Content-Type': 'application/json', ...(window.w02token ? { Authorization: `Bearer ${window.w02token}` } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}) })
    if (!response.ok) throw new Error(`REST ${path}: ${response.status}`)
    return response.json()
  }
  window.w02rest = rest
  if (register) await rest('/api/auth/register', { ...credentials, player_name: 'W02' })
  window.w02token = (await rest('/api/auth/login', credentials)).access_token
  return true
}
async function rendererConnect(newMatch, id) {
  if (newMatch) {
    const cpus = await window.w02rest('/api/game/cpus')
    id = (await window.w02rest('/api/game/sessions', { cpu_character_ids: cpus.slice(0, 3).map(cpu => cpu.id) })).session_id
  }
  window.w02state = null
  window.w02socket = new WebSocket(`ws://${location.host}/api/game/sessions/${id}/ws`)
  window.w02socket.onopen = () => window.w02socket.send(JSON.stringify({ type: 'authenticate', access_token: window.w02token }))
  window.w02socket.onmessage = ({ data }) => {
    const message = JSON.parse(data)
    if (message.type === 'human_turn' || message.type === 'match_complete') window.w02state = message
    if (message.type === 'error') window.w02errors.push(message)
  }
  window.w02socket.onerror = () => window.w02errors.push('socket error')
  return id
}
const evaluate = (fn, ...args) => window.webContents.executeJavaScript(`(${fn.toString()})(${args.map(arg => JSON.stringify(arg)).join(',')})`)
const state = () => window.webContents.executeJavaScript('window.w02state')
async function load() {
  await window.loadURL(origin)
  assert.equal(new URL(window.webContents.getURL()).origin, origin)
  assert.ok(await window.webContents.executeJavaScript("document.querySelector('#root').children.length > 0"))
}
async function runSmoke() {
  // Occupied port: child must fail, and the unrelated listener must remain alive.
  foreign = createServer(socket => socket.end('foreign'))
  await new Promise(resolve => foreign.listen(0, '127.0.0.1', resolve))
  const port = foreign.address().port
  let rejected = false
  try { await start(port) } catch { rejected = true }
  assert.equal(rejected, true)
  await stop()
  assert.equal(foreign.listening, true)
  evidence.portCollision = 'rejected; unrelated listener survived'
  await start()
  await load()
  await evaluate(rendererBegin, true)
  // Only this marker-owned scratch DB is modified for the existing Tier2 scenario.
  engineCommand('promote')
  const id = await evaluate(rendererConnect, true, null)
  await until(async () => (await state())?.type === 'human_turn')
  let actions = 0, current = await state()
  while (current.type !== 'match_complete' && actions < 500) {
    if (actions === 12) {
      const before = current
      await window.webContents.executeJavaScript('window.w02socket.close()')
      await stop()
      await start()
      await load()
      await evaluate(rendererBegin, false)
      await evaluate(rendererConnect, false, id)
      await until(async () => (await state())?.type === 'human_turn')
      current = await state()
      assert.deepEqual(current, before)
      evidence.recoveredAfter12 = true
    }
    const version = current.action_version
    await window.webContents.executeJavaScript(`(() => {
      const legal = window.w02state.turn.legal_actions
      const index = [6,4,5,7,0].map(type => legal.findIndex(action => action.type === type)).find(index => index >= 0) ?? 0
      window.w02socket.send(JSON.stringify({ type: 'action', legal_action_index: index, action_version: window.w02state.action_version }))
    })()`)
    actions++
    await until(async () => { const next = await state(); return next?.type === 'match_complete' || next?.action_version !== version })
    current = await state()
  }
  assert.equal(current.type, 'match_complete')
  assert.equal(actions, 108)
  assert.deepEqual(current.result, { scores: [17000,27700,24700,30600], ranks: [4,2,3,1] })
  assert.deepEqual(await window.webContents.executeJavaScript('window.w02errors'), [])
  await window.webContents.executeJavaScript('window.w02socket.close()')
  await stop()
  const persisted = JSON.parse(engineCommand('inspect'))
  assert.equal(persisted.status, 'completed')
  assert.equal(persisted.actions, actions)
  assert.deepEqual(persisted.scores, current.result.scores)
  assert.deepEqual(persisted.ranks, current.result.ranks)
  assert.deepEqual(persisted.settlement, current.settlement)
  assert.equal(persisted.hp, 2)
  assert.ok(persisted.choices.every(choice => choice.policy_version === 2 && choice.defeat_stage === 2))
  assert.ok(Object.values(persisted.stages).every(stage => stage === 2))
  await start()
  await load()
  await evaluate(rendererBegin, false)
  await evaluate(rendererConnect, false, id)
  await until(async () => (await state())?.type === 'match_complete')
  assert.deepEqual(await state(), current)
  await window.webContents.executeJavaScript('window.w02socket.close()')
  await stop()
  assert.deepEqual(JSON.parse(engineCommand('inspect')), persisted)
  assert.equal(foreign.listening, true)
  evidence.match = { actions, ...current.result, settlement: current.settlement, completedRestart: true }
  evidence.passed = true
}
app.on('before-quit', event => {
  if (!stopping) { event.preventDefault(); finish(0) }
})
async function finish(code, error) {
  if (stopping) return
  stopping = true
  if (error) { evidence.passed = false; evidence.error = error.stack }
  try { await stop() } catch (error) { evidence.passed = false; evidence.stopError = error.stack; code = 1 }
  if (foreign) foreign.close()
  save()
  console.log(`W02 evidence: ${join(data, 'evidence.json')}`)
  if (process.env.W02_EVIDENCE) writeFileSync(process.env.W02_EVIDENCE, JSON.stringify(evidence, null, 2))
  if (error && !smoke) dialog.showErrorBox('W02 spike failed', error.message)
  app.exit(code)
}
app.whenReady().then(async () => {
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    const allowed = origin && (details.url.startsWith(origin + '/') || details.url.startsWith(origin.replace('http:', 'ws:') + '/'))
    callback({ cancel: !allowed })
  })
  window = new BrowserWindow({ show: !smoke, width: 1280, height: 900,
    webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true } })
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('will-navigate', (event, url) => { if (!origin || !url.startsWith(origin + '/')) event.preventDefault() })
  window.on('closed', () => finish(0))
  if (smoke) { await runSmoke(); await finish(0) }
  else { await start(); await load(); save() }
}).catch(error => finish(1, error))
