import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
try {
  const page = await browser.newPage(); page.setDefaultTimeout(8000)
  const errors = []; page.on('pageerror', (error) => errors.push(error.message))
  await page.addInitScript(() => {
    window.nrnfDesktop = { isDesktop: true }; window.__audios = []
    window.Audio = class extends EventTarget {
      constructor(src) { super(); this.src = src; this.paused = true; window.__audios.push(this) }
      play() { this.paused = false; return Promise.resolve() }
      pause() { this.paused = true; this.dispatchEvent(new Event('pause')) }
    }
  })
  const cpus = [1, 2, 3].map((id) => ({ id, name: `CPU ${id}`, defeat_stage: 3, style: 'balanced', short_description: 'test-only', profile_image_key: null }))
  const voices = new Map(cpus.map((cpu) => [cpu.id, { schema_version: 1, cpu_id: cpu.id, revision: 0, default_pack_id: null, selected_pack_id: null, selection_mode: 'default', packs: [] }]))
  const audioPacks = { schema_version: 1, revision: 0, sfx_mode: 'legacy', sfx_pack_id: null, bgm_mode: 'legacy', bgm_pack_id: null, defaults: { sfx: null, bgm: null }, packs: [], bgm_slots: {} }
  const selection = { effect_set_id: null, bgm_ids: [], effect_sets: [], tracks: [], effect_set_available: false, bgm_available: [], audio_packs: audioPacks }
  const play = { generation: 'test-generation', phase: 'omake', roster: cpus.map((cpu) => ({ cpu_character_id: cpu.id, defeat_stage: 3 })), ending_event_id: null, ending_payload: null, active_session_id: null, recent_session_id: null, legacy_active: false }
  const heldFiles = new Map(); let socket
  await page.route('**/api/**', async (route) => {
    const request = route.request(), path = new URL(request.url()).pathname
    if (/^\/api\/local\/media\/[^/]+\/file$/.test(path)) {
      if (heldFiles.has(path)) await heldFiles.get(path)
      return route.fulfill({ contentType: 'audio/mpeg', body: Buffer.from('test-only') })
    }
    if (path === '/api/profile/me') return route.fulfill({ json: { player_name: 'test', current_hp: null, max_hp: null } })
    if (path === '/api/local/play') return route.fulfill({ json: play })
    if (path === '/api/game/sessions/active') return route.fulfill({ json: null })
    if (path === '/api/admin/cpus' || path === '/api/local/play/roster-candidates') return route.fulfill({ json: cpus })
    if (path === '/api/local/sound-selection') return route.fulfill({ json: selection })
    if (path === '/api/local/audio-pack-selection' && request.method() === 'PUT') {
      Object.assign(audioPacks, request.postDataJSON(), { revision: audioPacks.revision + 1 })
      return route.fulfill({ json: audioPacks })
    }
    const voice = path.match(/^\/api\/local\/characters\/(\d+)\/voice-selection$/)
    if (voice) {
      const value = voices.get(Number(voice[1]))
      if (request.method() === 'PUT') Object.assign(value, request.postDataJSON(), { revision: value.revision + 1 })
      return route.fulfill({ json: value })
    }
    if (['/api/local/media', '/api/local/sound-effect-sets', '/api/local/background-tracks'].includes(path)) return route.fulfill({ json: [] })
    if (path === '/api/local/ending-resources') return route.fulfill({ json: { cg_asset_id: null, music_track_id: null, dialogue_text: null } })
    if (path === '/api/game/sessions' && request.method() === 'POST') return route.fulfill({ json: { session_id: 'test-match', generation: play.generation, players: [{ seat: 0, name: 'test', isHuman: true }, ...cpus.map((cpu, index) => ({ seat: index + 1, name: cpu.name, isHuman: false }))] } })
    throw new Error(`Unexpected API ${request.method()} ${path}`)
  })
  await page.routeWebSocket('**/api/game/sessions/*/ws', (route) => {
    socket = route
    route.onMessage(() => route.send(JSON.stringify({ type: 'human_turn', generation: play.generation, session_id: 'test-match', action_version: 0,
      turn: { observation: { player_id: 0, hands: [[], [], [], []], melds: [[], [], [], []], discards: [[], [], [], []], dora_indicators: [], scores: [25000, 25000, 25000, 25000], riichi_declared: [false, false, false, false], honba: 0, riichi_sticks: 0, round_wind: 0, kyoku_index: 0, oya: 0 }, legal_actions: [] } })))
  })
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  await page.locator('.selection-panel').waitFor()
  for (const card of await page.locator('button.cpu-card:not([disabled])').all()) await card.click()
  await page.getByRole('button', { name: '동풍전 시작' }).click()
  await page.locator('.human-controls').waitFor()
  await page.getByRole('button', { name: '사운드·자료 설정' }).click()
  const voiceRow = page.locator('.sound-voice-row').nth(1)
  await voiceRow.waitFor()
  const event = { generation: play.generation, session_id: 'test-match', action_version: 1, event_index: 0, actor_seat: 2, event_key: 'pon', asset_id: 'test-only' }
  for (const [index, domain] of ['voice', 'sfx'].entries()) {
    const path = `/api/local/media/held-${domain}/file`; let release
    heldFiles.set(path, new Promise((resolve) => { release = resolve }))
    const requested = page.waitForRequest((r) => new URL(r.url()).pathname === path)
    const responded = page.waitForResponse((r) => new URL(r.url()).pathname === path)
    socket.send(JSON.stringify({ ...event, type: domain === 'voice' ? 'voice_effect' : 'sound_effect', action_version: index + 1, url: path }))
    if (domain === 'voice') socket.send(JSON.stringify({ ...event, type: 'voice_effect', event_key: 'win', url: '/api/local/media/queued-win/file' }))
    await requested
    if (domain === 'voice') {
      await voiceRow.getByLabel('음성팩').selectOption('off')
      await voiceRow.getByRole('button', { name: '저장', exact: true }).click()
    } else {
      await page.getByLabel('SFX 재생 방식').selectOption('pack')
      await page.getByRole('button', { name: '팩 재생 방식 저장', exact: true }).click()
    }
    await page.waitForFunction(() => !document.querySelector('.sound-panel input[type="file"]')?.disabled)
    release(); await (await responded).finished()
    await page.waitForTimeout(100)
    assert.equal(await page.evaluate(() => window.__audios.length), 0, `${domain} change must discard old in-flight files and queued voices`)
  }
  await voiceRow.getByLabel('음성팩').selectOption('')
  await voiceRow.getByRole('button', { name: '저장', exact: true }).click()
  await page.waitForFunction(() => !document.querySelector('.sound-panel input[type="file"]')?.disabled)
  socket.send(JSON.stringify({ ...event, type: 'voice_effect', action_version: 3, url: '/api/local/media/current-voice/file' }))
  await page.waitForFunction(() => window.__audios.length === 1 && !window.__audios[0].paused)
  await voiceRow.getByLabel('음성팩').selectOption('off')
  await voiceRow.getByRole('button', { name: '저장', exact: true }).click()
  await page.waitForFunction(() => window.__audios[0].paused)
  assert.deepEqual(errors, [])
  console.log('PASS: voice-off/SFX pack save discard held media and queued voices, future voice queue recovers, active voice stops')
} finally { await browser.close() }
