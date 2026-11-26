import {createContext,useContext,useEffect,useRef,useState} from 'react'
import {apiRequest,type CharacterContent} from './api'
import {pollImage,queueImage,useImageQueue} from './imageQueue'

export type ImageKind='profile'|'full_body'|'cg'|'ending'
export const ImageSettings=createContext({available:false,ready:false})
export const slotPath=(cpu:number,level:number,kind:ImageKind)=>'/api/local/characters/'+cpu+'/stage-images/'+level+'/'+kind
const slotFor=(content:CharacterContent,level:number,kind:ImageKind)=>kind==='ending'?content.ending:content.levels[String(level)][kind]
const latest=new Map<string,{url?:string;message?:string}>()
export function rememberImage(key:string,url:string) {latest.set(key,{url});window.dispatchEvent(new Event('nrnf-image-saved'))}

export function ImageQueueStatus(){
  const q=useImageQueue()
  return q.count ? <aside role="status" className="image-queue-status">이미지 생성 중 · {q.waiting}개 대기</aside>:null
}

export function PromptShortcut({cpu,level,kind}:{cpu:number;level:number;kind:ImageKind}){
  const [draft,setDraft]=useState<string|null>(null),[message,setMessage]=useState('')
  const [revision,setRevision]=useState(0)
  const [busy,setBusy]=useState(false)
  async function edit(){
    setBusy(true);setMessage('')
    try{
      const data=await apiRequest<CharacterContent>('/api/local/characters/'+cpu+'/content')
      const slot=slotFor(data,level,kind)!
      let text=slot.positive
      if((kind==='profile'||kind==='full_body')&&!slot.overrides?.positive){
        const presets=await apiRequest<Record<string,string>>('/api/local/characters/situation-prompts')
        text=presets[kind+'_'+level]
      }
      setRevision(data.revision);setDraft(text)
    }catch(error){setMessage(String(error))}finally{setBusy(false)}
  }
  async function save(){
    setBusy(true)
    try{
      const change=kind==='ending'?{prompts:{ending:{positive:draft}}}:{framing:[{level,kind,positive:draft}]}
      await apiRequest('/api/local/characters/'+cpu+'/content',{method:'PATCH',body:JSON.stringify({expected_revision:revision,...change})})
      setDraft(null);setMessage('저장했습니다. 재생성하면 새 문구를 적용합니다.')
      window.dispatchEvent(new CustomEvent('nrnf-prompt-edited',{detail:cpu}))
    }catch(error){setMessage(String(error))}finally{setBusy(false)}
  }
  return <><button type="button" disabled={busy} onClick={()=>void edit()}>프롬프트 바로 수정</button>
    {draft!==null && <span><label>이미지 구도 프롬프트<textarea value={draft} onChange={e=>setDraft(e.target.value)}/></label>
    <button type="button" disabled={busy} onClick={()=>void save()}>프롬프트 저장</button>
    <button type="button" disabled={busy} onClick={()=>setDraft(null)}>취소</button></span>}
    {message && <small role="status">{message}</small>}</>
}

type Props={cpu:number;level:number;kind:ImageKind;url?:string|null;label:string;className:string;controlsOnly?:boolean;imageOnly?:boolean;onLoaded?:(url:string)=>void}
export function LiveImage({cpu,level,kind,url,label,className,controlsOnly,imageOnly,onLoaded}:Props){
  const settings=useContext(ImageSettings)
  const key=slotPath(cpu,level,kind)
  const q=useImageQueue()
  const anchor=useRef<HTMLSpanElement>(null)
  const [visible,setVisible]=useState(false)
  const [,redraw]=useState(0)
  useEffect(()=>{
    const listener=()=>redraw(n=>n+1)
    window.addEventListener('nrnf-image-saved',listener)
    const observer=new IntersectionObserver(([entry])=>setVisible(entry.isIntersecting))
    if(anchor.current)observer.observe(anchor.current)
    return ()=>{observer.disconnect();window.removeEventListener('nrnf-image-saved',listener)}
  },[])
  async function generate(force:boolean){
    try{await queueImage(key,async()=>{
      const data=await apiRequest<CharacterContent>('/api/local/characters/'+cpu+'/content')
      const slot=slotFor(data,level,kind)!
      if(slot.media&&!force){rememberImage(key,slot.media.url);return}
      if(!data.prompts.appearance.positive.trim())throw Error('캐릭터 외모 프롬프트를 입력해 주세요.')
      let ticket=slot.generation_ticket
      if(!ticket||force)ticket=(await apiRequest<{ticket:string}>(key+'?expected_revision='+data.revision+'&regenerate='+force,{method:'POST'})).ticket
      const path=key+'/'+ticket
      const status=await pollImage(path+'/advance')
      if(status.state!=='ready')throw Error('이미지를 생성하지 못했습니다. 이미지 생성 설정과 ComfyUI를 확인해 주세요.')
      const saved=await apiRequest<CharacterContent>(path+'/'+status.attempt+'/save',{method:'POST'})
      rememberImage(key,slotFor(saved,level,kind)!.media!.url)
      if(saved.image_copy_warning)throw Error(saved.image_copy_warning)
    })}catch(error){latest.set(key,{...latest.get(key),message:String(error)});redraw(n=>n+1)}
  }
  const display=latest.get(key)?.url || url, message=latest.get(key)?.message
  useEffect(()=>{
    if(settings.ready && visible && !controlsOnly && !display && !message)void generate(false)
  },[key,settings.ready,visible,display,message,controlsOnly])
  return <span ref={anchor} className="live-image">
    {!controlsOnly && (display ? <img className={className} src={display} alt={label} onLoad={()=>onLoaded?.(display)}/> :
      <span className={className+' image-empty'}>{q.active===key?'생성 중…':q.pending.has(key)?'생성 대기 중':label+' 없음'}</span>)}
    {!imageOnly && settings.available && <span className="image-actions"><button type="button" disabled={q.pending.has(key)} onClick={()=>void generate(true)}>이미지 재생성</button>
      <PromptShortcut key={key} cpu={cpu} level={level} kind={kind}/></span>}
    {message && !controlsOnly && <small role="status">{message}</small>}</span>
}
