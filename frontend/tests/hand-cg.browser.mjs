import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser=await chromium.launch({executablePath:process.env.TEST_CHROMIUM_EXECUTABLE || undefined})
try {
  const page=await browser.newPage()
  page.setDefaultTimeout(6000)
  await page.addInitScript(()=>{window.nrnfDesktop={isDesktop:true}})
  const env={version:1,generation:'g',session_id:'s',acked_ordinal:0,terminal_ordinal:null,route:'result',delivery_revision:1,head:{ordinal:1,event_id:'e',kind:'hand',payload:{kind:'hand',fact_snapshot:{start:{bakaze:'E',kyoku:1},winners:[{actor:1,target:0,hora_log_offset:1,win_kind:'ron',score:{band:1}}]},displayed_hora_log_offset:1,content:{version:1,scene:{stage:0,media:null,generation_input:{}},dialogues:[{cpu_id:1,slot:'win',text:'화료 대사'}]}}}}
  let cgCalls=0
  let retry=0, held, began, cached=false, disconnected=false
  const waiting=new Promise(resolve=>{began=resolve})
  await page.route('**/api/**',async route=>{
    const u=new URL(route.request().url()), p=u.pathname
    const json=data=>route.fulfill({json:data})
    if(p==='/api/local/sound-selection')return json({effect_set_id:null,bgm_ids:[],tracks:[],effect_sets:[]})
    if(p==='/api/local/play')return json({phase:'progress',roster:[],generation:'g',result_resume:{session_id:'s',route:'result'}})
    if(p.endsWith('/results'))return json(env)
    if(p.endsWith('/results/e/cg')){
      cgCalls++
      if(disconnected && u.searchParams.get('retry')!=='known')return json({state:'disconnected',attempt:'known'})
      if(cached)return json({state:'ready',attempt:'cached'})
      if(u.searchParams.get('retry')==='a'){retry++;return json({state:'ready',attempt:'b'})}
      return json({state:'uncertain',attempt:'a'})
    }
    if(p.endsWith('/cg/cached'))return route.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1kAAAAASUVORK5CYII=','base64')})
    if(p.endsWith('/cg/b')){
      began()
      await new Promise(resolve=>{held=resolve})
      return route.fulfill({contentType:'image/png',body:Buffer.from('unused')}).catch(()=>{})
    }
    if(p.endsWith('/results/ack'))return json({...env,acked_ordinal:1,delivery_revision:2,head:{ordinal:2,event_id:'e2',kind:'hand',payload:{kind:'hand',fact_snapshot:{start:{bakaze:'E',kyoku:2},winners:[]}}}})
    return json({})
  })
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  await page.getByText('화료 대사').waitFor()
  await page.getByRole('button',{name:'다시 시도'}).click()
  await Promise.race([waiting,page.waitForTimeout(6000).then(()=>{throw Error('image request did not start')})])
  await page.getByRole('button',{name:'확인하고 다음 결과 보기'}).click()
  await page.getByRole('heading',{name:'국 결과 · E2국'}).waitFor()
  held()
  assert.equal(await page.locator('.hand-cg-backdrop').count(),0)
  cached=true
  await page.reload()
  await page.getByRole('img',{name:'화료 결과 CG'}).waitFor()
  assert.equal(await page.locator('.hand-cg-backdrop').evaluate(async img=>{await img.decode();return img.naturalWidth}),1)
  assert.equal(retry,1)
  disconnected=true
  await page.reload()
  await page.getByRole('button',{name:'기존 작업 다시 조회'}).click()
  await page.getByRole('img',{name:'화료 결과 CG'}).waitFor()
  delete env.head.payload.content.scene.generation_input
  env.head.payload.content.scene.missing_candidates=['situation']
  const before=cgCalls
  await page.reload()
  await page.getByText('화료 CG 생략 · 미등록 후보: 화료 상황').waitFor()
  await page.getByText('화료 대사').waitFor()
  assert.equal(cgCalls,before)
  assert.equal(await page.getByRole('button',{name:'확인하고 다음 결과 보기'}).isEnabled(),true)
  console.log('PASS: hand dialogue, explicit retry, next hand before image, no stale backdrop')
}finally{await browser.close()}
