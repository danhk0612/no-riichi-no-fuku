// Run against Vite with Playwright supplied by the test environment.
// PLAYWRIGHT_MODULE_PATH may point to an external Playwright package.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined,
})
try {
  const page = await browser.newPage()
  page.setDefaultTimeout(5000)
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  const players = [0, 1, 2, 3].map((seat) => ({
    seat, name: `Player ${seat}`, isHuman: seat === 0,
  }))
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    const body = path === '/api/auth/login'
      ? { access_token: 'browser-test-token' }
      : path === '/api/game/sessions/active'
        ? { session_id: 'first', players }
        : path === '/api/game/sessions'
          ? { session_id: 'second', players }
          : [1, 2, 3].map((id) => ({
            id, name: `CPU ${id}`, defeat_stage: 0, style: 'balanced',
            short_description: 'Test CPU', profile_image_key: null,
          }))
    await route.fulfill({ json: body })
  })
  const sockets = []
  await page.routeWebSocket('**/api/game/sessions/*/ws', (socket) => {
    sockets.push(socket)
  })
  const send = (socket, message) => socket.send(JSON.stringify(message))
  const dialogue = (seat, text) => ({
    type: 'dialogue_event', cpu_character_id: seat, seat,
    event_key: 'riichi', text,
  })
  const turn = (version) => ({
    type: 'human_turn', action_version: version,
    turn: {
      observation: {
        player_id: 0, hands: [[0], [], [], []], melds: [[], [], [], []],
        discards: [[], [], [], []], dora_indicators: [],
        scores: [25000, 25000, 25000, 25000],
        riichi_declared: [false, false, false, false],
        legal_actions: [], honba: 0, riichi_sticks: 0, round_wind: 0, oya: 0,
      },
      legal_actions: [],
    },
  })
  const bubble = (seat) => page.locator(`.seat-${seat} .speech-bubble`)
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  await page.getByLabel('로그인 ID').fill('test-member')
  await page.getByLabel('비밀번호', { exact: true }).fill('test-password')
  await page.getByRole('button', { name: '로그인', exact: true }).click()
  await page.waitForFunction(() => document.querySelector('.game-toolbar'))
  assert.equal(sockets.length, 1)

  // The server sends dialogue before the next turn, including the initial turn.
  send(sockets[0], dialogue(1, '첫 대사'))
  send(sockets[0], turn(0))
  await bubble(1).getByText('첫 대사', { exact: true }).waitFor()
  send(sockets[0], turn(1))
  await bubble(1).getByText('첫 대사', { exact: true }).waitFor()

  // An incoming line also updates an already displayed turn immediately.
  send(sockets[0], dialogue(2, '다른 좌석 대사'))
  await bubble(2).getByText('다른 좌석 대사', { exact: true }).waitFor()
  send(sockets[0], dialogue(1, '최신 대사'))
  send(sockets[0], turn(2))
  await bubble(1).getByText('최신 대사', { exact: true }).waitFor()
  assert.equal(await bubble(1).getByText('첫 대사', { exact: true }).count(), 0)
  assert.equal(await bubble(2).innerText(), '다른 좌석 대사')

  // Public melds belong to their seats, including the player's exposed groups.
  const meldTurn = turn(3)
  meldTurn.turn.observation.melds = [
    [{ meld_type: 0, tiles: [8, 12, 16], called_tile: 16, from_who: 3, opened: true }],
    [{ meld_type: 1, tiles: [108, 109, 110], called_tile: 108, from_who: 0, opened: true }],
    [{ meld_type: 2, tiles: [36, 37, 38, 39], called_tile: 36, from_who: 1, opened: true }],
    [{ meld_type: 3, tiles: [72, 73, 74, 75], called_tile: -1, from_who: -1, opened: false }],
  ]
  send(sockets[0], meldTurn)
  for (const seat of [0, 1, 2, 3]) {
    await page.locator(`.seat-${seat} .melds`).waitFor()
    assert.equal(await page.locator(`.seat-${seat} .meld .tile`).count(), seat < 2 ? 3 : 4)
    assert.equal(await page.locator(`.seat-${seat} .meld small`).innerText(), seat === 3 ? '암깡' : '부로')
  }
  assert.deepEqual(await page.locator('.seat-0 .meld .tile').allTextContents(), ['3만', '4만', '5만'])
  assert.equal(await page.locator('.seat-0 .meld .tile-red').count(), 1)
  assert.equal(await page.locator('.seat-1 .meld .tile-honor').count(), 3)

  // Server snapshots replace groups on each turn; a new round clears old melds.
  const updatedTurn = structuredClone(meldTurn)
  updatedTurn.action_version = 4
  updatedTurn.turn.observation.melds[1].push({
    meld_type: 1, tiles: [112, 113, 114], called_tile: 112, from_who: 2, opened: true,
  })
  send(sockets[0], updatedTurn)
  await page.waitForFunction(() => document.querySelectorAll('.seat-1 .meld').length === 2)
  for (const viewport of [{ width: 1180, height: 1000 }, { width: 360, height: 800 }]) {
    await page.setViewportSize(viewport)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
  }
  send(sockets[0], turn(5))
  await page.waitForFunction(() => document.querySelectorAll('.meld').length === 0)

  // Completing and starting a new match must not reuse previous dialogue.
  send(sockets[0], {
    type: 'match_complete', result: { scores: [25000, 25000, 25000, 25000], ranks: [1, 2, 3, 4] },
    settlement: {
      last_place_seat: 3, current_hp: 3, cpu_character_id: 3,
      defeat_stage: 1, game_over: false, cpu_completed: false,
    },
    result_asset: null, result_dialogue: null,
  })
  await page.getByRole('button', { name: '다음 대국 선택' }).click()
  for (const id of [1, 2, 3]) {
    await page.locator('.cpu-card').filter({ hasText: `CPU ${id}` }).click()
  }
  await page.getByRole('button', { name: '동풍전 시작' }).click()
  await page.waitForFunction(() => !document.querySelector('.selection-panel'))
  assert.equal(sockets.length, 2)
  send(sockets[1], turn(0))
  await page.locator('.mahjong-table').waitFor()
  assert.equal(await page.locator('.speech-bubble').count(), 0)
  send(sockets[1], dialogue(3, '새 대국 대사'))
  send(sockets[1], turn(1))
  await bubble(3).getByText('새 대국 대사', { exact: true }).waitFor()
  assert.deepEqual(errors, [])
  console.log('PASS: dialogue lifecycle; four-seat melds, red fives, kan, snapshot replacement and round reset')
} finally {
  await browser.close()
}
