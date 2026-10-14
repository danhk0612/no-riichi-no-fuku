// Uses the same Vite/Playwright environment as dialogue.browser.mjs.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined,
})
try {
  for (const closeCode of [1000, 1011]) {
    const page = await browser.newPage()
    page.setDefaultTimeout(5000)
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    const players = [0, 1, 2, 3].map((seat) => ({
      seat, name: `Player ${seat}`, isHuman: seat === 0,
    }))
    let activeLookups = 0
    await page.route('**/api/**', async (route) => {
      const path = new URL(route.request().url()).pathname
      if (path === '/api/auth/login') {
        await route.fulfill({ json: { access_token: 'connection-test-token' } })
      } else {
        assert.equal(path, '/api/game/sessions/active')
        activeLookups += 1
        await route.fulfill({ json: { session_id: 'persisted-match', players } })
      }
    })
    const sockets = []
    const sent = []
    await page.routeWebSocket('**/api/game/sessions/*/ws', (socket) => {
      sockets.push(socket)
      socket.onMessage((message) => sent.push(JSON.parse(message)))
    })
    const login = async () => {
      await page.getByLabel('로그인 ID').fill('member')
      await page.getByLabel('비밀번호', { exact: true }).fill('password')
      await page.getByRole('button', { name: '로그인', exact: true }).click()
      await page.locator('.game-toolbar').waitFor()
    }
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
        legal_actions: [{ type: 0, tile: 0, consume_tiles: [], actor: 0 }],
      },
    })
    await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
    await login()
    sockets[0].send(JSON.stringify(turn(11)))
    const discard = page.locator('.hand button')
    await discard.waitFor()
    assert.equal(await discard.isEnabled(), true)
    sockets[0].close({ code: closeCode })
    await page.getByRole('alert').filter({ hasText: '새로고침 후 다시 로그인' }).waitFor()
    assert.equal(await discard.isDisabled(), true)
    assert.equal(sent.filter((message) => message.type === 'action').length, 0)

    // Refresh/re-login discovers the same session and waits for server state.
    await page.reload()
    await login()
    assert.equal(sockets.length, 2)
    assert.equal(await page.locator('.hand button').count(), 0)
    sockets[1].send(JSON.stringify(turn(12)))
    await discard.waitFor()
    assert.equal(await discard.isEnabled(), true)
    assert.equal(await page.getByRole('alert').count(), 0)
    const action = new Promise((resolve) => sockets[1].onMessage((message) => {
      resolve(JSON.parse(message))
    }))
    await discard.click()
    await page.waitForFunction(() => document.querySelector('.hand button')?.disabled)
    assert.deepEqual(await action, { type: 'action', action_version: 12, legal_action_index: 0 })
    assert.equal(activeLookups, 2)
    assert.deepEqual(errors, [])
    await page.close()
  }
  console.log('PASS: normal/abnormal disconnect locks actions; refresh/login recovers current server turn')
} finally {
  await browser.close()
}
