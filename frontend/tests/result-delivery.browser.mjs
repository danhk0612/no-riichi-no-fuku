import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
try {
  const page = await browser.newPage()
  page.setDefaultTimeout(5000)
  let currentServerEnvelope = null
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/local/play/sessions/session-c1/results') return route.fulfill({ json: currentServerEnvelope })
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
  const reconciliation = page.waitForResponse((response) => response.url().includes('/api/local/play/sessions/session-c1/results?')
    && response.request().method() === 'GET')
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...conflicting }))
  await page.getByRole('alert').getByText('결과 확인 상태가 일치하지 않습니다.').waitFor()
  await reconciliation
  await page.getByText('등록된 결과 CG가 없습니다.').waitFor()
  await page.getByRole('alert').waitFor({ state: 'detached' })
  sockets[0].send(JSON.stringify({ type: 'result_delivery', ...hand }))
  await page.getByRole('heading', { name: '동풍전 정산' }).waitFor()
  await page.locator('.result-delivery-card figure.result-asset img').waitFor()
  assert.equal(await page.getByText('등록된 결과 CG가 없습니다.').count(), 1)
  assert.equal(await page.getByRole('button', { name: '정산 확인' }).isEnabled(), true)
  await page.close()
  console.log('PASS: C1 hand labels preserve MJAI kyoku/band, settlement restores saved CG, stale revision is ignored')
} finally {
  await browser.close()
}
