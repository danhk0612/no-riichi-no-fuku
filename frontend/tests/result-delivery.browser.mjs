import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
try {
  const page = await browser.newPage()
  page.setDefaultTimeout(5000)
  const resultDeliveryRequests = []
  page.on('request', (request) => {
    if (request.url().includes('/api/local/play/sessions/session-c1/results')) {
      resultDeliveryRequests.push({ method: request.method(), url: request.url() })
    }
  })
  let currentServerEnvelope = null
  let holdResult = null
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/local/play/sessions/session-c1/results') {
      if (holdResult) {
        const held = holdResult
        holdResult = null
        held.started()
        await held.release
        return route.fulfill({ json: held.response })
      }
      return route.fulfill({ json: currentServerEnvelope })
    }
    if (path === '/api/auth/login') return route.fulfill({ json: { access_token: 'result-delivery-test-token' } })
    if (path === '/api/game/result-assets/99/file') return route.fulfill({
      status: 200, contentType: 'image/png', body: Buffer.from('test-image-bytes'),
    })
    if (path === '/api/game/result-assets/100/file') return route.fulfill({ status: 503, json: { detail: 'unavailable' } })
    if (path === '/api/game/sessions/active') return route.fulfill({ json: {
      session_id: 'session-c1', players: [0, 1, 2, 3].map((seat) => ({ seat, name: `Player ${seat}`, isHuman: seat === 0 })),
    } })
    if (path === '/api/game/sessions/recent') return route.fulfill({ json: null })
    return route.fulfill({ status: 404, json: { detail: 'not found' } })
  })
  const sockets = []
  await page.routeWebSocket('**/api/game/sessions/*/ws', (socket) => sockets.push(socket))
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  await page.getByLabel('로그인 ID').fill('member')
  await page.getByLabel('비밀번호', { exact: true }).fill('password')
  await page.getByRole('button', { name: '로그인', exact: true }).click()
  await page.locator('.game-toolbar').waitFor()
  const makeHand = (revision, ordinal, eventId, band, ackedOrdinal) => ({
    version: 1, generation: 'generation-c1', session_id: 'session-c1', delivery_revision: revision,
    acked_ordinal: ackedOrdinal, terminal_ordinal: 4, route: 'result', action_version: null,
    head: { ordinal, event_id: eventId, kind: 'hand', payload: {
      fact_snapshot: {
        start: { bakaze: 'E', kyoku: 1, honba: 2, kyotaku: 1 }, participants: [{ seat: 1, name: '화료자' }],
        winners: [{ hora_log_offset: 8, actor: 1, target: 0, win_kind: 'ron', score: { band, han: 6, fu: 30 }, deltas: [0, 8000, -8000, 0] }],
      }, displayed_hora_log_offset: 8,
    } },
  })
  const hand = makeHand(10, 1, 'hand-band-1', 1, 0)
  currentServerEnvelope = hand
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...hand }))
  await page.getByRole('heading', { name: '국 결과 · E1국' }).waitFor()
  await page.getByText('만관 미만').waitFor()
  assert.equal(await page.locator('.result-delivery-card').evaluate((node) => getComputedStyle(node).animationDuration), '0.15s')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  assert.equal(await page.locator('.result-delivery-card').evaluate((node) => getComputedStyle(node).animationName), 'none')
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  const secondHand = makeHand(11, 2, 'hand-band-2', 2, 1)
  currentServerEnvelope = secondHand
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...secondHand }))
  await page.getByText('만관·하네만').waitFor()
  const thirdHand = makeHand(12, 3, 'hand-band-3', 3, 2)
  currentServerEnvelope = thirdHand
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...thirdHand }))
  await page.getByText('배만 이상').waitFor()
  const settlement = {
    version: 1, generation: 'generation-c1', session_id: 'session-c1', delivery_revision: 13,
    acked_ordinal: 3, terminal_ordinal: 4, route: 'result', action_version: null,
    head: { ordinal: 4, event_id: 'settlement-event', kind: 'settlement', payload: {
      kind: 'settlement', scores: [40000, 30000, 20000, 10000], ranks: [1, 2, 3, 4],
      participants: [{ seat: 0, name: '저장된 이름', isHuman: true }],
      presentation: { result_asset: { id: 99, url: '/api/game/result-assets/99/file', defeat_stage: 2 }, result_dialogues: [], settlement: { stage_changed: true } },
    } },
  }
  currentServerEnvelope = settlement
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...settlement }))
  await page.getByRole('heading', { name: '동풍전 정산' }).waitFor()
  await page.locator('.result-delivery-card figure.result-asset img').waitFor()
  assert.match(await page.locator('.result-delivery-card figure.result-asset img').getAttribute('src'), /^blob:/)
  assert.equal(await page.getByText('저장된 이름').count(), 1)
  const failedImage = structuredClone(settlement)
  failedImage.delivery_revision = 14
  failedImage.head.event_id = 'settlement-failed-image'
  failedImage.head.payload.presentation.result_asset.id = 100
  failedImage.head.payload.presentation.result_asset.url = '/api/game/result-assets/100/file'
  currentServerEnvelope = failedImage
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...failedImage }))
  await page.getByText('CG를 불러오지 못했습니다.').waitFor()
  assert.equal(await page.getByRole('button', { name: '정산 확인' }).isEnabled(), true)
  const noImage = structuredClone(settlement)
  noImage.delivery_revision = 15
  noImage.head.event_id = 'settlement-no-image'
  noImage.head.payload.presentation.result_asset = null
  currentServerEnvelope = noImage
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...noImage }))
  await page.getByText('등록된 결과 CG가 없습니다.').waitFor()
  const conflicting = structuredClone(noImage)
  conflicting.head.event_id = 'same-revision-conflict'
  const displayedEvent = page.locator('.result-delivery-card')
  assert.equal(await displayedEvent.getAttribute('data-event-id'), 'settlement-no-image')
  const reconciliation = page.waitForResponse((response) => response.url().includes('/api/local/play/sessions/session-c1/results?')
    && response.request().method() === 'GET').then(() => true).catch(() => false)
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...conflicting }))
  const reconciled = await reconciliation
  assert.equal(reconciled, true, `same-revision head conflict did not re-fetch; displayed event=${await displayedEvent.getAttribute('data-event-id')}; requests=${JSON.stringify(resultDeliveryRequests)}`)
  await page.getByRole('alert').waitFor({ state: 'detached' })
  assert.equal(await page.getByText('등록된 결과 CG가 없습니다.').count(), 1)
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...hand }))
  await page.waitForTimeout(100)
  assert.equal(await displayedEvent.getAttribute('data-event-id'), 'settlement-no-image')
  assert.equal(await page.getByRole('heading', { name: '동풍전 정산' }).count(), 1)
  assert.equal(await page.locator('.result-delivery-card figure.result-asset img').count(), 0)
  assert.equal(await page.getByText('등록된 결과 CG가 없습니다.').count(), 1)
  assert.equal(await page.getByRole('button', { name: '정산 확인' }).isEnabled(), true)
  let releaseHeld
  let startedHeld
  const started = new Promise((resolve) => { startedHeld = resolve })
  holdResult = { response: noImage, started: startedHeld, release: new Promise((resolve) => { releaseHeld = resolve }) }
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...conflicting }))
  await started
  const newer = structuredClone(noImage)
  newer.delivery_revision = 16
  newer.head.event_id = 'newer-settlement'
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...newer }))
  await page.locator('[data-event-id="newer-settlement"]').waitFor()
  const heldResponse = page.waitForResponse((response) => response.url().includes('/api/local/play/sessions/session-c1/results?'))
  releaseHeld()
  await heldResponse
  await page.waitForTimeout(100)
  assert.equal(await displayedEvent.getAttribute('data-event-id'), 'settlement-no-image', 'pre-fix baseline must first reproduce the old card')
  await page.close()
  for (const scenario of ['new-session']) {
    const desktop = await browser.newPage()
    desktop.setDefaultTimeout(8000)
    await desktop.addInitScript(() => { window.nrnfDesktop = { isDesktop: true } })
    const players = [0, 1, 2, 3].map((seat) => ({ seat, name: `Player ${seat}`, isHuman: seat === 0 }))
    const cpus = [1, 2, 3].map((id) => ({ id, name: `CPU ${id}`, defeat_stage: 0, style: 'balanced', short_description: '', profile_image_key: null }))
    let play = { generation: 'generation-c1', phase: 'playing', roster: cpus.map((cpu) => ({ cpu_character_id: cpu.id, defeat_stage: 0 })), ending_event_id: null, ending_payload: null, active_session_id: 'session-c1', recent_session_id: null, legacy_active: false, result_resume: null }
    let session = 'session-c1'
    let releaseGet
    let startGet
    const getStarted = new Promise((resolve) => { startGet = resolve })
    const getRelease = new Promise((resolve) => { releaseGet = resolve })
    let fresh = noImage
    let resultRequests = 0
    await desktop.route('**/api/**', async (route) => {
      const request = route.request()
      const path = new URL(request.url()).pathname
      if (path === '/api/profile/me') return route.fulfill({ json: { player_name: 'Tester' } })
      if (path === '/api/local/sound-selection') return route.fulfill({ json: { effect_set_id: null, bgm_ids: [], effect_sets: [], tracks: [], effect_set_available: false, bgm_available: [] } })
      if (path === '/api/local/play/reset') {
        play = { ...play, generation: 'new-generation', phase: 'omake', active_session_id: null }
        return route.fulfill({ json: play })
      }
      if (path === '/api/local/play') return route.fulfill({ json: play })
      if (path === '/api/local/play/roster-candidates') return route.fulfill({ json: cpus })
      if (path === '/api/game/sessions/active') return route.fulfill({ json: play.active_session_id ? { session_id: session, generation: play.generation, players } : null })
      if (path === '/api/game/sessions/recent') return route.fulfill({ json: null })
      if (path === '/api/game/sessions' && request.method() === 'POST') {
        if (scenario === 'reset') return route.fulfill({ status: 503, json: { detail: '새 대국 테스트 오류' } })
        session = 'new-session'; play = { ...play, active_session_id: session }
        return route.fulfill({ json: { session_id: session, generation: play.generation, players } })
      }
      if (path === '/api/local/play/sessions/session-c1/results') {
        resultRequests += 1
        if (scenario === 'same-generation-new-session' && resultRequests === 2) {
          return route.fulfill({ json: { ...noImage, delivery_revision: 16, head: null, route: 'selection' } })
        }
        startGet(); await getRelease
        return route.fulfill({ json: fresh })
      }
      return route.fulfill({ json: {} })
    })
    const desktopSockets = []
    const sent = []
    await desktop.routeWebSocket('**/api/game/sessions/*/ws', (socket) => {
      desktopSockets.push(socket)
      socket.onMessage((raw) => {
        const message = JSON.parse(String(raw)); sent.push(message)
        if (message.type === 'authenticate') socket.send(JSON.stringify({
          type: 'human_turn', generation: play.generation, session_id: session, action_version: 37,
          turn: { observation: { player_id: 0, hands: [[0], [], [], []], melds: [[], [], [], []], discards: [[], [], [], []], dora_indicators: [], scores: [25000, 25000, 25000, 25000], riichi_declared: [false, false, false, false], legal_actions: [], honba: 0, riichi_sticks: 0, round_wind: 0, kyoku_index: 0, oya: 0 }, legal_actions: [{ type: 0, tile: 0, consume_tiles: [], actor: 0 }] },
        }))
      })
    })
    await desktop.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
    await desktop.locator('.hand button').waitFor()
    desktopSockets[0].send(JSON.stringify({ type: 'result_delivery', ...noImage }))
    await desktop.locator('[data-event-id="settlement-no-image"]').waitFor()
    desktopSockets[0].send(JSON.stringify({ type: 'result_delivery', ...conflicting }))
    await getStarted
    if (scenario === 'reset' || scenario === 'new-session' || scenario === 'same-generation-new-session') {
      if (scenario === 'same-generation-new-session') {
        play = { ...play, phase: 'omake', active_session_id: null }
        desktopSockets[0].send(JSON.stringify({ type: 'result_delivery', ...conflicting }))
      } else {
        desktop.once('dialog', (dialog) => dialog.accept())
        await desktop.getByRole('button', { name: '초기화' }).click()
      }
      await desktop.locator('.selection-panel').waitFor()
      for (const card of await desktop.locator('button.cpu-card:not([disabled])').all()) await card.click()
      await desktop.getByRole('button', { name: '동풍전 시작' }).click()
      if (scenario === 'reset') {
        await desktop.getByRole('alert').filter({ hasText: '새 대국 테스트 오류' }).waitFor()
      } else {
        await desktop.locator('.hand button').waitFor()
      }
      const response = desktop.waitForResponse((item) => item.url().includes('/sessions/session-c1/results?'))
      releaseGet(); await response; await desktop.waitForTimeout(200)
      assert.equal(await desktop.locator('.result-delivery-card').count(), 0, `old GET after ${scenario} must not restore result`)
      if (scenario === 'reset') assert.equal(await desktop.getByRole('alert').filter({ hasText: '새 대국 테스트 오류' }).count(), 1, 'old GET after reset must not clear the current error')
    } else {
      fresh = { ...noImage, delivery_revision: 16, head: null, route: scenario, action_version: scenario === 'human_turn' ? 37 : null }
      if (scenario === 'ending') play = { ...play, phase: 'ending_pending', active_session_id: null, ending_event_id: 'ending-1' }
      if (scenario === 'selection') play = { ...play, phase: 'omake', active_session_id: null }
      releaseGet()
      if (scenario === 'human_turn') {
        await desktop.locator('.hand button').waitFor()
        desktopSockets.at(-1).send(JSON.stringify({ type: 'result_delivery', ...noImage }))
        await desktop.waitForTimeout(100)
        assert.equal(await desktop.locator('.result-delivery-card').count(), 0, 'stale revision must not replace the recovered turn')
        const action = new Promise((resolve) => desktopSockets.at(-1).onMessage((raw) => {
          const message = JSON.parse(String(raw))
          if (message.type === 'action') resolve(message)
        }))
        await desktop.locator('.hand button').click()
        assert.equal((await Promise.race([action, new Promise((_, reject) => setTimeout(() => reject(new Error('restored action was not sent')), 5000))])).action_version, 37)
      } else if (scenario === 'ending') await desktop.getByRole('region', { name: '엔딩' }).waitFor()
      else await desktop.locator('.selection-panel').waitFor()
      assert.equal(await desktop.locator('.result-delivery-card').count(), 0, `${scenario} must leave the result card`)
    }
    await desktop.close()
  }
  console.log('PASS: C1 hand labels preserve MJAI kyoku/band, settlement restores saved CG, stale revision is ignored')
} finally {
  await browser.close()
}
