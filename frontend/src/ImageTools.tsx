import {useRef, useState} from 'react'
import {createPortal} from 'react-dom'

type Props = {
  label: string
  regenerateLabel: string
  disabled?: boolean
  onGenerate: () => void
  loadPrompt: () => Promise<string>
  savePrompt: (text: string) => Promise<void>
}

export function ImageTools({label,regenerateLabel,disabled,onGenerate,loadPrompt,savePrompt}:Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const request = useRef(0)
  const [mode,setMode] = useState<'generate'|'edit'>('generate')
  const [draft,setDraft] = useState<string|null>(null)
  const [saving,setSaving] = useState(false)
  const [error,setError] = useState('')
  async function open(next:typeof mode) {
    const id = ++request.current
    setMode(next); setDraft(null); setError('')
    dialog.current?.showModal()
    if(next === 'edit') {
      try {
        const text = await loadPrompt()
        if(request.current === id) setDraft(text)
      } catch(e) { if(request.current === id) setError(String(e)) }
    }
  }
  async function save() {
    if(draft === null || saving) return
    setSaving(true)
    try { await savePrompt(draft); dialog.current?.close() }
    catch(e) { setError(String(e)) }
    finally { setSaving(false) }
  }
  const title = mode === 'edit' ? label+' 프롬프트' : regenerateLabel
  return <span className="image-tools">
    <button className="image-icon" type="button" aria-haspopup="dialog" title={regenerateLabel} aria-label={regenerateLabel} disabled={disabled} onClick={()=>void open('generate')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 4v6h-6M20 10a8 8 0 1 0 0 5"/></svg>
    </button>
    <button className="image-icon" type="button" aria-haspopup="dialog" title="프롬프트 수정" aria-label={label+' 프롬프트 수정'} onClick={()=>void open('edit')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16-1 5 5-1L20 8l-4-4ZM14 6l4 4"/></svg>
    </button>
    {createPortal(<dialog ref={dialog} className="image-tool-dialog" aria-label={title}
      onCancel={e=>{if(saving)e.preventDefault()}} onClose={()=>{request.current++}}>
      <h2>{title}</h2>
      {mode==='edit' && (draft!==null ? <textarea autoFocus aria-label="이미지 구도 프롬프트" value={draft} onChange={e=>setDraft(e.target.value)}/> : !error && <p role="status">불러오는 중…</p>)}
      {error && <p role="alert">{error}</p>}
      <footer><button type="button" disabled={saving} onClick={()=>dialog.current?.close()}>취소</button>
      {mode==='edit' ? <button type="button" disabled={saving || draft===null} onClick={()=>void save()}>프롬프트 저장</button>
        : <button type="button" disabled={disabled} onClick={()=>{dialog.current?.close();onGenerate()}}>{regenerateLabel.endsWith('재생성')?'재생성':'생성'}</button>}</footer>
    </dialog>,document.body)}
  </span>
}
