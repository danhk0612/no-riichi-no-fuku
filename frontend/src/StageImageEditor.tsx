import {situationLabels} from './SituationPrompts'
import {useEffect, useRef, useState} from 'react'
import {apiRequest, type CharacterContent} from './api'

const labels:Record<string,string>={pending:'생성 중입니다.', uncertain:'접수 여부를 확인하지 못했습니다.', rejected:'ComfyUI가 생성 입력을 검증하지 못해 요청을 거절했습니다.', failed:'생성에 실패했습니다.', missing:'생성 파일이 없습니다.',disconnected:'접수된 이미지 작업의 결과를 읽지 못했습니다.',unconfigured:'생성 설정이 필요합니다.'}
type Slot = CharacterContent['levels'][string]['profile']
export function StageImageEditor({token,cpu,level,kind,label,revision,slot,disabled,onSaved}:{
  token:string;cpu:number;level:number;kind:'profile'|'full_body'|'cg';label:string;revision:number;
  slot:Slot;disabled:boolean;onSaved:(next:Slot)=>void
}) {
  const path='/api/local/characters/'+cpu+'/stage-images/'+level+'/'+kind
  const [ticket,setTicket]=useState(slot.generation_ticket)
  const [event,setEvent]=useState('')
  const [attempt,setAttempt]=useState<string>()
  const [state,setState]=useState('')
  const [message,setMessage]=useState('')
  const [busy,setBusy]=useState(false)
  const serial=useRef(0), timer=useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  useEffect(()=>()=>{serial.current++;clearTimeout(timer.current)},[])
  async function run(fresh:boolean) {
    const id=++serial.current
    const current=()=>id===serial.current
    clearTimeout(timer.current);setBusy(true);setMessage('')
    let t=ticket
    try {
      if(fresh){
        setState('');setAttempt(undefined)
        const res=await apiRequest<{ticket:string}>(path+'?expected_revision='+revision+(event ? '&event='+event : ''),{method:'POST'},token)
        if(!current())return
        t=res.ticket;setTicket(t);setAttempt(undefined)
      }
      if(!t)return
      const retry=!fresh && ['failed','rejected','missing','uncertain','disconnected'].includes(state) && attempt ? '?retry='+attempt : ''
      const step=async (query:string)=>{
        try {
          const s=await apiRequest<{state:string;attempt?:string}>(path+'/'+t+'/advance'+query,{method:'POST'},token)
          if(!current())return
          setState(s.state);setAttempt(s.attempt)
          if(s.state==='pending')timer.current=setTimeout(()=>void step(''),1500)
          else setBusy(false)
        }catch(e){if(current()){setMessage(String(e));setBusy(false)}}
      }
      await step(retry)
    }catch(e){if(current()){setMessage(String(e));setBusy(false)}}
  }
  async function save(){
    const id=++serial.current;setBusy(true);setMessage('')
    try{
      const result=await apiRequest<CharacterContent>(path+'/'+ticket+'/'+attempt+'/save',{method:'POST'},token)
      if(id===serial.current){onSaved(result.levels[String(level)][kind]);setState('saved');setMessage(label+' 이미지를 저장했습니다.')}
    }catch(e){if(id===serial.current)setMessage(String(e))}
    finally{if(id===serial.current)setBusy(false)}
  }
  return <section aria-label={label+' 이미지'} className="stage-image-editor">
    {slot.media ? <figure><img alt={'저장된 '+label} src={slot.media.url}/><figcaption>{slot.media.source==='generated'?'직접 저장한 이미지':'캐릭터팩 이미지'}</figcaption></figure> : <p>{label} 이미지 미등록</p>}
    {kind === 'cg' && <label>CG 상황<select value={event} disabled={busy || disabled} onChange={e => setEvent(e.target.value)}>
      <option value="">기본 장면</option>
      {Object.entries(situationLabels).map(([key,text]) => <option key={key} value={key}>{text}</option>)}
    </select></label>}
    <button type="button" disabled={disabled||busy} onClick={()=>void run(true)}>{label} 생성</button>
    {ticket && state!=='ready' && state!=='saved' && !busy && <button type="button" disabled={disabled} onClick={()=>void run(false)}>{state==='disconnected'?'기존 작업 다시 조회':attempt?'다시 시도':'이전 요청 확인'}</button>}
    {ticket && state==='ready' && attempt && <figure><img alt={label+' 생성 미리보기'} src={path+'/'+ticket+'/'+attempt}/><figcaption>미리보기 · 저장하면 이 단계에 적용됩니다.</figcaption>
      <button type="button" disabled={disabled||busy} onClick={()=>void save()}>이 이미지 저장</button></figure>}
    {(message||labels[state]) && <p role="status">{message||labels[state]}</p>}
  </section>
}
