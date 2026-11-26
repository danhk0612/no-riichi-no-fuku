import { useEffect, useState } from 'react'
import {apiRequest} from '../api'
import {pollImage,queueImage,useImageQueue} from '../imageQueue'

type Status = {state:string; attempt?:string}
const labels:Record<string,string> = {
  pending:'화료 CG를 준비하고 있습니다.', unconfigured:'대국 시작 시 이미지 생성 설정이 비어 있습니다.',
  rejected:'ComfyUI가 생성 입력을 검증하지 못해 요청을 거절했습니다.', failed:'화료 CG를 생성하지 못했습니다.', uncertain:'생성 요청의 접수 여부를 확인하지 못했습니다.',
  disconnected:'접수된 이미지 작업의 결과를 읽지 못했습니다.', missing:'저장된 화료 CG 파일이 없거나 변경되었습니다.',
  unavailable:'화료 CG 상태를 읽지 못했습니다.', unsupported:'이 결과의 이미지 형식을 지원하지 않습니다.',
}

export function HandCG({path, generation}:{path:string; generation:string}) {
  const [status,setStatus]=useState<Status>({state:'pending'})
  const [action,setAction]=useState<{retry?:string;regenerate?:boolean}>({})
  const [image,setImage]=useState('')
  const [draft,setDraft]=useState<string|null>(null), [previous,setPrevious]=useState(''), [note,setNote]=useState('')
  const q=useImageQueue()
  const query=new URLSearchParams({generation}).toString()
  useEffect(()=>{
    let current=true
    setStatus({state:'pending'})
    queueImage(path,()=>pollImage(path,query+(action.regenerate?'&regenerate=true':''),action.retry)).then(result=>{
      if(!current)return
      setStatus(result)
      if(result.state==='ready')setImage(path+'/'+result.attempt+'?'+query)
    }).catch(()=>{if(current)setStatus({state:'unavailable'})})
    return ()=>{current=false}
  },[path,query,action])
  async function edit(){
    try{
      if(draft===null){
        const data=await apiRequest<{positive:string}>(path+'/prompt?'+query)
        setPrevious(data.positive);setDraft(data.positive);setNote('')
      }else{
        await apiRequest(path+'/prompt?'+query,{method:'PUT',body:JSON.stringify({positive:draft,previous})})
        setDraft(null);setNote('저장했습니다. 재생성하면 적용됩니다.')
      }
    }catch(error){setNote(String(error))}
  }
  return <>{image && <img className="hand-cg-backdrop" src={image} alt="화료 결과 CG" />}
    <button type="button" disabled={q.pending.has(path)} onClick={()=>setAction({regenerate:true})}>화료 CG 재생성</button>
    {draft!==null && <label>화료 CG 프롬프트<textarea value={draft} onChange={e=>setDraft(e.target.value)}/></label>}
    <button type="button" onClick={()=>void edit()}>{draft===null?'프롬프트 바로 수정':'프롬프트 저장'}</button>
    {note && <small role="status">{note}</small>}
    {status.state!=='ready' && <p role="status" className="result-asset-status">{status.state==='pending' && q.active!==path?'생성 대기 중':labels[status.state]}
      {['failed','rejected','uncertain','missing','disconnected','unavailable'].includes(status.state) &&
        <button type="button" onClick={()=>setAction({retry:status.attempt})}>{status.state==='disconnected'?'기존 작업 다시 조회':status.state==='unavailable'?'상태 다시 확인':'다시 시도'}</button>}
    </p>}</>
}
