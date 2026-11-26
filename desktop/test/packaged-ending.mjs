import { enterDesktopGame } from '../../frontend/tests/desktop-menu.mjs'
import assert from 'node:assert/strict'
import { dirname, join } from 'node:path'
import {readFileSync,writeFileSync} from 'node:fs'
import {createRequire} from 'node:module'

const {_electron}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const [exe,data,planFile,reportFile]=process.argv.slice(2)
const plan=JSON.parse(readFileSync(planFile,'utf8'))
const report={source:process.env.W11_SOURCE_SHA, fixture:plan,checks:[],passed:false}
const record=message=>{report.checks.push(message);writeFileSync(reportFile,JSON.stringify(report,null,2))}
const noMedia = plan.no_media === true
const mediaRequests = []
let app,page,turn
async function launch(){
  app=await _electron.launch({executablePath:exe,args:['--data',data],timeout:90000})
  page=await app.firstWindow({timeout:90000})
  page.setDefaultTimeout(30000)
  page.on('websocket', socket => socket.on('framereceived', frame => {
    const message = JSON.parse(String(frame.payload))
    if (message.type === 'human_turn') turn = message
  }))
  if (noMedia) page.on('request', req => {
    const path = new URL(req.url()).pathname
    if (req.resourceType() === 'media' || /\/cg(?:\/|$)|\/advance$|\/catalog$|\/prompt$/.test(path)) mediaRequests.push(path)
  })
  await enterDesktopGame(page)
}
async function stop(){
  if(!app)return
  const exit=new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>reject(Error('packaged application did not exit')),30000)
    app.process().once('exit',(code)=>{clearTimeout(timeout);code===0?resolve():reject(Error('packaged application exit '+code))})
  })
  page.once('dialog', d=>d.accept())
  await Promise.all([exit,app.evaluate(({BrowserWindow})=>{setImmediate(()=>BrowserWindow.getAllWindows()[0].close())})])
  app=null
}
const state=()=>page.evaluate(async()=>{const r=await fetch('/api/local/play');if(!r.ok)throw Error('local play '+r.status);return r.json()})
try{
  await launch()
  await page.locator('.human-controls').waitFor()
  assert.equal((await state()).active_session_id,plan.session)
  const seat=page.locator('.seat-1')
  await seat.locator('.portrait-button').click()
  if (noMedia) {
    assert.equal(plan.previous_matches.length, 8)
    assert.equal(await seat.locator('img.seat-body').count(), 0)
    record('eight real settlements from a fresh silent profile restored at match nine')
  } else {
    await seat.locator('img.seat-body').evaluate(i=>i.decode())
    record('restored final hand and decoded current-stage seat image')
  }
  await page.keyboard.press('Escape')
  // The fixture was saved before the final action. Resume now starts at the hand boundary.
  while (turn.action_version < plan.prior_actions) {
    const version = turn.action_version
    const action = turn.turn.legal_actions[0]
    const choice = action.type ? page.locator('.action-bar button').first() :
      page.locator('.hand > *').nth(turn.turn.observation.hands[0].indexOf(action.tile))
    await choice.click()
    const until = Date.now()+15000
    while (turn.action_version === version) {
      if (Date.now() > until) throw Error('정해진 행동을 재생하지 못했습니다.')
      await page.waitForTimeout(15)
    }
  }
  await page.locator(plan.selector).nth(plan.index).click()
  for(let i=0;i<8;i++){
    const card=page.locator('.result-delivery-card[data-event-id]')
    await card.waitFor()
    if(await card.getAttribute('data-result-kind')==='settlement')break
    const event=await card.getAttribute('data-event-id')
    await card.locator('button.primary-button').click()
    await page.waitForFunction(id=>document.querySelector('.result-delivery-card')?.dataset.eventId!==id,event)
  }
  const result=page.locator('[data-result-kind="settlement"]')
  const id = await result.getAttribute('data-event-id')
  if (noMedia) {
    await result.getByRole('region', {name:'패배 단계 변경'}).getByText(/단계 2 → 3/).waitFor()
    assert.equal(await result.getByRole('button',{name:'CG만 보기'}).count(),0)
    assert.deepEqual((await state()).roster.map(row => row.defeat_stage), [3,3,3])
    record('ninth match completed all three participants using stored scores without CG')
  } else {
    await result.getByText('W11 fixture line').waitFor()
    await result.locator('img.settlement-body').evaluate(i=>i.decode())
    await result.locator('img.settlement-profile').evaluate(i=>i.decode())
    await result.getByRole('button',{name:'CG만 보기'}).click()
    await page.getByRole('dialog').getByRole('button',{name:'확대',exact:true}).click()
    await page.getByRole('dialog').getByText('150%').waitFor()
    await page.getByRole('dialog').press('Escape')
    await result.screenshot({ path: join(dirname(reportFile), 'settlement-screen.png') })
    record('real last action led to stage 2 to 3 settlement and CG viewer')
  }
  await stop()
  await launch()
  await page.locator('[data-result-kind="settlement"]').waitFor()
  assert.equal(await page.locator('[data-result-kind="settlement"]').getAttribute('data-event-id'),id)
  await page.getByRole('button',{name:'정산 확인'}).click()
  await page.getByRole('region',{name:'엔딩'}).waitFor()
  assert.equal((await state()).phase,'ending_pending')
  await page.getByRole('region',{name:'엔딩'}).screenshot({path:join(dirname(reportFile),'ending-screen.png')})
  record('same settlement survived process restart and explicit acknowledgement reached real ending')
  if (noMedia) {
    await stop()
    await launch()
    const ending = page.getByRole('region',{name:'엔딩'})
    await ending.getByText('오마케에서는 완료한 참가자들과 동풍전을 계속할 수 있습니다.').waitFor()
    assert.equal((await state()).phase, 'ending_pending')
    assert.equal(await ending.locator('img,audio').count(), 0)
    await ending.screenshot({path:join(dirname(reportFile), 'offline-ending.png')})
  }
  await page.getByRole('button',{name:'오마케로 계속하기'}).click()
  await page.locator('.opponent-sheet').waitFor()
  await stop()
  await launch()
  await page.locator('.opponent-sheet').waitFor()
  assert.equal((await state()).phase,'omake')
  if (noMedia) {
    for (let i=0;i<3;i++) await page.locator('button.cpu-card:not(.selected):enabled').first().click()
    await page.getByRole('button',{name:'동풍전 시작',exact:true}).click()
    await page.locator('.human-controls').waitFor()
    const omake = await state()
    assert.ok(omake.active_session_id && omake.active_session_id !== plan.session)
    assert.deepEqual(mediaRequests, [])
    record('ending survived restart and a playable omake match opened with no renderer media or generation requests observed')
  }
  await stop()
  report.passed=true
  record('acknowledged ending survived another process restart in omake selection')
}catch(error){
  report.error=String(error?.stack||error)
  report.screen=await page?.locator('body').innerText({timeout:2000}).catch(()=>'unavailable')
  writeFileSync(reportFile,JSON.stringify(report,null,2))
  throw error
}finally{if(app)await app.close().catch(()=>{})}
