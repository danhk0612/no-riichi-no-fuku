// Owns local test processes and a temporary DB. No routed/mocked responses or media files.
import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { mkdtempSync, rmSync } from 'node:fs'
import { createRequire } from 'node:module'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const backend = resolve(frontend, '../backend')
const python = process.env.TEST_PYTHON || 'python3'
const temporary = mkdtempSync(resolve(tmpdir(), 'nrnf-live-'))
const env = {
  ...process.env,
  DATABASE_URL: `sqlite+pysqlite:///${temporary}/game.db`,
  MEDIA_ROOT: `${temporary}/media`,
  JWT_SECRET: randomUUID(),
  SUPERADMIN_LOGIN_ID: 'integration-admin',
  SUPERADMIN_INITIAL_PASSWORD: randomUUID(),
}
const children = new Set()
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
async function until(predicate) {
  const deadline = Date.now() + 15000
  while (!await predicate()) {
    if (Date.now() > deadline) throw new Error('integration wait timed out')
    await delay(25)
  }
}
function runPython(code) {
  const result = spawnSync(python, ['-c', code], { cwd: backend, env, encoding: 'utf8' })
  assert.equal(result.status, 0, result.stderr || result.error?.message)
  return result.stdout
}
function start(command, args, cwd) {
  const child = spawn(command, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] })
  children.add(child)
  let log = ''
  for (const stream of [child.stdout, child.stderr]) stream.on('data', (chunk) => { log = (log + chunk).slice(-8000) })
  child.on('error', (error) => { log += error.message })
  child.testLog = () => log
  return child
}
async function stop(child) {
  if (child.exitCode === null) {
    child.kill('SIGTERM')
    await until(() => child.exitCode !== null || child.signalCode !== null)
  }
  children.delete(child)
}
async function unusedPort(port) {
  await new Promise((resolve, reject) => {
    const probe = createServer()
    probe.once('error', () => reject(new Error(`test requires unused local port ${port}`)))
    probe.listen(port, '127.0.0.1', () => probe.close(resolve))
  })
}
async function ready(child, url) {
  await until(async () => {
    if (child.exitCode !== null) throw new Error(child.testLog())
    try { return (await fetch(url)).ok } catch { return false }
  })
}
function startApi() {
  return start(python, ['-c', `
from app.main import app
from app.services.game_registry import GameRegistry, get_game_registry
import uvicorn
registry = GameRegistry(seed_factory=lambda: 5)
app.dependency_overrides[get_game_registry] = lambda: registry
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
`], backend)
}
let browser
try {
  await unusedPort(8000)
  await unusedPort(5193)
  runPython(`from alembic.config import Config
from alembic import command
command.upgrade(Config("alembic.ini"), "head")
from app.bootstrap import main
main()`)
  let api = startApi()
  await ready(api, 'http://127.0.0.1:8000/api/health')
  const vite = start(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5193', '--strictPort'], frontend)
  await ready(vite, 'http://127.0.0.1:5193')
  browser = await chromium.launch({ headless: true, executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
  const page = await browser.newPage()
  page.setDefaultTimeout(10000)
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  let state
  let websocketUrl
  let token
  page.on('response', async (response) => {
    if (new URL(response.url()).pathname === '/api/auth/login' && response.ok()) token = (await response.json()).access_token
  })
  page.on('websocket', (socket) => {
    websocketUrl = socket.url()
    socket.on('framereceived', ({ payload }) => {
      const message = JSON.parse(payload.toString())
      if (message.type === 'human_turn' || message.type === 'match_complete') state = message
      if (message.type === 'error') errors.push(message.code)
    })
  })
  await page.goto('http://127.0.0.1:5193')
  await page.getByRole('button', { name: '새 회원으로 시작' }).click()
  await page.getByLabel('로그인 ID').fill('live-member')
  await page.getByLabel('플레이어 이름').fill('통합검증')
  await page.getByLabel('비밀번호', { exact: true }).fill('integration-password')
  await page.getByRole('button', { name: '가입 후 로그인' }).click()
  await page.locator('.selection-panel').waitFor()
  // Seed test progress only in this owned temporary DB, then reload choices through login.
  runPython(`from app.core.config import Settings
from app.db.session import create_database_engine,create_session_factory
from app.db.models import UserCpuProgress
from sqlalchemy import select
factory=create_session_factory(create_database_engine(Settings().require_database_url()))
with factory.begin() as db:
 for progress in db.scalars(select(UserCpuProgress)):
  progress.defeat_stage=2`)
  async function login() {
    await page.getByLabel('로그인 ID').fill('live-member')
    await page.getByLabel('비밀번호', { exact: true }).fill('integration-password')
    await page.getByRole('button', { name: '로그인', exact: true }).click()
  }
  await page.getByRole('button', { name: '로그아웃' }).click()
  await login()
  await page.locator('.selection-panel').waitFor()
  for (const index of [0, 1, 2]) await page.locator('.cpu-card').nth(index).click()
  await page.getByRole('button', { name: '동풍전 시작' }).click()
  await until(() => state?.type === 'human_turn')
  const sessionUrl = websocketUrl
  let actions = 0
  while (state.type !== 'match_complete' && actions < 500) {
    if (actions === 12) {
      const beforeRestart = structuredClone(state)
      await stop(api)
      await page.getByRole('alert').filter({ hasText: '새로고침 후 다시 로그인' }).waitFor()
      assert.equal(await page.locator('.human-controls button:enabled').count(), 0)
      api = startApi()
      await ready(api, 'http://127.0.0.1:8000/api/health')
      state = null
      await page.reload()
      await login()
      await until(() => state?.type === 'human_turn')
      assert.equal(websocketUrl, sessionUrl)
      assert.deepEqual(state, beforeRestart)
      console.log('PASS: process restart recovered the identical authoritative turn after 12 actions')
    }
    const current = state
    const legal = current.turn.legal_actions
    const index = [6, 4, 5, 7, 0].map((type) => legal.findIndex((action) => action.type === type)).find((index) => index >= 0) ?? 0
    const action = legal[index]
    await page.locator('.human-controls').waitFor()
    if (action.type === 0) {
      await page.locator('.hand .tile').nth(current.turn.observation.hands[0].indexOf(action.tile)).click()
    } else {
      await page.locator('.action-bar button').nth(legal.slice(0, index).filter((action) => action.type !== 0).length).click()
    }
    actions += 1
    await until(() => state !== current)
  }
  assert.equal(state.type, 'match_complete')
  await page.locator('.match-result').waitFor()
  assert.equal(await page.locator('.match-result li').count(), 4)
  const readPersisted = () => JSON.parse(runPython(`import json
from app.core.config import Settings
from app.db.session import create_database_engine,create_session_factory
from app.db.models import GameSessionRecord,User,UserCpuProgress
from sqlalchemy import select
factory=create_session_factory(create_database_engine(Settings().require_database_url()))
with factory() as db:
 record=db.scalar(select(GameSessionRecord))
 user=db.get(User,record.user_id)
 print(json.dumps(dict(status=record.status,scores=record.scores,ranks=record.ranks,settlement=record.settlement,actions=len(record.human_action_indices),choices=record.cpu_choices,hp=user.current_hp,stages={p.cpu_character_id:p.defeat_stage for p in db.scalars(select(UserCpuProgress))})))`))
  const persisted = readPersisted()
  assert.equal(persisted.status, 'completed')
  assert.deepEqual(persisted.scores, state.result.scores)
  assert.deepEqual(persisted.ranks, state.result.ranks)
  assert.deepEqual(persisted.settlement, state.settlement)
  assert.equal(persisted.actions, actions)
  assert.ok(persisted.choices.every((choice) => choice.policy_version === 2 && choice.defeat_stage === 2))
  assert.equal(persisted.hp, state.settlement.current_hp)
  for (const [id, stage] of Object.entries(persisted.stages)) assert.equal(stage, Number(id) === state.settlement.cpu_character_id ? 3 : 2)
  // Restart again and reopen the completed match; DB settlement must stay unchanged.
  await stop(api)
  api = startApi()
  await ready(api, 'http://127.0.0.1:8000/api/health')
  const again = await page.evaluate(async ({ url, token }) => new Promise((resolve, reject) => {
    const ws = new WebSocket(url)
    ws.onopen = () => ws.send(JSON.stringify({ type: 'authenticate', access_token: token }))
    ws.onmessage = ({ data }) => {
      const message = JSON.parse(data)
      if (message.type === 'match_complete') { ws.close(); resolve(message) }
      else if (message.type === 'error') { ws.close(); reject(new Error(message.code)) }
    }
    ws.onerror = () => reject(new Error('completed reconnect failed'))
  }), { url: sessionUrl, token })
  assert.deepEqual(again, state)
  assert.deepEqual(readPersisted(), persisted)
  await page.getByRole('button', { name: '다음 대국 선택' }).click()
  await page.locator('.selection-panel').waitFor()
  assert.equal(await page.locator('.cpu-card').count(), state.settlement.cpu_completed ? 5 : 6)
  assert.deepEqual(errors, [])
  console.log(JSON.stringify({ actions, scores: state.result.scores, ranks: state.result.ranks, settlement: state.settlement }))
  console.log('PASS: real signup, Tier2 selection, Vite proxy match, restart recovery, durable result and next selection')
} finally {
  if (browser) await browser.close()
  for (const child of children) await stop(child)
  rmSync(temporary, { recursive: true, force: true })
}
