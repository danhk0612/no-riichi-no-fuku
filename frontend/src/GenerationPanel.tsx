import { useEffect, useState } from 'react'
import { apiRequest, listLocalCharacters } from './api'

type Lora = { name: string; strength: number }
type Character = { model: string; loras: Lora[] }
type Common = Character & { encoder: string; vae: string; sampler: string; scheduler: string; width: number; height: number; steps: number; cfg: number }
type Saved = { endpoint: string; common: Common; characters: Record<string, Character>; revision: number }
type Catalog = { choices: Record<string, string[]>; missing_nodes: string[] }
const path = '/api/local/generation-settings'

export function GenerationPanel({token, close}: {token: string; close: () => void}) {
  const [data, setData] = useState<Saved | null>(null)
  const [people, setPeople] = useState<{id:number; name:string}[]>([])
  const [person, setPerson] = useState('')
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    setData(null); setNote(''); setCatalog(null)
    Promise.all([apiRequest<Saved>(path, {}, token), listLocalCharacters(token)]).then(([d,p]) => {
      if (active) { setData(d); setPeople(p) }
    }).catch(e => { if (active) setNote(String(e)) })
    return () => { active = false }
  }, [token, reload])
  const target: Character = data ? (person ? data.characters[person] ?? { model:'', loras:[] } : data.common) : {model:'',loras:[]}
  function patch(change: Partial<Common>) {
    if (!data) return
    setNote('')
    setData(person ? {...data, characters:{...data.characters,[person]:{...target,...change}}} : {...data,common:{...data.common,...change}})
  }
  async function run(check: boolean) {
    if (!data || busy) return
    setBusy(true); setNote('')
    try {
      const { revision, ...config } = data
      if (check) {
        setCatalog(null)
        const c = await apiRequest<Catalog>(path+'/catalog',{method:'POST', body:JSON.stringify({endpoint:data.endpoint})},token)
        setCatalog(c); setNote(c.missing_nodes.length ? '연결됨 · 없는 필수 노드: '+c.missing_nodes.join(', ') : '연결됨 · 기본 생성 노드 확인')
      } else {
        const saved = await apiRequest<Saved>(path,{method:'PUT',body:JSON.stringify({...config,expected_revision:revision})},token)
        setData(saved); setNote('설정을 저장했습니다.')
      }
    } catch(e) { setNote(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false) }
  }
  return <section className="selection-panel" aria-label="이미지 생성 설정">
    <div className="panel-heading"><h2>이미지 생성 설정</h2><button disabled={busy} onClick={close}>닫기</button></div>
    <p>ComfyUI 없이 설정을 저장할 수 있습니다. 연결 확인은 설치된 모델과 노드 목록만 읽습니다.</p>
    {data && <fieldset disabled={busy}>
      <label>ComfyUI 주소 <input value={data.endpoint} onChange={e=>{setData({...data,endpoint:e.target.value});setCatalog(null);setNote('')}} /></label>
      <button onClick={()=>void run(true)}>연결 확인·목록 갱신</button>
      <p><label>적용 대상 <select value={person} onChange={e=>setPerson(e.target.value)}><option value="">공통 설정</option>{people.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label></p>
      {person && <p>모델을 비우면 공통 모델을 사용합니다. 캐릭터 LoRA는 공통 LoRA 뒤에 순서대로 적용됩니다.</p>}
      <label>모델 <input list="gen-model" value={target.model} onChange={e=>patch({model:e.target.value})}/></label>
      {!person && <>{([['encoder','텍스트 인코더'],['vae','VAE'],['sampler','샘플러'],['scheduler','스케줄러']] as const).map(([key,label])=><p key={key}><label>{label} <input list={'gen-'+key} value={data.common[key]} onChange={e=>patch({[key]:e.target.value})}/></label></p>)}
        {([['width','가로'],['height','세로'],['steps','스텝'],['cfg','CFG']] as const).map(([key,label])=><label key={key}>{label} <input type="number" step={key==='cfg'?'any':key==='steps'?1:16} value={data.common[key]} onChange={e=>patch({[key]:Number(e.target.value)})}/></label>)}</>}
      <h3>LoRA 적용 순서</h3>
      {target.loras.map((l,i)=><p key={i}>
        <label>LoRA {i+1} <input list="gen-lora" value={l.name} onChange={e=>patch({loras:target.loras.map((v,n)=>n===i?{...v,name:e.target.value}:v)})}/></label>
        <label>강도 <input type="number" step="any" value={l.strength} onChange={e=>patch({loras:target.loras.map((v,n)=>n===i?{...v,strength:Number(e.target.value)}:v)})}/></label>
        <button disabled={!i} onClick={()=>{const rows=[...target.loras];[rows[i-1],rows[i]]=[rows[i],rows[i-1]];patch({loras:rows})}}>위로</button>
        <button onClick={()=>patch({loras:target.loras.filter((_,n)=>i!==n)})}>삭제</button></p>)}
      <button onClick={()=>patch({loras:[...target.loras,{name:'',strength:1}]})}>LoRA 추가</button>
      <button onClick={()=>void run(false)}>설정 저장</button>
      {catalog && Object.entries(catalog.choices).map(([k,vs])=><datalist key={k} id={'gen-'+k}>{vs.map(v=><option key={v} value={v}/>)}</datalist>)}
    </fieldset>}
    {note && <p role="status">{note}</p>}
    <button disabled={busy} onClick={()=>setReload(reload+1)}>저장된 설정 다시 불러오기</button>
  </section>
}
