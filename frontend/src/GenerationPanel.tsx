import { useEffect, useState } from 'react'
import { apiRequest } from './api'

type Lora = { name: string; strength: number; trigger?: string }
type Character = { model: string; loras: Lora[] }
type Common = Character & { encoder: string; vae: string; sampler: string; scheduler: string; width: number; height: number; steps: number; cfg: number; model_revision?: number }
type Saved = { endpoint: string; common: Common; characters: Record<string, Character>; revision: number }
type Catalog = { choices: Record<string, string[]>; missing_nodes: string[]; supports_anima_encoder: boolean | null }
const path = '/api/local/generation-settings'

export function GenerationPanel({token, close, characterId}: {characterId?: number; token: string; close?: () => void}) {
  const person = characterId ? String(characterId) : ''
  const [data, setData] = useState<Saved | null>(null)
  const [original, setOriginal] = useState<Saved | null>(null)
  const listId = (key: string) => (person ? 'char-' + person + '-' : 'gen-') + key
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    setLoading(true); setNote('')
    apiRequest<Saved>(path, {}, token).then(d => {
      if (active) { setData(d); setOriginal(d); setCatalog(null) }
    }).catch(e => { if (active) setNote(e instanceof Error ? e.message : String(e)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, reload])
  const target: Character = data ? (person ? data.characters[person] ?? { model:'', loras:[] } : data.common) : {model:'',loras:[]}
  function patch(change: Partial<Common>) {
    if (!data) return
    setNote('')
    setData(person ? {...data, characters:{...data.characters,[person]:{...target,...change}}} : {...data,common:{...data.common,...change}})
  }
  async function run(check: boolean) {
    if (!data || !original || busy || loading) return
    setBusy(true); setNote('')
    try {
      if (check) {
        setCatalog(null)
        const c = await apiRequest<Catalog>(path+'/catalog',{method:'POST', body:JSON.stringify({endpoint:data.endpoint})},token)
        setCatalog(c)
        const details = c.missing_nodes.length ? ['없는 필수 노드: '+c.missing_nodes.join(', ')] : ['기본 생성 노드 확인']
        if (!c.missing_nodes.includes('CLIPLoader')) {
          details.push(c.supports_anima_encoder === true ? 'Anima 인코더 유형 확인'
            : c.supports_anima_encoder === false ? '이 설치는 Anima 인코더 유형(qwen_image)을 지원하지 않습니다.'
            : 'Anima 인코더 유형의 지원 여부를 확인할 수 없습니다.')
        }
        setNote(['연결됨', ...details].join(' · '))
      } else {
        const latest = await apiRequest<Saved>(path, {}, token)
        const scope = (value: Saved) => person ? value.characters[person] : [value.common, value.endpoint]
        if (JSON.stringify(scope(original)) !== JSON.stringify(scope(latest))) throw Error('설정이 변경됐습니다. 다시 불러온 뒤 저장해 주세요.')
        const { revision, ...config } = latest
        const changes = person ? {characters:{...latest.characters,[person]:target}} : {common:data.common,endpoint:data.endpoint}
        const saved = await apiRequest<Saved>(path,{method:'PUT',body:JSON.stringify({...config,...changes,expected_revision:revision})},token)
        setData(saved); setOriginal(saved); window.dispatchEvent(new Event('nrnf-generation-settings')); setNote('설정을 저장했습니다.')

      }
    } catch(e) { setNote(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false) }
  }
  return <section className="selection-panel generation-editor" aria-label={person ? '캐릭터 모델·LoRA' : '이미지 생성 설정'}>
    <div className="panel-heading"><h2>{person ? '캐릭터 모델·LoRA' : '이미지 생성 설정'}</h2>{close && <button disabled={busy} onClick={close}>닫기</button>}</div>
    {data && <fieldset disabled={busy || loading}>
      {!person && <><h3>ComfyUI 연결</h3>
      <label>ComfyUI 주소 <input value={data.endpoint} onChange={e=>{setData({...data,endpoint:e.target.value});setCatalog(null);setNote('')}} /></label></>}
      <button onClick={()=>void run(true)}>연결 확인·목록 갱신</button>
      <h3>{person ? '캐릭터 모델 (비우면 공통 모델 사용)' : '모델과 샘플링'}</h3>
      <div className="generation-grid">
      <label>모델 <input list={listId('model')} value={target.model} onChange={e=>patch({model:e.target.value})}/></label>
      {!person && <>{([['encoder','텍스트 인코더'],['vae','VAE'],['sampler','샘플러'],['scheduler','스케줄러']] as const).map(([key,label])=><label key={key}>{label} <input list={listId(key)} value={data.common[key]} onChange={e=>patch({[key]:e.target.value})}/></label>)}
        {([['width','가로'],['height','세로'],['steps','스텝'],['cfg','CFG']] as const).map(([key,label])=><label key={key}>{label} <input type="number" step={key==='cfg'?'any':key==='steps'?1:16} value={data.common[key]} onBlur={()=>{if(key==='width'||key==='height'){
          const aligned=Math.min(16384,Math.max(16,Math.round(data.common[key]/16)*16))
          if(aligned!==data.common[key]){patch({[key]:aligned});setNote(label+' 해상도를 '+aligned+'픽셀로 맞췄습니다.')}
        }}} onChange={e=>patch({[key]:Number(e.target.value)})}/></label>)}</>}
      {!person && <p><label>모델 파일 버전 <input type="number" min="1" value={data.common.model_revision ?? 1} onChange={e=>patch({model_revision:Number(e.target.value)})}/></label> 같은 이름의 모델·LoRA 파일을 교체했다면 이 숫자를 올려 주세요.</p>}
      </div><h3>{person ? '캐릭터 LoRA' : '공통 LoRA'} 적용 순서</h3>
      {target.loras.map((l,i)=><p key={i}>
        <label>LoRA {i+1} <input list={listId('lora')} value={l.name} onChange={e=>patch({loras:target.loras.map((v,n)=>n===i?{...v,name:e.target.value}:v)})}/></label>
        {person && <label>트리거 단어 <input value={l.trigger ?? ''} onChange={e=>patch({loras:target.loras.map((v,n)=>n===i?{...v,trigger:e.target.value}:v)})}/></label>}
        <label>강도 <input type="number" step="any" value={l.strength} onChange={e=>patch({loras:target.loras.map((v,n)=>n===i?{...v,strength:Number(e.target.value)}:v)})}/></label>
        <button disabled={!i} onClick={()=>{const rows=[...target.loras];[rows[i-1],rows[i]]=[rows[i],rows[i-1]];patch({loras:rows})}}>위로</button>
        <button onClick={()=>patch({loras:target.loras.filter((_,n)=>i!==n)})}>삭제</button></p>)}
      <button onClick={()=>patch({loras:[...target.loras,{name:'',strength:1}]})}>LoRA 추가</button>
      <button onClick={()=>void run(false)}>설정 저장</button>
      {catalog && Object.entries(catalog.choices).map(([k,vs])=><datalist key={k} id={listId(k)}>{vs.map(v=><option key={v} value={v}/>)}</datalist>)}
    </fieldset>}
    {!person && <p>가로와 세로는 저장 시 가장 가까운 16픽셀 단위로 맞춥니다 (16–16384).</p>}
    {note && <p role="status">{note}</p>}
    <button disabled={busy || loading} onClick={()=>setReload(reload+1)}>저장된 설정 다시 불러오기</button>
  </section>
}
