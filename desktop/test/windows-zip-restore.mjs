import assert from 'node:assert/strict'
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'

const { _electron } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const [firstExe, secondExe, scratch, evidence, source] = process.argv.slice(2)
const root = mkdtempSync(join(scratch, '배포 복구 '))
const initial = join(root, 'original')
const restored = join(root, 'restored')
const report = { source, checks: [], passed: false }
const record = check => {
  report.checks.push(check)
  writeFileSync(evidence, JSON.stringify(report, null, 2))
}

async function withGame(executablePath, localAppData, check) {
  mkdirSync(localAppData, { recursive: true })
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => key.toUpperCase() !== 'LOCALAPPDATA'))
  const app = await _electron.launch({ executablePath, env: { ...env, LOCALAPPDATA: localAppData }, timeout: 90000 })
  try {
    const page = await app.firstWindow({ timeout: 90000 })
    page.setDefaultTimeout(45000)
    await check(page)
  } finally {
    await app.close()
  }
}

async function snapshot(page) {
  await page.locator('.human-controls').waitFor()
  return page.evaluate(async () => {
    async function get(path) {
      const response = await fetch(path)
      if (!response.ok) throw Error(path + ' ' + response.status)
      return response.json()
    }
    const play = await get('/api/local/play')
    const profile = await get('/api/profile/me')
    return { name: profile.player_name, session: play.active_session_id, generation: play.generation, roster: play.roster }
  })
}

try {
  for (const exe of [firstExe, secondExe]) {
    assert.equal(readFileSync(join(dirname(exe), 'BUILD-SOURCE.txt'), 'utf8').trim(), source)
    assert.ok(existsSync(join(dirname(exe), '시작하기.txt')))
  }
  let expected
  await withGame(firstExe, initial, async page => {
    await page.locator('.profile-editor input').fill('배포 복구 확인')
    await page.locator('.profile-editor button').click()
    await page.waitForFunction(async () => (await (await fetch('/api/profile/me')).json()).player_name === '배포 복구 확인')
    for (const action of ['참가 명단 확정', '동풍전 시작']) {
      const start = page.getByRole('button', { name: action, exact: true })
      await start.waitFor()
      for (let i = 0; i < 3; i++) await page.locator('button.cpu-card:not(.selected):enabled').first().click()
      await start.click()
    }
    expected = await snapshot(page)
    assert.equal(expected.name, '배포 복구 확인')
    assert.ok(expected.session && expected.generation)
    assert.equal(expected.roster.length, 3)
  })
  const folder = 'NoRiichiNoFuku'
  assert.ok(existsSync(join(initial, folder, 'game.db')))
  record('first extracted EXE saved profile, roster and active match in default LocalAppData')
  const backup = join(root, 'backup', folder)
  cpSync(join(initial, folder), backup, { recursive: true })
  await withGame(secondExe, initial, async page => assert.deepEqual(await snapshot(page), expected))
  record('second extraction reopened the same profile and active match')
  cpSync(backup, join(restored, folder), { recursive: true })
  await withGame(secondExe, restored, async page => assert.deepEqual(await snapshot(page), expected))
  report.passed = true
  record('closed-game backup restored into a fresh LocalAppData and resumed the same match')
} catch (error) {
  report.error = String(error.stack || error)
  writeFileSync(evidence, JSON.stringify(report, null, 2))
  throw error
}
