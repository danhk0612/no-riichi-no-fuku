import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdirSync, mkdtempSync } from 'node:fs'
import { join } from 'node:path'

const { _electron } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const [exe, evidence] = process.argv.slice(2)
mkdirSync(evidence, {recursive:true})
const data = mkdtempSync(join(evidence, 'campaign-'))
let app, page, turn
const button = name => page.getByRole('button', {name, exact:true})
async function launch() {
  app = await _electron.launch({executablePath:exe, args:['--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows','--data', data]})
  page = await app.firstWindow()
  page.setDefaultTimeout(45000)
  page.on('pageerror',error=>console.error(error.message))
  await app.evaluate(({BrowserWindow}) => BrowserWindow.getAllWindows()[0].setContentSize(1280,800))
  page.on('websocket', socket => socket.on('framereceived', frame => {
    const event = JSON.parse(String(frame.payload))
    if (event.type === 'human_turn') turn = event
  }))
}
const decisionRows = new Map()
const actionKinds = new Set()
async function checkViewport() {
  const layout = await page.evaluate(() => {
    const doc = document.scrollingElement
    const rect = selector => document.querySelector(selector)?.getBoundingClientRect()
    const table = rect('.mahjong-table'), hand = rect('.human-controls')
    const visible = el => el.top >= -1 && el.bottom <= innerHeight+1 && el.left >= -1 && el.right <= innerWidth+1
    const faces = [...document.querySelectorAll('.portrait-button')].map(el=>el.getBoundingClientRect())
    const items = [...document.querySelectorAll('.river-square .river-preview,.hand button,.action-bar button')]
    return {
      uniform:!table || (faces.length===3 && faces.every(r=>r.width===r.height && r.width===faces[0].width)),
      top:!table || (table.top < 16 && !document.querySelector('.app-header h1') && !document.querySelector('.game-toolbar span')),
      outer:doc.scrollHeight <= innerHeight+1 && doc.scrollWidth <= innerWidth+1,
      actions:items.every(el => visible(el.getBoundingClientRect())),
      hand:!hand || (visible(hand) && hand.top >= table.bottom-1),
      table:!table || visible(table),
      width:innerWidth, height:innerHeight,
      positions:table && [table.top, table.bottom, rect('.hand').top, rect('.action-bar').top],
      kinds:[...document.querySelectorAll('.action-bar button')].map(b=>b.dataset.action)
    }
  })
  if (layout.positions) {
    const size = layout.width+'x'+layout.height
    const prior = decisionRows.get(size)
    if (prior) assert.deepEqual(layout.positions,prior,'행동 선택지가 달라져도 대국판과 손패 위치 유지')
    decisionRows.set(size,layout.positions)
    for (const kind of layout.kinds.length ? layout.kinds : ['discard']) actionKinds.add(kind)
  }
  for (const key of ['outer','actions','hand','table','top','uniform']) assert.ok(layout[key], JSON.stringify(layout))
}
async function shot(name) {
  await checkViewport()
  await page.screenshot({path:join(evidence,name+'.png')})
}
async function discardOrCall() {
  const previous = turn.action_version
  const win = page.locator('.action-bar button:is([data-action="4"],[data-action="6"]):enabled')
  const discard = page.locator('.hand button:enabled')
  const action = await win.count() ? win : await discard.count() ? discard : page.locator('.action-bar button:enabled')
  await action.first().click()
  const until = Date.now()+15000
  while (previous === turn.action_version && !await page.locator('.result-delivery-card,.match-result').count()) {
    if (Date.now()>until) throw Error('새 행동 상태를 받지 못했습니다.')
    await page.waitForTimeout(15)
  }
}
try {
  await launch()
  await shot('title')
  await button('메인 메뉴로').click()
  await button('새로 시작').waitFor()
  assert.ok(await button('이어하기').isDisabled())
  await shot('menu')
  await button('설정').click()
  await page.getByRole('heading',{name:'설정',exact:true}).waitFor()
  await shot('settings')
  await button('메인 메뉴로').click()
  await button('새로 시작').click()
  await page.locator('.cpu-grid').waitFor()
  await shot('roster')
  {
    const cards = page.locator('button.cpu-card')
    for(let i=0;i<3;i++) await cards.nth(i).click()
    await button('참가 명단 확정').click()
    const badges = page.locator('.portrait-button .seat-wind-tile')
    await badges.first().waitFor()
    assert.deepEqual((await badges.allTextContents()).sort(), (await page.locator('.seat:not(.seat-0) .wind').allTextContents()).sort())
    await page.locator('.portrait-button').first().click()
    const profile = page.locator('.profile-dialog[open]')
    await profile.locator('.seat-body').waitFor()
    await profile.evaluate(el=>Promise.all(el.getAnimations().map(a=>a.finished)))
    await page.screenshot({path:join(evidence,'profile.png')})
    await page.keyboard.press('Escape')
    assert.equal(await page.locator('.game-toolbar').getByText('초기화').count(),0)
  }
  let riverVerified = false
  let verified = false
  let start, key = ''
  for(let step=0;step<1500;step++) {
    const result = page.locator('.result-delivery-card[data-event-id]')
    if(await result.count()) {
      const settlement = await result.getAttribute('data-result-kind') === 'settlement'
      await result.evaluate(el => Promise.all(el.getAnimations().map(a => a.finished)))
      await shot(settlement?'settlement':'hand-result')
      const id = await result.getAttribute('data-event-id')
      await result.locator('button.primary-button').click()
      await page.waitForFunction(id=>document.querySelector('.result-delivery-card')?.dataset.eventId !== id,id)
      if (settlement) break
      continue
    }
    await page.locator('.human-controls').waitFor()
    await page.locator('.hand button:enabled,.action-bar button:enabled').first().waitFor()
    await checkViewport()
    const observation = turn.turn.observation
    const current = [observation.round_wind, observation.kyoku_index, observation.honba].join('/')
    if (current !== key) { start = structuredClone(turn); key = current }
    const riverSeat = observation.discards.findIndex(tiles => tiles.length > 6)
    if (!riverVerified && riverSeat >= 0) {
      await app.evaluate(({BrowserWindow}) => BrowserWindow.getAllWindows()[0].setSize(1000,720))
      await checkViewport()
      console.log('최소 게임 창', await page.evaluate(()=>[innerWidth,innerHeight,document.scrollingElement.scrollHeight]))
      const preview = page.locator('.river-seat-'+riverSeat+' .river-preview')
      const before = (await page.locator('.human-controls').boundingBox()).y
      assert.equal(await preview.locator('.tile').count(),Math.min(18,observation.discards[riverSeat].length))
      await preview.click()
      const dialog = page.getByRole('dialog')
      assert.equal(await dialog.locator('.tile').count(),observation.discards[riverSeat].length)
      await page.screenshot({path:join(evidence,'discards.png')})
      await dialog.getByRole('button',{name:'닫기'}).click()
      assert.equal((await page.locator('.human-controls').boundingBox()).y,before)
      riverVerified = true
    }
    if (!verified && observation.kyoku_index >= 2 && turn.action_version > start.action_version) {
      await shot('table')
      const oldVersion = turn.action_version
      page.once('dialog',d=>d.dismiss())
      await button('저장하고 나가기').click()
      await page.locator('.human-controls').waitFor()
      page.once('dialog',d=>d.accept())
      await button('저장하고 나가기').click()
      await button('이어하기').waitFor()
      // Exit via the actual main menu, then reopen the packaged application.
      page.once('dialog',d=>d.dismiss())
      await button('게임 종료').click()
      await button('이어하기').waitFor()
      page.once('dialog',d=>d.accept())
      const exit = app.waitForEvent('close')
      await button('게임 종료').click()
      await exit
      await launch()
      await button('메인 메뉴로').click()
      await button('이어하기').click()
      await page.locator('.human-controls').waitFor()
      assert.equal(turn.session_id,start.session_id)
      assert.equal(turn.action_version,start.action_version)
      assert.deepEqual(turn.turn,start.turn)
      console.log(JSON.stringify({round:key, scores:observation.scores, restoredScores:turn.turn.observation.scores, before:oldVersion, restored:turn.action_version}))
      verified = true
    }
    await discardOrCall()
    await page.waitForFunction(()=>document.querySelector('.hand button:enabled,.action-bar button:enabled,.result-delivery-card,.match-result'))
  }
  assert.ok(riverVerified,'일곱 장 이상의 실제 버림패 확인')
  assert.ok(verified,'두 번째 이후 국을 실제로 되감아야 합니다.')
  await page.locator('.opponent-sheet').waitFor()
  await button('메인 메뉴로').click()
  page.once('dialog',d=>d.dismiss())
  await button('새로 시작').click()
  assert.ok(await button('이어하기').isEnabled())
  page.once('dialog',d=>d.accept())
  await button('새로 시작').click()
  await page.locator('.cpu-grid').waitFor()
  assert.equal(await page.locator('.cpu-card.selected').count(),0)
  console.log('고정 좌표',Object.fromEntries(decisionRows),'행동 종류',[...actionKinds])
  console.log('PASS 메뉴, 종료, 동일한 국 복원, 최종 정산, 새 게임')
} catch (error) {
  if(page && !page.isClosed()) console.error((await page.locator('body').innerText()).slice(-900))
  throw error
} finally { if(app) await app.close() }
