import { useEffect, useRef, useState } from 'react'
import {
  confirmSharedPromptChange, createSharedPrompt, getPromptCandidates,
  getSharedPromptDefault, listSharedPrompts, patchSharedPrompt,
  previewSharedPromptChange, putPromptCandidates, putSharedPromptDefault,
} from './api'
import type { LocalCharacterChoice, SharedPromptCandidates, SharedPromptDefault, SharedPromptImpact, SharedPromptItem, SharedPromptKind } from './api'

const KINDS: { id: SharedPromptKind; label: string }[] = [
  { id: 'clothing_state', label: '복장 상태' }, { id: 'pose', label: '포즈' },
]
const LEVELS = ['정상', '상의 겉옷 탈의', '속옷 세트', '전체 탈의']
type Draft = { label: string; positive: string; negative: string }

export function SharedPromptManager({ accessToken, cpus }: { accessToken: string; cpus: LocalCharacterChoice[] }) {
  const [level, setLevel] = useState(0)
  const [kind, setKind] = useState<SharedPromptKind>('clothing_state')
  const [cpuId, setCpuId] = useState<number | null>(null)
  const [items, setItems] = useState<SharedPromptItem[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [candidate, setCandidate] = useState<SharedPromptCandidates | null>(null)
  const [candidateIds, setCandidateIds] = useState<string[]>([])
  const [candidateDrafts, setCandidateDrafts] = useState<Record<string, string[]>>({})
  const [defaultValue, setDefaultValue] = useState<SharedPromptDefault | null>(null)
  const [defaultChoice, setDefaultChoice] = useState('')
  const [defaultDrafts, setDefaultDrafts] = useState<Record<string, string>>({})
  const [impact, setImpact] = useState<SharedPromptImpact | null>(null)
  const [action, setAction] = useState<'move' | 'delete'>('move')
  const [targetLevel, setTargetLevel] = useState(1)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const request = useRef(0)
  const activeCpu = cpuId ?? cpus[0]?.id ?? null
  const scopeKey = `${activeCpu ?? ''}:${level}:${kind}`

  useEffect(() => { if (cpuId === null && cpus.length) setCpuId(cpus[0].id) }, [cpus, cpuId])
  async function load() {
    const current = ++request.current
    setLoading(true); setError(null); setImpact(null)
    try {
      const [listing, fallback, candidates] = await Promise.all([
        listSharedPrompts(accessToken, kind, level), getSharedPromptDefault(accessToken, level, kind),
        activeCpu === null ? Promise.resolve(null) : getPromptCandidates(accessToken, activeCpu, level, kind),
      ])
      if (current !== request.current) return
      setItems(listing.items); setDefaultValue(fallback)
      setDefaultChoice(Object.hasOwn(defaultDrafts, `${level}:${kind}`) ? defaultDrafts[`${level}:${kind}`] : fallback.item_id ?? '')
      setCandidate(candidates)
      setCandidateIds(Object.hasOwn(candidateDrafts, scopeKey) ? candidateDrafts[scopeKey] : candidates?.stored_item_ids ?? [])
      setSelectedId((previous) => listing.items.some((item) => item.id === previous) ? previous : listing.items[0]?.id ?? '')
    } catch (caught) { if (current === request.current) setError(message(caught)) }
    finally { if (current === request.current) setLoading(false) }
  }
  useEffect(() => { void load(); return () => { request.current += 1 } }, [accessToken, level, kind, activeCpu]) // selection changes invalidate earlier responses

  const selected = items.find((item) => item.id === selectedId) ?? null
  const draftKey = selected?.id ?? `new:${level}:${kind}`
  const draft: Draft = drafts[draftKey] ?? { label: selected?.label ?? '', positive: selected?.positive ?? '', negative: selected?.negative ?? '' }
  const dirty = !!selected
    ? draft.label !== selected.label || draft.positive !== selected.positive || draft.negative !== selected.negative
    : !!draft.label || !!draft.positive || !!draft.negative
  const candidateDirty = !!candidate && JSON.stringify(candidateIds) !== JSON.stringify(candidate.stored_item_ids)
  const defaultDirty = !!defaultValue && defaultChoice !== (defaultValue.item_id ?? '')
  function changeDraft(field: keyof Draft, value: string) {
    setDrafts((current) => ({ ...current, [draftKey]: { ...draft, [field]: value } }))
  }
  async function saveItem() {
    if (busy || !draft.label.trim()) return
    setBusy(true); setError(null)
    try {
      const saved = selected
        ? await patchSharedPrompt(accessToken, selected.id, selected.revision, {
          ...(draft.label !== selected.label ? { label: draft.label } : {}),
          ...(draft.positive !== selected.positive ? { positive: draft.positive } : {}),
          ...(draft.negative !== selected.negative ? { negative: draft.negative } : {}),
        })
        : await createSharedPrompt(accessToken, { kind, level, ...draft })
      setDrafts((value) => { const next = { ...value }; delete next[draftKey]; return next })
      await load(); setSelectedId(saved.id)
    } catch (caught) { setError(message(caught)) }
    finally { setBusy(false) }
  }
  async function saveDefault() {
    if (busy || !defaultValue || !defaultDirty) return
    setBusy(true); setError(null)
    try {
      const next = await putSharedPromptDefault(accessToken, level, kind, defaultValue.revision, defaultChoice || null)
      const resolved = activeCpu === null ? null : await getPromptCandidates(accessToken, activeCpu, level, kind)
      setDefaultValue(next); setDefaultChoice(next.item_id ?? ''); setCandidate(resolved)
      setDefaultDrafts((current) => { const result = { ...current }; delete result[`${level}:${kind}`]; return result })
    }
    catch (caught) { setError(message(caught)) }
    finally { setBusy(false) }
  }
  async function saveCandidates() {
    if (busy || !candidate || activeCpu === null || !candidateDirty) return
    setBusy(true); setError(null)
    try {
      const next = await putPromptCandidates(accessToken, activeCpu, level, kind, candidate.revision, candidateIds)
      setCandidate(next); setCandidateIds(next.stored_item_ids)
      setCandidateDrafts((current) => { const result = { ...current }; delete result[scopeKey]; return result })
    }
    catch (caught) { setError(message(caught)) }
    finally { setBusy(false) }
  }
  async function preview() {
    if (busy || !selected || dirty) return
    setBusy(true); setError(null)
    try {
      const value = await previewSharedPromptChange(accessToken, selected.id, {
        expected_revision: selected.revision, action, ...(action === 'move' ? { target_level: targetLevel } : {}),
      })
      setImpact(value)
    } catch (caught) { setError(message(caught)) }
    finally { setBusy(false) }
  }
  async function confirm() {
    if (busy || !selected || !impact) return
    setBusy(true); setError(null)
    try {
      await confirmSharedPromptChange(accessToken, selected.id, {
        expected_revision: selected.revision, action, ...(action === 'move' ? { target_level: targetLevel } : {}), preview_digest: impact.preview_digest,
      })
      setImpact(null); setSelectedId(''); await load()
    } catch (caught) { setImpact(null); setError(message(caught)) }
    finally { setBusy(false) }
  }

  return <section className="sound-card content-editor shared-prompt-manager" aria-label="공유 복장 상태·포즈 관리">
    <h3>공유 복장 상태·포즈</h3>
    <p className="muted">공유 문구는 공통 항목에 한 번 저장합니다. 새 항목은 캐릭터 후보에 자동 추가되지 않습니다.</p>
    <div className="shared-prompt-controls">
      <label>Level<select value={level} disabled={busy} onChange={(event) => { setLevel(Number(event.target.value)); setImpact(null) }}>{LEVELS.map((label, index) => <option key={index} value={index}>Level {index} · {label}</option>)}</select></label>
      <label>종류<select value={kind} disabled={busy} onChange={(event) => { setKind(event.target.value as SharedPromptKind); setImpact(null) }}>{KINDS.map((entry) => <option key={entry.id} value={entry.id}>{entry.label}</option>)}</select></label>
      <label>캐릭터<select value={activeCpu ?? ''} disabled={busy || !cpus.length} onChange={(event) => { setCpuId(Number(event.target.value)); setImpact(null) }}>{cpus.map((cpu) => <option key={cpu.id} value={cpu.id}>{cpu.name}</option>)}</select></label>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {loading ? <p className="muted" role="status">공유 자료를 불러오는 중…</p> : <>
      <div className="shared-prompt-grid">
        <section><h4>공유 항목</h4>
          <ul className="shared-prompt-list">{items.map((item) => <li key={item.id}><button type="button" aria-pressed={selectedId === item.id} onClick={() => { setSelectedId(item.id); setImpact(null) }}>{item.label}{defaultValue?.item_id === item.id ? ' · 기본값' : ''}</button></li>)}</ul>
          <button type="button" disabled={busy} onClick={() => { setSelectedId(''); setImpact(null) }}>새 항목</button>
        </section>
        <section className="shared-prompt-editor">
          <label>표시 이름<input aria-label="공유 항목 표시 이름" value={draft.label} disabled={busy} onChange={(event) => changeDraft('label', event.target.value)} /></label>
          <label>Positive<textarea aria-label="공유 항목 Positive" rows={3} value={draft.positive} disabled={busy} onChange={(event) => changeDraft('positive', event.target.value)} /></label>
          <label>Negative<textarea aria-label="공유 항목 Negative" rows={3} value={draft.negative} disabled={busy} onChange={(event) => changeDraft('negative', event.target.value)} /></label>
          <button className="primary-button" type="button" disabled={busy || !dirty || !draft.label.trim()} onClick={() => void saveItem()}>{busy ? '저장 중…' : selected ? '공유 항목 저장' : '공유 항목 추가'}</button>
          {selected && <div className="shared-prompt-actions">
            <label>변경<select value={action} disabled={busy} onChange={(event) => { setAction(event.target.value as 'move' | 'delete'); setImpact(null) }}><option value="move">다른 Level로 이동</option><option value="delete">비활성화</option></select></label>
            {action === 'move' && <label>이동할 Level<select value={targetLevel} disabled={busy} onChange={(event) => { setTargetLevel(Number(event.target.value)); setImpact(null) }}>{LEVELS.map((label, index) => <option key={index} value={index} disabled={index === level}>Level {index} · {label}</option>)}</select></label>}
            <button type="button" disabled={busy || dirty || (action === 'move' && targetLevel === level)} onClick={() => void preview()}>영향 확인</button>
          </div>}
        </section>
      </div>
      {selected && <section className="shared-prompt-configuration">
        <h4>기본값</h4>
        <p className="muted">명시 후보가 비어 있거나 유효 후보가 없을 때만 기본값을 적용합니다.</p>
        <div className="shared-prompt-controls"><select aria-label="지정 기본 항목" value={defaultChoice} disabled={busy} onChange={(event) => { setDefaultChoice(event.target.value); setDefaultDrafts((current) => ({ ...current, [`${level}:${kind}`]: event.target.value })) }}><option value="">기본값 없음</option>{items.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select><button type="button" disabled={busy || !defaultDirty} onClick={() => void saveDefault()}>기본값 저장</button></div>
        <h4>캐릭터별 명시 후보</h4>
        {items.length ? <ul className="shared-candidate-list">{items.map((item) => <li key={item.id}><label><input type="checkbox" checked={candidateIds.includes(item.id)} disabled={busy} onChange={(event) => setCandidateIds((ids) => { const next = event.target.checked ? [...ids, item.id] : ids.filter((id) => id !== item.id); setCandidateDrafts((current) => ({ ...current, [scopeKey]: next })); return next })} />{item.label}</label></li>)}</ul> : <p className="muted">선택할 공유 항목이 없습니다.</p>}
        <p className="muted">현재 결과: {candidate?.unregistered ? '미등록 (적용 가능한 항목 없음)' : candidate?.uses_default ? `기본값 사용 · ${candidate?.effective_items[0]?.label ?? ''}` : `${candidate?.effective_items.length ?? 0}개 명시 후보`}</p>
        <button type="button" disabled={busy || !candidateDirty} onClick={() => void saveCandidates()}>캐릭터 후보 저장</button>
      </section>}
      {impact && <section className="shared-prompt-impact" aria-label="변경 영향 확인">
        <h4>{action === 'delete' ? '비활성화 영향' : 'Level 이동 영향'}</h4>
        <p>후보 연결 {impact.candidate_changes.length}건을 제거하고, 기본값 참조 {impact.source_default.will_clear ? '1건을 해제' : '변경 없음'}합니다.</p>
        {impact.candidate_changes.length > 0 && <ul>{impact.candidate_changes.map((row) => <li key={row.candidate_set_id}>{row.cpu_name} · 명시 후보 제거 · {row.unregistered_after ? '변경 후 미등록' : row.fallback_item_id ? `기본값 ${items.find((item) => item.id === row.fallback_item_id)?.label ?? row.fallback_item_id} 적용` : `${row.after_effective_item_ids.length}개 후보 유지`}</li>)}</ul>}
        {impact.affected_cpus.length ? <ul>{impact.affected_cpus.map((cpu, index) => <li key={`${cpu.cpu_id}-${index}`}>{cpu.cpu_name} · {cpu.reason === 'default_reference' ? '기본값 사용' : '명시 후보'} · {cpu.unregistered_after ? '변경 후 미등록' : `기본값 ${cpu.fallback_item_id ?? ''} 적용`}</li>)}</ul> : <p>영향받는 캐릭터가 없습니다.</p>}
        <p className="muted">이동한 항목은 새 Level의 후보나 기본값에 자동 등록되지 않습니다.</p>
        <button type="button" disabled={busy} onClick={() => setImpact(null)}>취소</button><button type="button" disabled={busy} onClick={() => void confirm()}>확인 후 {action === 'delete' ? '비활성화' : '이동'}</button>
      </section>}
    </>}
  </section>
}

function message(error: unknown) { return error instanceof Error ? error.message : '요청에 실패했습니다.' }
