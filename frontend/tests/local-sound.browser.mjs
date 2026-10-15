import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
try {
  const page = await browser.newPage()
  page.setDefaultTimeout(8000)
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.addInitScript(() => {
    window.nrnfDesktop = { isDesktop: true }
    window.__soundPlayCount = 0
    HTMLMediaElement.prototype.play = function () { window.__soundPlayCount += 1; return Promise.resolve() }
  })
  const play = {
    generation: 'sound-test-generation', phase: 'omake',
    roster: [1, 2, 3].map((cpu_character_id) => ({ cpu_character_id, defeat_stage: 3 })),
    ending_event_id: 'ending-1', ending_payload: null, active_session_id: null,
    recent_session_id: null, legacy_active: false,
  }
  const cpus = [1, 2, 3].map((id) => ({ id, name: `CPU ${id}`, defeat_stage: 3, style: 'balanced', short_description: 'fixture', profile_image_key: null }))
  let selection = { effect_set_id: null, bgm_ids: [], effect_sets: [], tracks: [], effect_set_available: false, bgm_available: [] }
  let socket
  await page.route('**/api/local/media/*/file', (route) => route.fulfill({ status: 200, contentType: 'audio/mpeg', body: Buffer.from('mock sound data') }))
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path === '/api/profile/me') return route.fulfill({ json: { player_name: 'Tester', current_hp: null, max_hp: null } })
    if (path === '/api/local/play') return route.fulfill({ json: play })
    if (path === '/api/local/play/roster-candidates') return route.fulfill({ json: cpus })
    if (path === '/api/game/sessions' && request.method() === 'POST') return route.fulfill({ json: { session_id: 'sound-match', generation: play.generation, players: [
      { seat: 0, name: 'Tester', isHuman: true }, ...cpus.map((cpu, index) => ({ seat: index + 1, name: cpu.name, isHuman: false })),
    ] } })
    if (path === '/api/local/media') return route.fulfill({ json: [] })
    if (path === '/api/local/sound-effect-sets') return route.fulfill({ json: [] })
    if (path === '/api/local/background-tracks') return route.fulfill({ json: [] })
    if (path === '/api/local/sound-selection' && request.method() === 'PUT') {
      selection = await request.postDataJSON()
      return route.fulfill({ json: { ...selection, effect_sets: [], tracks: [], effect_set_available: false, bgm_available: [] } })
    }
    if (path === '/api/local/sound-selection') return route.fulfill({ json: selection })
    if (path === '/api/local/ending-resources') return route.fulfill({ json: { cg_asset_id: null, music_track_id: null, dialogue_text: null } })
    return route.fulfill({ json: {} })
  })
  await page.routeWebSocket('**/api/game/sessions/*/ws', (route) => {
    socket = route
    route.onMessage((raw) => {
      const message = JSON.parse(String(raw))
      if (message.type === 'authenticate') route.send(JSON.stringify({
        type: 'human_turn', generation: play.generation, session_id: 'sound-match', action_version: 0,
        turn: { observation: { player_id: 0, hands: [[], [], [], []], melds: [[], [], [], []], discards: [[], [], [], []], dora_indicators: [], scores: [25000, 25000, 25000, 25000], riichi_declared: [false, false, false, false], legal_actions: [], honba: 0, riichi_sticks: 0, round_wind: 0, kyoku_index: 0, oya: 0 }, legal_actions: [] },
      }))
    })
  })
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  await page.locator('.selection-panel').waitFor()
  await page.getByRole('button', { name: '사운드·자료 설정' }).click()
  await page.locator('.sound-panel').waitFor()
  assert.equal(await page.getByText('파일 등록', { exact: true }).count(), 1)
  await page.getByRole('button', { name: '닫기' }).click()
  for (const card of await page.locator('button.cpu-card:not([disabled])').all()) await card.click()
  await page.getByRole('button', { name: '동풍전 시작' }).click()
  await page.locator('.human-controls').waitFor()
  assert.ok(socket)
  const effect = { type: 'sound_effect', generation: play.generation, session_id: 'sound-match', action_version: 1, event_index: 0, event_key: 'ron', asset_id: 'audio-1', url: '/api/local/media/audio-1/file' }
  socket.send(JSON.stringify(effect))
  await page.waitForFunction(() => window.__soundPlayCount === 1)
  socket.send(JSON.stringify(effect))
  await page.waitForTimeout(100)
  assert.equal(await page.evaluate(() => window.__soundPlayCount), 1)
  assert.deepEqual(errors, [])
  console.log('PASS: local sound settings render and duplicate committed SFX identity plays once')
  await page.close()
} finally {
  await browser.close()
}
