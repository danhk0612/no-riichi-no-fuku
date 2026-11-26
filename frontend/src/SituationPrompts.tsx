import {useEffect, useState} from 'react'
import {apiRequest} from './api'

export const situationLabels = {
  chi: '치', pon: '퐁', kan: '깡', riichi: '리치', ron: '론', tsumo: '쯔모', defeat: '대국 패배',
}
const levelLabels = {profile: '프로필 구도', full_body: '전신 구도', expression: '표정', clothing: '의상 상태'}
type Values = Record<string, string>
const path = '/api/local/characters/situation-prompts'

export function SituationPrompts({token}: {token: string}) {
  const [saved, setSaved] = useState<Values>({})
  const [drafts, setDrafts] = useState<Values>({})
  const [event, setEvent] = useState('chi')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  useEffect(() => {
    let active = true
    apiRequest<Values>(path, {}, token).then(values => { if (active) setSaved(values) })
      .catch(error => { if (active) setMessage(String(error)) })
    return () => { active = false }
  }, [token])
  async function save() {
    setBusy(true)
    try {
      const values = await apiRequest<Values>(path + '/' + event, {method: 'PUT',
        body: JSON.stringify({previous: saved[event], text: drafts[event]})}, token)
      setSaved(values)
      setDrafts(current => { const next = {...current}; delete next[event]; return next })
      setMessage('공통 프롬프트를 저장했습니다.')
    } catch (error) { setMessage(String(error)) }
    finally { setBusy(false) }
  }
  return <fieldset disabled={busy}><legend>모든 캐릭터에 적용할 프롬프트</legend>
    <label>편집 항목<select value={event} onChange={e => {setEvent(e.target.value); setMessage('')}}>
      {Object.entries(levelLabels).map(([key,label]) => <optgroup key={key} label={label}>{[0,1,2,3].map(level =>
        <option key={level} value={key+'_'+level}>{level}단계 {label}</option>)}</optgroup>)}
      <optgroup label="대국 상황">{Object.entries(situationLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</optgroup>
    </select></label>
    <label>공통 프롬프트<textarea disabled={saved[event] === undefined} value={drafts[event] ?? saved[event] ?? ''}
      onChange={e => setDrafts({...drafts, [event]: e.target.value})} /></label>
    <p>비워서 저장하면 기본 문구로 돌아갑니다. 대국 중 화료 CG에는 대국 시작 시점의 설정이 적용됩니다.</p>
    <button type="button" disabled={drafts[event] === undefined} onClick={() => void save()}>공통 문구 저장</button>
    <p role="status">{message}</p>
  </fieldset>
}
