import {useEffect,useRef,useState} from 'react'
import {CharacterImage} from '../CharacterImage'
import type {StageTransition} from './types'

function CGViewer({url}:{url:string}) {
  const dialog=useRef<HTMLDialogElement>(null), view=useRef<HTMLDivElement>(null), img=useRef<HTMLImageElement>(null)
  const [zoom,setZoom]=useState(1), [pan,setPan]=useState({x:0,y:0})
  const drag=useRef<{id:number;x:number;y:number;px:number;py:number}|null>(null)
  function constrain(x:number,y:number,z:number) {
    const v=view.current, i=img.current
    if (!v || !i?.naturalWidth) return {x:0,y:0}
    const scale=Math.min(v.clientWidth/i.naturalWidth,v.clientHeight/i.naturalHeight)*z
    const maxX=Math.max(0,(i.naturalWidth*scale-v.clientWidth)/2)
    const maxY=Math.max(0,(i.naturalHeight*scale-v.clientHeight)/2)
    return {x:Math.max(-maxX,Math.min(maxX,x)),y:Math.max(-maxY,Math.min(maxY,y))}
  }
  function change(z:number) {setZoom(z);setPan(p=>constrain(p.x,p.y,z))}
  return <>
    <button type="button" onClick={()=>{setZoom(1);setPan({x:0,y:0});dialog.current?.showModal()}}>CG만 보기</button>
    <dialog ref={dialog} className="cg-viewer" aria-label="결과 CG 감상" onClose={()=>{drag.current=null}}>
      <div className="cg-canvas" ref={view} tabIndex={0} aria-label="확대 후 드래그 또는 방향키로 이동"
        onPointerDown={e=>{if(e.button!==0 || zoom===1)return;e.currentTarget.setPointerCapture(e.pointerId);drag.current={id:e.pointerId,x:e.clientX,y:e.clientY,px:pan.x,py:pan.y}}}
        onPointerMove={e=>{const d=drag.current;if(d?.id===e.pointerId)setPan(constrain(d.px+e.clientX-d.x,d.py+e.clientY-d.y,zoom))}}
        onLostPointerCapture={()=>{drag.current=null}}
        onKeyDown={e=>{const delta:Record<string,[number,number]>={ArrowLeft:[-40,0],ArrowRight:[40,0],ArrowUp:[0,-40],ArrowDown:[0,40]}
          const step=delta[e.key];if(step){e.preventDefault();setPan(p=>constrain(p.x+step[0],p.y+step[1],zoom))}}}>
        <img ref={img} draggable={false} src={url} alt="감상용 결과 CG" style={{transform:'translate('+pan.x+'px,'+pan.y+'px) scale('+zoom+')'}}/>
      </div>
      <div className="cg-tools"><button type="button" disabled={zoom<=1} onClick={()=>change(zoom-.5)}>축소</button>
        <output>{zoom*100}%</output><button type="button" disabled={zoom>=4} onClick={()=>change(zoom+.5)}>확대</button>
        <button type="button" onClick={()=>change(1)}>원래 크기</button><button type="button" onClick={()=>dialog.current?.close()}>결산으로 돌아가기</button></div>
    </dialog>
  </>
}

export function SettlementScene({transition:t,stage,text,url,hasCG,failed}:{
  transition:StageTransition;stage:number;text:string|null;url?:string|null;hasCG:boolean;failed:boolean
}) {
  const [loaded,setLoaded]=useState(false),[broken,setBroken]=useState(false)
  const [skipWait,setSkipWait]=useState(false)
  useEffect(()=>{
    if (!hasCG || loaded || failed || broken) return
    const timer=setTimeout(()=>setSkipWait(true),1500)
    return ()=>clearTimeout(timer)
  },[hasCG,loaded,failed,broken])
  const reveal=loaded || !hasCG || failed || broken || skipWait
  return <section className="stage-change" aria-label="패배 단계 변경">
    <h3>{t.name} · 단계 {t.from_stage} → {stage}</h3>
    <div className="settlement-scene">
      {url && !broken && <img className="settlement-cg" src={url} alt={'단계 '+stage+' 결과 CG'} onLoad={()=>setLoaded(true)} onError={()=>setBroken(true)}/>}
      {(!url || broken) && <p role="status">{failed || broken ? 'CG를 불러오지 못했습니다.' : hasCG ? 'CG를 불러오는 중입니다.' : '등록된 결과 CG가 없습니다.'}</p>}
      {reveal && <><CharacterImage url={t.full_body?.url} label={t.name+' 전신'} className="settlement-body"/>
      <div className="settlement-line">
        <CharacterImage url={t.profile?.url} label={t.name+' 프로필'} className="settlement-profile"/>
        <div><strong>{t.name}</strong><p>{text || '등록된 패배 대사가 없습니다.'}</p></div>
      </div></>}
    </div>
    {url && loaded && !broken && <CGViewer url={url}/>}
  </section>
}
