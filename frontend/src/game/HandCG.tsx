import { useEffect, useState } from 'react'

type Status = {state:string; attempt?:string}
const labels:Record<string,string> = {
  pending:'화료 CG를 준비하고 있습니다.', unconfigured:'대국 시작 시 이미지 생성 설정이 비어 있습니다.',
  rejected:'ComfyUI가 생성 입력을 검증하지 못해 요청을 거절했습니다.', failed:'화료 CG를 생성하지 못했습니다.', uncertain:'생성 요청의 접수 여부를 확인하지 못했습니다.',
  disconnected:'접수된 이미지 작업의 결과를 읽지 못했습니다.', missing:'저장된 화료 CG 파일이 없거나 변경되었습니다.',
  unavailable:'화료 CG 상태를 읽지 못했습니다.', unsupported:'이 결과의 이미지 형식을 지원하지 않습니다.',
}

export function HandCG({path, generation}:{path:string; generation:string}) {
  const [status,setStatus]=useState<Status>({state:'pending'})
  const [action,setAction]=useState<{retry?:string}>({})
  const [image,setImage]=useState('')
  useEffect(()=>{
    const abort=new AbortController()
    let timer:ReturnType<typeof setTimeout>, objectUrl=''
    setStatus({state:'pending'});setImage('')
    const query=new URLSearchParams({generation})
    async function step(retry?:string) {
      try {
        const q=new URLSearchParams(query)
        if(retry)q.set('retry',retry)
        const response=await fetch(path+'?'+q,{method:'POST',signal:abort.signal})
        if(!response.ok)throw Error()
        const data:Status=await response.json()
        if(abort.signal.aborted)return
        if(data.state==='ready'){
          const file=await fetch(path+'/'+encodeURIComponent(data.attempt!)+'?'+query,{signal:abort.signal})
          if(!file.ok)throw Error()
          const blob=await file.blob()
          if(abort.signal.aborted)return
          objectUrl=URL.createObjectURL(blob);setImage(objectUrl)
        }
        setStatus(data)
        if(data.state==='pending')timer=setTimeout(()=>void step(),1500)
      }catch{if(!abort.signal.aborted)setStatus({state:'unavailable'})}
    }
    void step(action.retry)
    return ()=>{abort.abort();clearTimeout(timer);if(objectUrl)URL.revokeObjectURL(objectUrl)}
  },[path,generation,action])
  return <>{image && <img className="hand-cg-backdrop" src={image} alt="화료 결과 CG" />}
    {status.state!=='ready' && <p role="status" className="result-asset-status">{labels[status.state]}
      {['failed','rejected','uncertain','missing','disconnected','unavailable'].includes(status.state) &&
        <button type="button" onClick={()=>setAction({retry:status.attempt})}>{status.state==='disconnected'?'기존 작업 다시 조회':status.state==='unavailable'?'상태 다시 확인':'다시 시도'}</button>}
    </p>}</>
}
