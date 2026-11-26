import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ executablePath:process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
try {
  const page = await browser.newPage()
  page.setDefaultTimeout(6000)
  await page.addInitScript(()=>{window.nrnfDesktop={isDesktop:true}})
  const requests=[]
  let failRead=false, writes=0, difficultyReads=0
  let settings={endpoint:'http://127.0.0.1:8188',revision:0,characters:{},common:{model:'',encoder:'',vae:'',sampler:'euler',scheduler:'normal',width:1024,height:1024,steps:20,cfg:4,loras:[]}}
  await page.route('**/api/**',async route=>{
    const path=new URL(route.request().url()).pathname
    if(path==='/api/local/difficulty'){
      assert.equal(route.request().method(),'GET')
      difficultyReads++
      return route.fulfill({json:{setting:5, revision:0}})
    }
    if(path.endsWith('/generation-settings/catalog')){
      requests.push('check')
      if(requests.length===2)return route.fulfill({json:{choices:{},missing_nodes:[],supports_anima_encoder:false}})
      return route.fulfill({status:502,json:{detail:'연결할 수 없습니다.'}})
    }
    if(path.endsWith('/generation-settings')){
      if(failRead && route.request().method()==='GET')return route.fulfill({status:503,json:{detail:'일시적인 조회 실패'}})
      if(route.request().method()==='PUT'){
        writes++
        const {expected_revision,...rest}=route.request().postDataJSON()
        assert.equal(expected_revision,settings.revision);settings={...rest,revision:expected_revision+1}
      }
      return route.fulfill({json:settings})
    }
    if(path==='/api/admin/cpus')return route.fulfill({json:[{id:1,name:'테스트 CPU'}]})
    if(path==='/api/local/play')return route.fulfill({json:{phase:'progress',generation:'test',roster:[],active_session_id:null,recent_session_id:null}})
    if(path==='/api/local/sound-selection')return route.fulfill({json:{effect_set_id:null,bgm_ids:[],tracks:[],effect_sets:[]}})
    return route.fulfill({json:[]})
  })
  await page.goto(process.env.TEST_BASE_URL || 'http://127.0.0.1:5173')
  const open=page.getByRole('button',{name:'이미지 생성 설정',exact:true})
  await open.click()
  const panel=page.getByRole('region',{name:'이미지 생성 설정'})
  await panel.getByLabel('모델',{exact:true}).fill('base')
  await panel.getByRole('button',{name:'LoRA 추가'}).click()
  await panel.getByLabel('LoRA 1',{exact:true}).fill('char')
  await panel.getByLabel('강도').fill('0')
  assert.deepEqual(requests,[])
  await panel.getByRole('button',{name:'연결 확인·목록 갱신'}).click()
  await panel.getByText('연결할 수 없습니다.').waitFor()
  await panel.getByRole('button',{name:'연결 확인·목록 갱신'}).click()
  await panel.getByText(/이 설치는 Anima 인코더 유형.*지원하지 않습니다/).waitFor()
  await panel.getByRole('button',{name:'설정 저장',exact:true}).click()
  await panel.getByText('설정을 저장했습니다.').waitFor()
  assert.equal(settings.common.model,'base')
  assert.deepEqual(settings.common.loras,[{name:'char',strength:0}])
  assert.deepEqual(requests,['check','check'])
  const model=panel.getByLabel('모델',{exact:true}), reload=panel.getByRole('button',{name:'저장된 설정 다시 불러오기'})
  await model.fill('draft-model')
  const difficultyButton = page.getByRole('button', { name:'난이도 설정', exact:true })
  await difficultyButton.click()
  const difficulty = page.getByRole('region', { name:'난이도 설정' })
  await difficulty.getByLabel('게임 난이도').selectOption('8')
  const readsAfterOpening = difficultyReads
  assert.equal(await panel.isVisible(), false)
  await page.getByRole('button', { name:'게임 화면으로' }).click()
  assert.equal(await difficulty.isVisible(), false)
  await open.click()
  assert.equal(await model.inputValue(), 'draft-model')
  assert.equal(await panel.getByLabel('강도').inputValue(), '0')
  await difficultyButton.click()
  assert.equal(await difficulty.getByLabel('게임 난이도').inputValue(), '8')
  await difficulty.getByRole('button', {name:'닫기'}).click()
  assert.equal(await difficultyButton.evaluate(button => button === document.activeElement), true)
  await open.click()
  assert.equal(difficultyReads, readsAfterOpening, 'switching back must retain the open editor')
  assert.equal(writes, 1)
  assert.deepEqual(requests, ['check','check'])
  failRead=true
  await reload.click()
  await panel.getByText(/일시적인 조회 실패/).waitFor()
  assert.equal(await model.inputValue(),'draft-model')
  assert.equal(await model.isEnabled(),true)
  assert.equal(await panel.getByLabel('LoRA 1',{exact:true}).inputValue(),'char')
  failRead=false
  await reload.click()
  await page.waitForFunction(()=>document.querySelector('input[list="gen-model"]')?.value==='base')
  assert.equal(writes,1,'reload must not save the draft')
  assert.deepEqual(requests,['check','check'])
  console.log('PASS: offline save, catalog check, failed refresh retains draft, successful refresh restores saved settings')
} finally {await browser.close()}
