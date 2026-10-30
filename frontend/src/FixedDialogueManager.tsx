import { useEffect, useRef, useState } from 'react'
import { getFixedCandidates, getFixedDialogues, patchFixedDialogues } from './api'
import type { FixedCandidate, FixedDialogue, FixedEdit, FixedSlot } from './api'

const slots: [FixedSlot, string][] = [['win','화료'], ['defeat_stage_1','패배 단계 1'], ['defeat_stage_2','패배 단계 2'], ['defeat_stage_3','패배 단계 3'], ['match_first','기존 보충 승리']]
export function FixedDialogueManager({ token, cpus, onDirty, onSaving }: { token: string; cpus: {id: number; name: string; slug: string}[]; onDirty: (value: boolean) => void; onSaving: (value: boolean) => void }) {
  const [id, setId] = useState<number | null>(null)
  const [data, setData] = useState<FixedDialogue | null>(null)
  const [candidates, setCandidates] = useState<FixedCandidate[]>([])
  const [edits, setEdits] = useState<Partial<Record<FixedSlot, FixedEdit>>>({})
  const [open, setOpen] = useState<FixedSlot | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const sequence = useRef(0)
  const dirty = Object.keys(edits).length > 0
  useEffect(() => { onDirty(dirty) }, [dirty, onDirty])
  useEffect(() => () => { sequence.current++ }, [])
  async function load(next: number) {
    if (busy || (dirty && !window.confirm('저장하지 않은 고정 대사를 버리시겠습니까?'))) return
    const request = ++sequence.current
    setId(next); setData(null); setCandidates([]); setEdits({}); setOpen(null); setError('')
    try {
      const [result, choices] = await Promise.all([getFixedDialogues(token, next), getFixedCandidates(token, next)])
      if (request === sequence.current) { setData(result); setCandidates(choices.items) }
    } catch (e) { if (request === sequence.current) setError(e instanceof Error ? e.message : '조회 실패') }
  }
  async function save() {
    if (!data || id === null || busy || !dirty) return
    setBusy(true); onSaving(true); setError('')
    try { const result = await patchFixedDialogues(token, id, data.revision, edits); setData(result); setEdits({}); setOpen(null) }
    catch (e) { setError(e instanceof Error ? e.message : '저장 실패') }
    finally { setBusy(false); onSaving(false) }
  }
  const name = cpus.find(cpu => cpu.id === id)?.name ?? ''
  return <section className="sound-card" aria-label="고정 대사"><h3>고정 대사</h3><p>편집 자료는 과거 게임 결과와 별개입니다. 허용 변수: {'{{character_name}}'}</p>
    <label>캐릭터<select aria-label="고정 대사 캐릭터" value={id ?? ''} disabled={busy} onChange={e => void load(Number(e.target.value))}><option value="" disabled>캐릭터 선택</option>{cpus.map(cpu => <option key={cpu.id} value={cpu.id}>{cpu.name} · {cpu.slug}</option>)}</select></label>
    {error && <p role="alert" className="form-error">{error}</p>}{id !== null && <button type="button" disabled={busy} onClick={() => void load(id)}>다시 조회</button>}
    {data && <>{slots.map(([key, label]) => {
      const saved = data.slots[key], edit = edits[key]
      const selected = edit && 'legacy_dialogue_id' in edit ? candidates.find(c => c.id === edit.legacy_dialogue_id) : undefined
      const text = edit && 'text' in edit ? edit.text : selected ? selected.text : saved?.text ?? ''
      return <fieldset key={key} disabled={busy}><legend>{label}</legend><p>{saved ? saved.text === '' ? '직접 빈 값' : '설정됨' : '미설정'}</p>
        <label>대사<textarea aria-label={`${label} 대사`} value={text} onChange={e => setEdits(current => ({...current, [key]: {text: e.target.value}}))} /></label>
        <p>미리보기: {text.replaceAll('{{character_name}}', () => name)}</p>
        {saved?.origin && <p>출처 ID {saved.origin.legacy_dialogue_id} · 당시 원문: {saved.origin.text}</p>}
        {!saved && <><button type="button" onClick={() => setOpen(open === key ? null : key)}>기존 문구 선택</button>{open === key && <div>{candidates.filter(c => c.event_key === key).length ? candidates.filter(c => c.event_key === key).map(c => <label key={c.id}><input type="radio" name={`candidate-${key}`} disabled={!c.active} checked={selected?.id === c.id} onChange={() => setEdits(current => ({...current, [key]: {legacy_dialogue_id: c.id, expected_source_text: c.text}}))} />ID {c.id} · {c.active ? '활성' : '비활성'} · {c.text}</label>) : <p>후보가 없습니다.</p>}</div>}</>}
      </fieldset>
    })}<button type="button" disabled={busy || !dirty} onClick={() => void save()}>{busy ? '저장 중…' : '고정 대사 저장'}</button></>}
  </section>
}
