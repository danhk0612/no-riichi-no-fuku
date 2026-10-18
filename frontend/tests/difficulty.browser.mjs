import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
try {
  const page = await browser.newPage(); page.setDefaultTimeout(8000)
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  await page.addInitScript(() => { window.nrnfDesktop = { isDesktop: true } })
  let setting = { version: 1, revision: 0, setting: 5, applies_to: 'next_match' }
  let fail = false, savedBody, socket, holdSave, releaseSave, signalSave, enteredSave
  const cpus = () => [1,2,3].map(id => ({ id, name: `CPU ${id}`, style: 'balanced', defeat_stage: 0,
    profile_image_key: null, short_description: 'test-only', difficulty_preview: { level: setting.setting === 5 ? 3 : 8 }, difficulty_setting_revision: setting.revision }))
  const play = { generation: 'test-diff', phase: 'progress', roster: [1,2,3].map(id=>({ cpu_character_id:id, defeat_stage:0 })), active_session_id:null, recent_session_id:null }
  await page.route('**/api/**', async route => {
    const req=route.request(), path=new URL(req.url()).pathname
    if(path==='/api/local/difficulty') {
      if(req.method()==='GET')return route.fulfill({json:setting})
      savedBody=req.postDataJSON()
      if(fail)return route.fulfill({status:409,json:{detail:'test-conflict'}})
      if (holdSave) { signalSave(); await holdSave }
      setting={...setting,setting:savedBody.setting,revision:setting.revision+1}
      return route.fulfill({json:setting})
    }
    if(path==='/api/profile/me')return route.fulfill({json:{player_name:'test-only'}})
    if(path==='/api/local/play')return route.fulfill({json:play})
    if(path==='/api/game/sessions/active')return route.fulfill({json:null})
    if(path==='/api/local/play/roster-candidates')return route.fulfill({json:cpus()})
    if(path==='/api/local/sound-selection')return route.fulfill({json:{effect_set_id:null,bgm_ids:[],tracks:[],effect_sets:[]}})
    if(path==='/api/game/sessions')return route.fulfill({json:{session_id:'test-session',generation:play.generation,players:[{seat:0,name:'human',isHuman:true},...[1,2,3].map(seat=>({seat,name:`CPU ${seat}`,isHuman:false}))]}})
    throw new Error(`Unexpected API ${path}`)
  })
  await page.routeWebSocket('**/api/game/**', ws => { socket=ws; ws.onMessage(data => {
    const message=JSON.parse(data)
    if(message.type==='authenticate')ws.send(JSON.stringify({type:'human_turn',generation:play.generation,session_id:'test-session',action_version:0,
      cpu_difficulties:[1,2,3].map(seat=>({seat,cpu_character_id:seat,level:8,profile_version:'test-only',reason:'stage_setting'})),
      turn:{observation:{hands:[[],[],[],[]],melds:[[],[],[],[]],discards:[[],[],[],[]],scores:[25000,25000,25000,25000],riichi_declared:[false,false,false,false],dora_indicators:[],honba:0,riichi_sticks:0,round_wind:0,kyoku_index:0,oya:0,player_id:0},legal_actions:[]}}))
  }) })
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  await page.getByText('다음 대국 난이도 3/10').first().waitFor()
  await page.locator('.cpu-card').first().click()
  await page.getByRole('button',{name:'난이도 설정',exact:true}).click()
  const panel=page.getByRole('region',{name:'난이도 설정'}), select=panel.getByRole('combobox',{name:'게임 난이도'})
  await select.selectOption('10');fail=true
  await panel.getByRole('button',{name:'난이도 저장'}).click()
  await panel.getByRole('alert').filter({hasText:'test-conflict'}).waitFor()
  assert.equal(await select.inputValue(),'10')
  assert.equal(await page.locator('.cpu-card.selected').count(),1)
  fail=false;await panel.getByRole('button',{name:'난이도 저장'}).click()
  await panel.getByRole('status').waitFor()
  assert.deepEqual(savedBody,{setting:10,expected_revision:0})
  await page.getByText('다음 대국 난이도 8/10').first().waitFor()
  assert.equal(await page.locator('.cpu-card.selected').count(),1)
  await page.locator('.cpu-card').nth(1).click();await page.locator('.cpu-card').nth(2).click()
  holdSave=new Promise(resolve=>{releaseSave=resolve});enteredSave=new Promise(resolve=>{signalSave=resolve})
  await select.selectOption('1');await panel.getByRole('button',{name:'난이도 저장'}).click();await enteredSave
  await page.getByRole('button',{name:'동풍전 시작',exact:true}).click()
  await page.getByText('현재 대국 난이도').waitFor()
  const current=await page.locator('.current-difficulty').innerText()
  releaseSave();await panel.getByRole('status').waitFor()
  assert.equal(await page.locator('.cpu-grid').count(),0,'late setting save reopened selection during active match')
  assert.equal(await page.locator('.current-difficulty').innerText(),current)
  assert.equal(await page.locator('.human-controls').count(),1)
  assert.deepEqual(errors,[])
  console.log('PASS difficulty: preview, draft/conflict, selection preservation, saved revision, active snapshot')
} finally { await browser.close() }
