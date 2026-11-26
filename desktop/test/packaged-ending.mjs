import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {createRequire} from 'node:module'

const {_electron}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const [exe,data,planFile,reportFile]=process.argv.slice(2)
const plan=JSON.parse(readFileSync(planFile,'utf8'))
const report={source:process.env.W11_SOURCE_SHA, fixture:plan,checks:[],passed:false}
const record=message=>{report.checks.push(message);writeFileSync(reportFile,JSON.stringify(report,null,2))}
let app,page
async function launch(){
  app=await _electron.launch({executablePath:exe,args:['--data',data],timeout:90000})
  page=await app.firstWindow({timeout:90000})
  page.setDefaultTimeout(30000)
}
async function stop(){
  if(!app)return
  const exit=new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>reject(Error('packaged application did not exit')),30000)
    app.process().once('exit',(code)=>{clearTimeout(timeout);code===0?resolve():reject(Error('packaged application exit '+code))})
  })
  await Promise.all([exit,app.evaluate(({BrowserWindow})=>{setImmediate(()=>BrowserWindow.getAllWindows()[0].close())})])
  app=null
}
const state=()=>page.evaluate(async()=>{const r=await fetch('/api/local/play');if(!r.ok)throw Error('local play '+r.status);return r.json()})
try{
  await launch()
  await page.locator('.human-controls').waitFor()
  assert.equal((await state()).active_session_id,plan.session)
  const seat=page.locator('.seat-1')
  await seat.locator('summary').click()
  await seat.locator('img.seat-body').evaluate(i=>i.decode())
  record('restored real final turn and decoded current-stage seat image')
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
  await result.getByText('W11 fixture line').waitFor()
  const id=await result.getAttribute('data-event-id')
  await result.locator('img.settlement-body').evaluate(i=>i.decode())
  await result.locator('img.settlement-profile').evaluate(i=>i.decode())
  await result.getByRole('button',{name:'CG만 보기'}).click()
  await page.getByRole('dialog').getByRole('button',{name:'확대',exact:true}).click()
  await page.getByRole('dialog').getByText('150%').waitFor()
  record('real last action led to stage 2 to 3 settlement and CG viewer')
  await stop()
  await launch()
  await page.locator('[data-result-kind="settlement"]').getByText('W11 fixture line').waitFor()
  assert.equal(await page.locator('[data-result-kind="settlement"]').getAttribute('data-event-id'),id)
  await page.getByRole('button',{name:'정산 확인'}).click()
  await page.getByRole('region',{name:'엔딩'}).waitFor()
  assert.equal((await state()).phase,'ending_pending')
  record('same settlement survived process restart and explicit acknowledgement reached real ending')
  await page.getByRole('button',{name:'오마케로 계속하기'}).click()
  await page.locator('.selection-panel').waitFor()
  await stop()
  await launch()
  await page.locator('.selection-panel').waitFor()
  assert.equal((await state()).phase,'omake')
  await stop()
  report.passed=true
  record('acknowledged ending survived another process restart in omake selection')
}catch(error){
  report.error=String(error?.stack||error)
  report.screen=await page?.locator('body').innerText({timeout:2000}).catch(()=>'unavailable')
  writeFileSync(reportFile,JSON.stringify(report,null,2))
  throw error
}finally{if(app)await app.close().catch(()=>{})}
