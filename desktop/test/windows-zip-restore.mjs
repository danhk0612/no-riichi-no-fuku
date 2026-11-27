import { enterDesktopGame } from '../../frontend/tests/desktop-menu.mjs'
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
    await enterDesktopGame(page)
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
    const product = dirname(exe)
    const notices = join(product, 'resources', 'app', 'notices')
    assert.ok(existsSync(join(product, '시작하기.txt')))
    assert.ok(existsSync(join(product, 'LICENSES.chromium.html')))
    assert.ok(existsSync(join(notices, 'Python-LICENSE.txt')))
    assert.match(readFileSync(join(notices, 'frontend-licenses.md'), 'utf8'), /react-dom/)
    assert.match(readFileSync(join(notices, 'engine-packages.txt'), 'utf8'), /^riichienv 0\.4\.8 \| [1-9]/m)
  }
  let expected
  await withGame(firstExe, initial, async page => {
    await page.getByRole('button',{name:'설정',exact:true}).click()
    await page.getByRole('button', { name: '캐릭터 프롬프트·팩 설정', exact: true }).click()
    const editor = page.getByRole('region', { name: '캐릭터 프롬프트와 팩 관리' })
    await editor.getByRole('combobox', { name: '캐릭터', exact: true }).selectOption('1')
    const appearance = editor.getByRole('group', { name: '외모', exact: true }).locator('textarea').first()
    assert.match(await appearance.inputValue(), /auburn/)
    await editor.getByRole('button', { name: '캐릭터 추가' }).click()
    await editor.getByLabel('새 캐릭터 이름').fill('추가 캐릭터')
    await editor.getByRole('button', { name: '추가하기' }).click()
    await page.waitForFunction(() => document.querySelector('select[aria-label="캐릭터"]')?.selectedOptions[0]?.textContent.includes('추가 캐릭터'))
    assert.match(await appearance.inputValue(), /brown hair/)
    await editor.getByRole('button', { name: '이름 변경' }).click()
    await editor.getByLabel('변경할 이름').fill('다시 만난 캐릭터')
    await editor.getByRole('button', { name: '캐릭터 이름 저장' }).click()
    await page.getByRole('button', { name: '게임 화면으로' }).click()
    await page.locator('button.cpu-card').filter({ hasText: '다시 만난 캐릭터' }).waitFor()
    await page.getByRole('button',{name:'설정',exact:true}).click()
    await page.locator('.profile-editor input').fill('배포 복구 확인')
    await page.locator('.profile-editor button').click()
    await page.waitForFunction(async () => (await (await fetch('/api/profile/me')).json()).player_name === '배포 복구 확인')
    await page.getByRole('button',{name:'게임 화면으로',exact:true}).click()
    await page.locator('.cpu-preview').waitFor()
    await page.screenshot({ path: join(dirname(evidence), 'selection-screen.png') })
    {
      const action = '참가 명단 확정'
      const start = page.getByRole('button', { name: action, exact: true })
      await start.waitFor()
      await page.locator('button.cpu-card').filter({ hasText: '다시 만난 캐릭터' }).click()
      for (let i = 0; i < 2; i++) await page.locator('button.cpu-card:not(.selected):enabled').first().click()
      await start.click()
    }
    expected = await snapshot(page)
    const controls = page.getByRole('region', { name: '플레이어 행동' })
    for (const width of [1280, 680]) {
      await page.setViewportSize({ width, height: 800 })
      await controls.locator('.hand .tile').first().waitFor()
      const layout = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth,
        seats: document.querySelectorAll('.mahjong-table .seat').length,
        missingNames: [...document.querySelectorAll('.hand button.tile')].some(tile => !tile.getAttribute('aria-label')),
        visibleHint: document.querySelector('.hand-heading [role=status]')?.textContent?.trim()
      }))
      assert.equal(layout.seats, 4)
      assert.equal(layout.overflow, false, 'page overflow at ' + width)
      assert.equal(layout.missingNames, false)
      assert.ok(layout.visibleHint)
      const faceSize = await controls.locator('.tile-art').first().evaluate(async face => {
        const image = new Image()
        image.src = getComputedStyle(face).backgroundImage.slice(5, -2)
        await image.decode()
        return [image.naturalWidth, image.naturalHeight]
      })
      assert.deepEqual(faceSize, [3552, 112])
      await page.locator('.mahjong-table').screenshot({ path: join(dirname(evidence), 'table-' + width + '.png') })
      await controls.screenshot({ path: join(dirname(evidence), 'hand-' + width + '.png') })
    }
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
