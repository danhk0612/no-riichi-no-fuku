import { useState } from 'react'

export function CharacterImage({url, label, className}: {url?:string|null; label:string; className:string}) {
  const [failed,setFailed]=useState<string|null>(null)
  if (!url || failed===url) return <span className={className+' image-empty'}>{label} 없음</span>
  return <img className={className} src={url} alt={label} onError={()=>setFailed(url)}/>
}

export function Measurements({values}: {values?:Record<string,string|null>}) {
  return <>{Object.entries({height:'키',bust:'가슴(B)',waist:'허리(W)',hips:'엉덩이(H)'}).map(([k,label])=>
    values?.[k] && <span key={k}>{label} {values[k]} cm </span>)}</>
}
