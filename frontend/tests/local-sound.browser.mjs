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
    window.__audioInstances = []
    const NativeAudio = window.Audio
    window.Audio = function (source) {
      const audio = new NativeAudio()
      audio.__source = source
      audio.__playCount = 0
      audio.play = () => {
        audio.__playCount += 1; window.__soundPlayCount += 1
        if (window.__deferNextPlay) { window.__deferNextPlay = false; return new Promise((resolve, reject) => { window.__rejectDeferredPlay = () => reject(new Error('late mock play rejection')) }) }
        if (window.__rejectNextPlay) { window.__rejectNextPlay = false; return Promise.reject(new Error('mock autoplay rejected')) }
        return Promise.resolve()
      }
      window.__audioInstances.push(audio)
      return audio
    }
    HTMLMediaElement.prototype.play = function () { window.__soundPlayCount += 1; return Promise.resolve() }
  })
  const play = {
    generation: 'sound-test-generation', phase: 'omake',
    roster: [1, 2, 3].map((cpu_character_id) => ({ cpu_character_id, defeat_stage: 3 })),
    ending_event_id: 'ending-1', ending_payload: null, active_session_id: null,
    recent_session_id: null, legacy_active: false,
  }
  const cpus = [1, 2, 3].map((id) => ({ id, name: `CPU ${id}`, defeat_stage: 3, style: 'balanced', short_description: 'fixture', profile_image_key: null }))
  const tracks = [
    { id: 'track-a', label: 'Track A', active: true, media_asset_id: 'asset-a', available: true, url: '/api/local/media/asset-a/file' },
    { id: 'track-b', label: 'Track B', active: true, media_asset_id: 'asset-b', available: true, url: '/api/local/media/asset-b/file' },
  ]
  let selection = { effect_set_id: 'set-old', bgm_ids: ['track-a', 'track-b'], effect_sets: [{ id: 'set-old', label: 'Old set', active: false, clips: {} }], tracks, effect_set_available: false, bgm_available: [true, true] }
  let ending = { cg_asset_id: null, music_track_id: 'track-b', dialogue_text: null }
  let disabledSetClearSaved = false
  let endingClearSaved = false
  let completed = false
  let failAssetA2Once = true
  let socket
  await page.route('**/api/local/media/*/file', async (route) => {
    if (route.request().url().includes('/asset-sfx-late/')) await new Promise((resolve) => setTimeout(resolve, 3000))
    else if (route.request().url().includes('/asset-sfx/')) await new Promise((resolve) => setTimeout(resolve, 250))
    if (route.request().url().includes('/asset-b/')) await new Promise((resolve) => setTimeout(resolve, 250))
    if (route.request().url().includes('/asset-a2/') && failAssetA2Once) {
      failAssetA2Once = false
      return route.fulfill({ status: 503, body: 'fixture media failure' })
    }
    return route.fulfill({ status: 200, contentType: 'audio/mpeg', body: Buffer.from('mock sound data') })
  })
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (/^\/api\/local\/media\/[^/]+\/file$/.test(path)) return route.fallback()
    if (path === '/api/profile/me') return route.fulfill({ json: { player_name: 'Tester', current_hp: null, max_hp: null } })
    if (path === '/api/local/play') return route.fulfill({ json: play })
    if (path === '/api/local/play/reset' && request.method() === 'POST') {
      Object.assign(play, { generation: 'sound-test-generation-reset', phase: 'roster_required', roster: [], ending_event_id: null, ending_payload: null, active_session_id: null, recent_session_id: null })
      return route.fulfill({ json: play })
    }
    if (path === '/api/local/play/roster-candidates') return route.fulfill({ json: cpus })
    if (path === '/api/game/sessions' && request.method() === 'POST') return route.fulfill({ json: { session_id: 'sound-match', generation: play.generation, players: [
      { seat: 0, name: 'Tester', isHuman: true }, ...cpus.map((cpu, index) => ({ seat: index + 1, name: cpu.name, isHuman: false })),
    ] } })
    if (path === '/api/local/media') return route.fulfill({ json: [
      { id: 'asset-a', kind: 'audio', mime_type: 'audio/mpeg', byte_size: 8, url: '/api/local/media/asset-a/file', available: true },
      { id: 'asset-a2', kind: 'audio', mime_type: 'audio/mpeg', byte_size: 8, url: '/api/local/media/asset-a2/file', available: true },
      { id: 'asset-b', kind: 'audio', mime_type: 'audio/mpeg', byte_size: 8, url: '/api/local/media/asset-b/file', available: true },
    ] })
    if (path === '/api/local/sound-effect-sets') return route.fulfill({ json: selection.effect_sets })
    if (path === '/api/local/background-tracks') return route.fulfill({ json: tracks })
    if (path.startsWith('/api/local/background-tracks/') && request.method() === 'PATCH') {
      const id = path.split('/').at(-1)
      const update = await request.postDataJSON()
      const track = tracks.find((item) => item.id === id)
      Object.assign(track, update, { url: `/api/local/media/${update.media_asset_id ?? track.media_asset_id}/file` })
      return route.fulfill({ json: track })
    }
    if (path === '/api/local/sound-selection' && request.method() === 'PUT') {
      const next = await request.postDataJSON()
      if (selection.effect_set_id === 'set-old' && next.effect_set_id === null) disabledSetClearSaved = true
      selection = { ...selection, ...next, tracks, effect_sets: [], effect_set_available: false, bgm_available: next.bgm_ids.map(() => true) }
      return route.fulfill({ json: selection })
    }
    if (path === '/api/local/sound-selection') return route.fulfill({ json: selection })
    if (path === '/api/local/ending-resources' && request.method() === 'PUT') {
      ending = await request.postDataJSON()
      endingClearSaved ||= ending.music_track_id === null
      return route.fulfill({ json: ending })
    }
    if (path === '/api/local/ending-resources') return route.fulfill({ json: ending })
    if (path === '/api/local/play' && completed) return route.fulfill({ json: { ...play, phase: 'omake' } })
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
  await page.waitForFunction(() => window.__audioInstances.length === 1)
  await page.getByRole('button', { name: '사운드·자료 설정' }).click()
  await page.locator('.sound-panel').waitFor()
  assert.equal(await page.getByText('파일 등록', { exact: true }).count(), 1)
  assert.equal(await page.getByRole('option', { name: 'Old set · 비활성' }).count(), 2)
  await page.getByLabel('효과음 세트').selectOption('')
  await page.getByRole('button', { name: '1번 배경음 아래로' }).click()
  await page.getByRole('button', { name: '사운드 선택 저장' }).click()
  await page.waitForFunction(() => window.__audioInstances.length === 1)
  const delayedTrackLoad = page.waitForRequest((request) => request.url().includes('/asset-b/'))
  await page.evaluate(() => window.__audioInstances[0].dispatchEvent(new Event('ended')))
  await delayedTrackLoad
  await page.getByRole('checkbox', { name: 'Track B' }).uncheck()
  await page.getByRole('button', { name: '사운드 선택 저장' }).click()
  await page.waitForFunction(() => window.__audioInstances.length === 2)
  await page.waitForTimeout(350)
  assert.equal(await page.evaluate(() => window.__audioInstances.length), 2, 'late BGM fetch after removal must not create an Audio')
  await page.evaluate(() => window.__audioInstances[1].dispatchEvent(new Event('ended')))
  await page.waitForFunction(() => window.__audioInstances[1].__playCount === 2)
  await page.evaluate(() => window.__audioInstances[1].dispatchEvent(new Event('ended')))
  await page.waitForFunction(() => window.__audioInstances[1].__playCount === 3)
  assert.equal(await page.evaluate(() => window.__audioInstances.length), 2, 'single BGM should repeatedly use the same Audio')
  await page.getByRole('checkbox', { name: 'Track B' }).check()
  const reenabledSelection = page.waitForResponse((response) => response.url().includes('/api/local/sound-selection') && response.request().method() === 'PUT')
  await page.getByRole('button', { name: '사운드 선택 저장' }).click()
  await reenabledSelection
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => resolve(undefined))))
  await page.evaluate(() => window.__audioInstances[1].dispatchEvent(new Event('ended')))
  await page.waitForFunction(() => window.__audioInstances.length === 3)
  await page.evaluate(() => window.__audioInstances[0].dispatchEvent(new Event('ended')))
  await page.waitForTimeout(50)
  assert.equal(await page.evaluate(() => window.__audioInstances.length), 3, 'stale ended callback must not advance the active BGM')
  const trackBRow = page.locator('.sound-list li').filter({ hasText: 'Track B' })
  await trackBRow.getByRole('button', { name: '비활성화' }).click()
  await page.getByRole('button', { name: '2번 배경음 선택 해제' }).click()
  await page.getByRole('button', { name: '사운드 선택 저장' }).click()
  await page.getByLabel('엔딩 음악').selectOption('')
  await page.getByRole('button', { name: '엔딩 자료 저장' }).click()
  await page.waitForFunction(() => window.__audioInstances.length === 4)
  assert.equal(await page.evaluate(() => window.__audioInstances.length), 4, 'current track should move to the first remaining active selection')
  const trackARow = page.locator('.sound-list li').filter({ hasText: 'Track A' })
  await trackARow.getByRole('button', { name: '편집' }).click()
  await page.getByLabel('오디오 파일').selectOption('asset-a2')
  await page.getByRole('button', { name: '배경음 수정 저장' }).click()
  await page.evaluate(() => { window.__rejectNextPlay = true })
  await page.getByRole('button', { name: '사운드 선택 저장' }).click()
  await page.getByRole('button', { name: '배경음 재생' }).waitFor()
  assert.equal(await page.evaluate(() => window.__audioInstances.length), 4, 'failed file load should offer a user retry without constructing audio')
  await page.getByRole('button', { name: '배경음 재생' }).click()
  await page.waitForFunction(() => window.__audioInstances.length === 5)
  await page.waitForFunction(() => window.__audioInstances[4].__playCount === 1)
  await page.getByRole('button', { name: '배경음 재생' }).click()
  await page.waitForFunction(() => window.__audioInstances[4].__playCount === 2)
  assert.equal(await page.evaluate(() => window.__audioInstances.length), 5, 'same track ID with replaced media must use the new media')
  // A user retry belongs to this Audio, even if its promise settles after a media replacement.
  await page.evaluate(() => { window.__rejectNextPlay = true; window.__audioInstances[4].dispatchEvent(new Event('ended')) })
  await page.getByRole('button', { name: '배경음 재생' }).waitFor()
  await page.evaluate(() => { window.__deferNextPlay = true })
  await page.getByRole('button', { name: '배경음 재생' }).click()
  await page.waitForFunction(() => typeof window.__rejectDeferredPlay === 'function')
  await trackARow.getByRole('button', { name: '편집' }).click()
  await page.getByLabel('오디오 파일').selectOption('asset-a')
  await page.getByRole('button', { name: '배경음 수정 저장' }).click()
  await page.waitForFunction(() => window.__audioInstances.length === 6)
  await page.evaluate(() => window.__rejectDeferredPlay())
  await page.waitForTimeout(50)
  assert.equal(await page.getByRole('button', { name: '배경음 재생' }).count(), 0, 'discarded retry rejection must not block the replacement Audio')
  assert.equal(await page.getByRole('button', { name: '1번 배경음 선택 해제' }).count(), 1)
  await page.getByRole('button', { name: '닫기' }).click()
  for (const card of await page.locator('button.cpu-card:not([disabled])').all()) await card.click()
  await page.getByRole('button', { name: '동풍전 시작' }).click()
  await page.locator('.human-controls').waitFor()
  assert.ok(socket)
  const beforeSfx = await page.evaluate(() => window.__audioInstances.length)
  await page.evaluate(() => { window.__deferNextPlay = true })
  const effect = { type: 'sound_effect', generation: play.generation, session_id: 'sound-match', action_version: 1, event_index: 0, event_key: 'ron', asset_id: 'audio-sfx', url: '/api/local/media/asset-sfx/file' }
  socket.send(JSON.stringify(effect))
  socket.send(JSON.stringify(effect))
  const lateEffect = { ...effect, action_version: 2, event_index: 1, event_key: 'tsumo', url: '/api/local/media/asset-sfx-late/file' }
  const delayedSfxLoad = page.waitForRequest((request) => request.url().includes('/asset-sfx-late/'))
  const delayedSfxResponse = page.waitForResponse((response) => response.url().includes('/asset-sfx-late/'))
  socket.send(JSON.stringify(lateEffect))
  await delayedSfxLoad
  completed = true
  socket.send(JSON.stringify({
    type: 'match_complete', generation: play.generation, session_id: 'sound-match',
    result: { scores: [30000, 25000, 25000, 20000], ranks: [1, 2, 3, 4] },
    settlement: { last_place_seat: 3, current_hp: null, cpu_character_id: null, defeat_stage: null, game_over: false, cpu_completed: false },
    result_asset: null, result_dialogue: null, result_dialogues: [], ending_event_id: null,
  }))
  await page.waitForFunction((count) => window.__audioInstances.length === count + 1, beforeSfx)
  await page.waitForTimeout(100)
  assert.equal(await page.evaluate(() => window.__audioInstances.length), beforeSfx + 1, 'committed SFX fetch should complete after match_complete')
  socket.send(JSON.stringify(effect))
  await page.waitForTimeout(100)
  assert.equal(await page.evaluate(() => window.__audioInstances.length), beforeSfx + 1, 'replayed SFX identity should stay silent')
  assert.ok(await page.locator('.match-result').count())
  await page.evaluate(() => { window.confirm = () => true })
  await page.getByRole('button', { name: '초기화' }).click()
  await page.locator('.selection-panel').waitFor()
  await page.evaluate(() => window.__rejectDeferredPlay())
  await (await delayedSfxResponse).finished()
  await page.waitForTimeout(50)
  assert.equal(await page.getByText('효과음을 재생할 수 없습니다.', { exact: true }).count(), 0, 'discarded SFX play rejection must not show an error after reset')
  assert.equal(await page.evaluate(() => window.__audioInstances.length), beforeSfx + 1, 'late SFX fetch after reset/new generation must not create audio')
  assert.deepEqual(errors, [])
  assert.equal(disabledSetClearSaved, true)
  assert.equal(endingClearSaved, true)
  console.log('PASS: BGM cycle/order continuity, one-track repeat, stale callback rejection, media replacement, retry after file/autoplay failure, inactive selection clearing, and final committed SFX survive match completion')
  await page.close()
} finally {
  await browser.close()
}
