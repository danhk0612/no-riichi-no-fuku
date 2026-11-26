import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ executablePath:process.env.TEST_CHROMIUM_EXECUTABLE || undefined })
try {
  const page = await browser.newPage()
  page.setDefaultTimeout(6000)
  await page.addInitScript(()=>{window.nrnfDesktop={isDesktop:true}})
  const requests=[]
  let settings={endpoint:'http://127.0.0.1:8188',revision:0,characters:{},common:{model:'',encoder:'',vae:'',sampler:'euler',scheduler:'normal',width:1024,height:1024,steps:20,cfg:4,loras:[]}}
  await page.route('**/api/**',async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/generation-settings/catalog')){
      requests.push('check');return route.fulfill({status:502,json:{detail:'연결할 수 없습니다.'}})
    }
    if(path.endsWith('/generation-settings')){
      if(route.request().method()==='PUT'){
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
  await panel.getByLabel('적용 대상').selectOption('1')
  await panel.getByRole('button',{name:'LoRA 추가'}).click()
  await panel.getByLabel('LoRA 1',{exact:true}).fill('char')
  await panel.getByLabel('강도').fill('0')
  assert.deepEqual(requests,[])
  await panel.getByRole('button',{name:'연결 확인·목록 갱신'}).click()
  await panel.getByText('연결할 수 없습니다.').waitFor()
  await panel.getByRole('button',{name:'설정 저장',exact:true}).click()
  await panel.getByText('설정을 저장했습니다.').waitFor()
  assert.equal(settings.common.model,'base')
  assert.deepEqual(settings.characters['1'],{model:'',loras:[{name:'char',strength:0}]})
  assert.deepEqual(requests,['check'])
  console.log('PASS: offline editing and saving after an explicit, failed catalog check')
} finally {await browser.close()}
