import {ImageTools} from './ImageTools'
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

export function SlotImageTools({cpu,level,kind,label,regenerateLabel,disabled,onGenerate}:{
  cpu:number;level:number;kind:ImageKind;label:string;regenerateLabel:string;disabled:boolean;onGenerate:()=>void
}) {
  const revision=useRef(0)
  async function loadPrompt() {
    const data=await apiRequest<CharacterContent>('/api/local/characters/'+cpu+'/content')
    revision.current=data.revision
    const slot=slotFor(data,level,kind)!
    if((kind==='profile'||kind==='full_body')&&!slot.overrides?.positive) {
      const presets=await apiRequest<Record<string,string>>('/api/local/characters/situation-prompts')
      return presets[kind+'_'+level] ?? ''
    }
    return slot.positive
  }
  async function savePrompt(positive:string) {
    const change=kind==='ending'?{prompts:{ending:{positive}}}:{framing:[{level,kind,positive}]}
    await apiRequest('/api/local/characters/'+cpu+'/content',{method:'PATCH',body:JSON.stringify({expected_revision:revision.current,...change})})
    window.dispatchEvent(new CustomEvent('nrnf-prompt-edited',{detail:cpu}))
  }
  return <ImageTools label={label} regenerateLabel={regenerateLabel} disabled={disabled} onGenerate={onGenerate} loadPrompt={loadPrompt} savePrompt={savePrompt}/>
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
    {!imageOnly && settings.available && <SlotImageTools key={key} cpu={cpu} level={level} kind={kind} label={label} regenerateLabel={label+' 재생성'} disabled={q.pending.has(key)} onGenerate={()=>void generate(true)}/>}
    {message && !controlsOnly && <small role="status">{message}</small>}</span>
}
