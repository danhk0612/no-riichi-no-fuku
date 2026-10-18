import { useEffect, useRef, useState } from 'react'
import {
  getCharacterContent, listLocalCharacters, listContentPacks, patchCharacterContent,
  rescanContentPacks, applyCharacterPack,
} from './api'
import type { CharacterContent, ContentPack } from './api'

const GROUPS = [
  ['appearance', '외모'],
  ['upper_underwear', '상의 속옷'],
  ['lower_underwear', '하의 속옷'],
] as const
const KINDS = [['profile', '프로필'], ['full_body', '전신'], ['cg', 'CG']] as const
const LEVELS = ['정상', '상의 겉옷 탈의', '속옷 세트', '전체 탈의']
const MEASUREMENTS = [['height', '키'], ['bust', '가슴(B)'], ['waist', '허리(W)'], ['hips', '엉덩이(H)']] as const
type Tab = 'prompts' | 'packs'

export function LocalContentPanel({ accessToken, onClose, onPackApplied }: { accessToken: string; onClose: () => void; onPackApplied: () => void }) {
  const [tab, setTab] = useState<Tab>('prompts')
  const [cpus, setCpus] = useState<{ id: number; slug: string; name: string }[]>([])
  const [cpuId, setCpuId] = useState<number | null>(null)
  const [content, setContent] = useState<CharacterContent | null>(null)
  const [dirty, setDirty] = useState<Record<string, string>>({})
  const [packs, setPacks] = useState<ContentPack[]>([])
  const [scanEntries, setScanEntries] = useState<{ source: string; identity: unknown; status: string; issues: string[] }[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selectedPack, setSelectedPack] = useState('')
  const mutationInFlight = useRef(false)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestId = useRef(0)
  const scanInFlight = useRef(false)
  const listingRequest = useRef(0)

  function updateListing(listing: { packs: ContentPack[]; scan_entries: typeof scanEntries }) {
    setPacks(listing.packs)
    setScanEntries(listing.scan_entries)
  }

  async function loadCharacter(id: number) {
    const request = ++requestId.current
    setCpuId(id); setSelectedPack(''); setContent(null); setDirty({}); setLoading(true); setError(null)
    try {
      const next = await getCharacterContent(accessToken, id)
      if (request === requestId.current) setContent(next)
    } catch (caught) {
      if (request === requestId.current) setError(message(caught))
    } finally {
      if (request === requestId.current) setLoading(false)
    }
  }

  async function scanPacks() {
    if (scanInFlight.current) return
    scanInFlight.current = true
    const request = ++listingRequest.current
    setScanning(true); setError(null)
    try {
      const result = await rescanContentPacks(accessToken)
      if (request === listingRequest.current) updateListing(result.registry)
    } catch (caught) {
      if (request === listingRequest.current) setError(message(caught))
      try { const listing = await listContentPacks(accessToken); if (request === listingRequest.current) updateListing(listing) } catch { /* retain last listing */ }
    } finally { scanInFlight.current = false; setScanning(false) }
  }

  useEffect(() => {
    let active = true
    void listLocalCharacters(accessToken).then((items) => {
      if (!active) return
      setCpus(items)
      setLoading(false)
    }).catch((caught) => { if (active) { setError(message(caught)); setLoading(false) } })
    const listingId = ++listingRequest.current
    void listContentPacks(accessToken).then((listing) => { if (active && listingId === listingRequest.current) updateListing(listing) }).catch((caught) => { if (active && listingId === listingRequest.current) setError(message(caught)) })
    return () => { active = false; requestId.current += 1; listingRequest.current += 1 }
  }, [accessToken])

  useEffect(() => { if (tab === 'packs') void scanPacks() }, [tab, accessToken])

  function editPrompt(group: string, field: 'positive' | 'negative', value: string) {
    const key = `p.${group}.${field}`
    setDirty((current) => ({ ...current, [key]: value }))
  }

  function editFraming(level: number, kind: string, field: 'positive' | 'negative', value: string) {
    const key = `f.${level}.${kind}.${field}`
    setDirty((current) => ({ ...current, [key]: value }))
  }

  function valueFor(key: string, original: string) { return Object.hasOwn(dirty, key) ? dirty[key] : original }

  async function save() {
    if (mutationInFlight.current || !content || cpuId === null || !Object.keys(dirty).length) return
    const prompts: Record<string, { positive?: string; negative?: string }> = {}
    const framing: { level: number; kind: 'profile' | 'full_body' | 'cg'; positive?: string; negative?: string }[] = []
    const measurements: Record<string, string | null> = {}
    const framingRows = new Map<string, typeof framing[number]>()
    for (const [key, value] of Object.entries(dirty)) {
      const parts = key.split('.')
      if (parts[0] === 'p') {
        const group = parts[1], field = parts[2] as 'positive' | 'negative'
        prompts[group] = { ...prompts[group], [field]: value }
      } else if (parts[0] === 'm') {
        measurements[parts[1]] = value === '' ? null : value
      } else {
        const level = Number(parts[1]), kind = parts[2] as 'profile' | 'full_body' | 'cg'
        const identity = `${level}.${kind}`
        const row = framingRows.get(identity) ?? { level, kind }
        row[parts[3] as 'positive' | 'negative'] = value
        framingRows.set(identity, row)
      }
    }
    framing.push(...framingRows.values())
    const selectedId = cpuId
    const request = requestId.current
    mutationInFlight.current = true
    setSaving(true); setError(null)
    try {
      const saved = await patchCharacterContent(accessToken, selectedId, {
        expected_revision: content.revision,
        ...(Object.keys(prompts).length ? { prompts } : {}),
        ...(framing.length ? { framing } : {}),
        ...(Object.keys(measurements).length ? { measurements_cm: measurements } : {}),
      })
      if (request === requestId.current && selectedId === cpuId) { setContent(saved); setDirty({}) }
    } catch (caught) {
      if (request === requestId.current && selectedId === cpuId) setError(message(caught))
    } finally { mutationInFlight.current = false; setSaving(false) }
  }

  const linkedPack = packs.find((pack) => pack.id === content?.pack?.id)
  const targetPack = content?.pack ? linkedPack : packs.find((pack) => pack.id === selectedPack)
  const targetRevision = targetPack?.registered_revision
  const canApply = !!targetPack && !!targetRevision && targetPack.kind === 'character'
    && targetPack.status !== 'conflict' && targetPack.issues.every((issue) => ['source_missing', 'default_voice_pack_unresolved'].includes(issue))
    && content?.pack_revision_id !== targetRevision.id

  async function applyPack() {
    if (mutationInFlight.current || !content || cpuId === null || !targetPack || !targetRevision || !canApply || Object.keys(dirty).length) return
    const request = requestId.current, selectedId = cpuId
    mutationInFlight.current = true; setSaving(true); setError(null)
    try {
      const next = await applyCharacterPack(accessToken, selectedId, {
        expected_revision: content.revision, pack_id: targetPack.id, registered_revision_id: targetRevision.id,
      })
      onPackApplied()
      if (request === requestId.current) { setContent(next); setSelectedPack('') }
    } catch (caught) { if (request === requestId.current) setError(message(caught)) }
    finally { mutationInFlight.current = false; setSaving(false) }
  }

  return <section className="sound-panel content-panel" aria-label="캐릭터 프롬프트와 팩 관리">
    <div className="sound-panel-heading"><div><p className="eyebrow">LOCAL CONTENT</p><h2>캐릭터 프롬프트·팩</h2></div><button className="text-button" onClick={onClose} type="button">닫기</button></div>
    <div className="content-tabs" role="tablist" aria-label="콘텐츠 관리">
      <button role="tab" aria-selected={tab === 'prompts'} onClick={() => setTab('prompts')} type="button">캐릭터 편집</button>
      <button role="tab" aria-selected={tab === 'packs'} onClick={() => setTab('packs')} type="button">팩 목록·진단</button>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {tab === 'prompts' && <section className="sound-card content-editor">
      <label>캐릭터<select aria-label="캐릭터" value={cpuId ?? ''} disabled={!cpus.length} onChange={(event) => { const id = Number(event.target.value); if (Number.isInteger(id)) void loadCharacter(id) }}>
        <option value="" disabled>캐릭터 선택</option>
        {cpus.map((cpu) => <option key={cpu.id} value={cpu.id}>{cpu.name} · {cpu.slug}</option>)}
      </select></label>
      {loading && <p className="muted" role="status">캐릭터 자료를 불러오는 중…</p>}
      {!loading && !cpus.length && <p className="muted">편집 가능한 캐릭터가 없습니다.</p>}
      {content && <>
        <section aria-label="캐릭터팩 연결">
          <h3>캐릭터팩 연결·갱신</h3>
          {content.pack ? <p>연결된 팩: {content.pack.pack_id} · 적용 revision {content.pack.applied_revision} · 등록 revision {linkedPack?.registered_revision?.revision ?? '확인 중'}</p>
            : <label>연결할 캐릭터팩<select aria-label="연결할 캐릭터팩" value={selectedPack} disabled={saving} onChange={(event) => setSelectedPack(event.target.value)}>
              <option value="">팩 선택</option>
              {packs.filter((pack) => pack.kind === 'character').map((pack) => <option key={pack.id} value={pack.id}>{pack.pack_id} · 등록 revision {pack.registered_revision?.revision ?? '없음'} · {statusLabel(pack.status)}</option>)}
            </select></label>}
          <p className="muted">직접 편집한 P/N은 빈 값도 유지하고 나머지만 팩 원본을 적용합니다. 재검색은 자동 적용하지 않습니다.</p>
          <button type="button" disabled={saving || scanning} onClick={() => void scanPacks()}>{scanning ? '연결할 팩 검색 중…' : '연결할 팩 다시 검색'}</button>
          <button type="button" disabled={saving || scanning || !canApply || !!Object.keys(dirty).length} onClick={() => void applyPack()}>{saving ? '처리 중…' : content.pack ? '같은 팩의 등록 revision 적용' : '선택한 팩 연결·적용'}</button>
          {!!Object.keys(dirty).length && <p className="muted">편집 내용을 먼저 저장한 뒤 팩을 적용해 주세요.</p>}
          {targetPack && !!targetPack.issues.length && <p className="diagnostic">팩 진단: {targetPack.issues.join(', ')}</p>}
        </section>
        <h3>신체 정보</h3>
        <p className="muted">단위 cm · 소수 첫째 자리까지 · 비워 두면 입력하지 않은 상태로 저장됩니다.</p>
        <div className="measurement-fields">
          {MEASUREMENTS.map(([key, label]) => {
            const dirtyKey = `m.${key}`
            const value = valueFor(dirtyKey, content.measurements_cm[key] ?? '')
            const source = content.pack_source?.metadata?.measurements_cm
            const sourceValue = source && typeof source === 'object' ? (source as Record<string, unknown>)[key] : undefined
            return <label key={key}>{label} {content.measurement_overrides[key] || Object.hasOwn(dirty, dirtyKey) ? <small>편집 기록</small> : null}
              <span><input aria-label={`${label} (cm)`} inputMode="decimal" value={value} disabled={saving} onChange={(event) => setDirty((current) => ({ ...current, [dirtyKey]: event.target.value }))} /><span>cm</span></span>
              {sourceValue !== undefined && <small className="muted">팩 원본: {sourceValue === null ? '미입력' : String(sourceValue)}{sourceValue === null ? '' : ' cm'}</small>}
            </label>
          })}
        </div>
        <p className="muted">변경한 항목만 저장합니다. 비워 둔 프롬프트도 명시 편집값으로 기록됩니다.</p>
        <h3>캐릭터 기본 프롬프트</h3>
        {GROUPS.map(([key, label]) => <PromptFields source={content.pack_source?.prompts[key]} disabled={saving} key={key} title={label} positive={valueFor(`p.${key}.positive`, content.prompts[key].positive)} negative={valueFor(`p.${key}.negative`, content.prompts[key].negative)} positiveEdited={content.prompts[key].overrides.positive || Object.hasOwn(dirty, `p.${key}.positive`)} negativeEdited={content.prompts[key].overrides.negative || Object.hasOwn(dirty, `p.${key}.negative`)} onPositive={(value) => editPrompt(key, 'positive', value)} onNegative={(value) => editPrompt(key, 'negative', value)} />)}
        <h3>단계별 이미지 구도 P/N</h3>
        {[0, 1, 2, 3].map((level) => <details className="framing-level" key={level} open={level === 0}>
          <summary>Level {level} · {LEVELS[level]}</summary>
          {KINDS.map(([kind, label]) => {
            const pair = content.levels[String(level)][kind]
            const posKey = `f.${level}.${kind}.positive`, negKey = `f.${level}.${kind}.negative`
            return <div key={kind}>
              {pair.media && <p className="muted">{label} 이미지 · 적용 팩 revision {content.pack?.applied_revision} · 보관 ID {pair.media.media_id}</p>}
              <PromptFields source={content.pack_source?.levels[String(level)].framing[kind]} disabled={saving} title={label} positive={valueFor(posKey, pair.positive)} negative={valueFor(negKey, pair.negative)} positiveEdited={pair.overrides.positive || Object.hasOwn(dirty, posKey)} negativeEdited={pair.overrides.negative || Object.hasOwn(dirty, negKey)} onPositive={(value) => editFraming(level, kind, 'positive', value)} onNegative={(value) => editFraming(level, kind, 'negative', value)} /></div>
          })}
        </details>)}
        <button className="primary-button" disabled={saving || !Object.keys(dirty).length} onClick={() => void save()} type="button">{saving ? '저장 중…' : `변경 필드 저장 (${Object.keys(dirty).length})`}</button>
      </>}
    </section>}
    {tab === 'packs' && <section className="sound-card">
      <div className="content-list-heading"><h3>등록된 팩</h3><button disabled={scanning} onClick={() => void scanPacks()} type="button">{scanning ? '재검색 중…' : '폴더 다시 검색'}</button></div>
      <p className="muted">설정 진입 때 자동 검색했습니다. 목록 조회 자체는 파일을 다시 읽지 않습니다.</p>
      {packs.length ? <ul className="sound-list pack-list">{packs.map((pack) => <li key={pack.id}>
        <span><strong>{pack.kind}</strong> · {pack.namespace ? `${pack.namespace}/` : ''}{pack.pack_id}<small> revision {pack.registered_revision?.revision ?? '없음'} · {statusLabel(pack.status)}</small>{pack.issues.length > 0 && <small className="diagnostic">진단: {pack.issues.join(', ')}</small>}</span>
      </li>)}</ul> : <p className="muted">등록된 팩이 없습니다.</p>}
      {!!scanEntries.length && <><h3>최근 검색 진단</h3><ul className="sound-list pack-list">{scanEntries.map((entry, index) => <li key={`${entry.source}-${index}`}><span>{entry.source}<small>{entry.status}{entry.issues.length ? ` · ${entry.issues.join(', ')}` : ''}</small></span></li>)}</ul></>}
    </section>}
  </section>
}

function PromptFields({ source, disabled, title, positive, negative, positiveEdited, negativeEdited, onPositive, onNegative }: {
  source?: { positive: string; negative: string }; disabled: boolean; title: string; positive: string; negative: string; positiveEdited: boolean; negativeEdited: boolean
  onPositive: (value: string) => void; onNegative: (value: string) => void
}) {
  return <fieldset className="prompt-fields" disabled={disabled}><legend>{title}</legend>
    <label>Positive {positiveEdited && <small>편집 기록</small>}<textarea rows={2} value={positive} onChange={(event) => onPositive(event.target.value)} /></label>
    <label>Negative {negativeEdited && <small>편집 기록</small>}<textarea rows={2} value={negative} onChange={(event) => onNegative(event.target.value)} /></label>
    {source && <details><summary>적용한 팩 원본 P/N</summary><p>Positive: {source.positive || '(빈 값)'}</p><p>Negative: {source.negative || '(빈 값)'}</p></details>}
  </fieldset>
}

function message(error: unknown) { return error instanceof Error ? error.message : '요청에 실패했습니다.' }
function statusLabel(status: ContentPack['status']) {
  return status === 'normal' ? '정상' : status === 'conflict' ? '충돌' : '미해결'
}
