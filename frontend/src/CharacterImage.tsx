import {ImageSettings, LiveImage,type ImageKind} from './LiveImage'
import { type ReactNode, useContext, useState } from 'react'

export function CharacterImage({url, label, className,cpu,level,kind,imageOnly,placeholder}: {url?:string|null; label:string; className:string;cpu?:number;level?:number;kind?:ImageKind;imageOnly?:boolean;placeholder?:ReactNode}) {
  const [failed,setFailed]=useState<string|null>(null)
  const settings=useContext(ImageSettings)
  if(settings.available && cpu && level!==undefined && kind)return <LiveImage cpu={cpu} level={level} kind={kind} url={url} label={label} className={className} imageOnly={imageOnly} placeholder={placeholder}/>
  if (!url || failed===url) return <span className={className+' image-empty'}>{placeholder ?? label+' 없음'}</span>
  return <img className={className} src={url} alt={label} onError={()=>setFailed(url)}/>
}

export function Measurements({values}: {values?:Record<string,string|null>}) {
  return <>{Object.entries({height:'키',bust:'가슴(B)',waist:'허리(W)',hips:'엉덩이(H)'}).map(([k,label])=>
    values?.[k] && <span key={k}>{label} {values[k]} cm </span>)}</>
}
