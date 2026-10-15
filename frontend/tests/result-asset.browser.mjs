// Metadata/error responses only; no image files are generated.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined,
})
try {
  for (const lateFailure of [false, true]) {
    const page = await browser.newPage()
    page.setDefaultTimeout(5000)
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    const players = [0, 1, 2, 3].map((seat) => ({ seat, name: `Player ${seat}`, isHuman: seat === 0 }))
    let releaseAsset
    const assetGate = new Promise((resolve) => { releaseAsset = resolve })
    const assetPath = '/api/game/result-assets/1/file'
    await page.route('**/api/**', async (route) => {
      const path = new URL(route.request().url()).pathname
      if (path === assetPath) {
        assert.equal(route.request().headers().authorization, 'Bearer asset-test-token')
        if (lateFailure) await assetGate
        await route.fulfill({ status: 503, json: { detail: 'fixture failure' } })
        return
      }
      const body = path === '/api/auth/login'
        ? { access_token: 'asset-test-token' }
        : path === '/api/game/sessions/active'
          ? { session_id: 'asset-match', players }
          : [1, 2, 3].map((id) => ({
            id, name: `CPU ${id}`, defeat_stage: 0, style: 'balanced',
            short_description: 'Test CPU', profile_image_key: null,
          }))
      await route.fulfill({ json: body })
    })
    let socket
    await page.routeWebSocket('**/api/game/sessions/*/ws', (route) => { socket = route })
    await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
    await page.getByLabel('로그인 ID').fill('member')
    await page.getByLabel('비밀번호', { exact: true }).fill('password')
    await page.getByRole('button', { name: '로그인', exact: true }).click()
    await page.locator('.game-toolbar').waitFor()
    const assetFinished = page.waitForEvent('requestfinished', {
      predicate: (request) => new URL(request.url()).pathname === assetPath,
    })
    socket.send(JSON.stringify({
      type: 'match_complete',
      result: { scores: [30000, 28000, 25000, 17000], ranks: [1, 2, 3, 4] },
      settlement: {
        last_place_seat: 3, current_hp: 3, cpu_character_id: 3,
        defeat_stage: 1, game_over: false, cpu_completed: false,
      },
      result_asset: { id: 1, cpu_character_id: 3, defeat_stage: 1, mime_type: 'image/png', url: assetPath },
      result_dialogue: null,
    }))
    if (lateFailure) {
      await page.locator('.result-asset-placeholder').getByText('결과 CG를 불러오는 중입니다.', { exact: true }).waitFor()
      await page.getByRole('button', { name: '다음 대국 선택' }).click()
      await page.locator('.selection-panel').waitFor()
      releaseAsset()
      await assetFinished
      // Allow the failed fetch's microtasks and React render to finish.
      await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      assert.equal(await page.getByRole('alert').count(), 0)
      assert.equal(await page.locator('.selection-panel').count(), 1)
    } else {
      await assetFinished
      await page.locator('.result-asset-placeholder').getByText('결과 CG를 불러오지 못했습니다.', { exact: true }).waitFor()
      await page.getByRole('alert').filter({ hasText: '503' }).waitFor()
      assert.equal(await page.getByText('결과 CG를 불러오는 중입니다.', { exact: true }).count(), 0)
      assert.equal(await page.locator('.match-result li').count(), 4)
      await page.getByRole('button', { name: '다음 대국 선택' }).click()
      await page.locator('.selection-panel').waitFor()
    }
    assert.deepEqual(errors, [])
    await page.close()
  }
  console.log('PASS: CG failure finishes loading; late failure cannot change next selection screen')
} finally {
  await browser.close()
}
