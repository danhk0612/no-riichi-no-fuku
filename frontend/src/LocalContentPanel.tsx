import { useEffect, useRef, useState } from 'react'
import {
  getCharacterContent, listLocalCharacters, listContentPacks, patchCharacterContent,
  rescanContentPacks,
} from './api'
import type { CharacterContent, ContentPack } from './api'

const GROUPS = [
  ['appearance', '외모'],
  ['upper_underwear', '상의 속옷'],
  ['lower_underwear', '하의 속옷'],
] as const
const KINDS = [['profile', '프로필'], ['full_body', '전신'], ['cg', 'CG']] as const
const LEVELS = ['정상', '상의 겉옷 탈의', '속옷 세트', '전체 탈의']
type Tab = 'prompts' | 'packs'

export function LocalContentPanel({ accessToken, onClose }: { accessToken: string; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>('prompts')
  const [cpus, setCpus] = useState<{ id: number; slug: string; name: string }[]>([])
  const [cpuId, setCpuId] = useState<number | null>(null)
  const [content, setContent] = useState<CharacterContent | null>(null)
  const [dirty, setDirty] = useState<Record<string, string>>({})
  const [packs, setPacks] = useState<ContentPack[]>([])
  const [scanEntries, setScanEntries] = useState<{ source: string; identity: unknown; status: string; issues: string[] }[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestId = useRef(0)

  function updateListing(listing: { packs: ContentPack[]; scan_entries: typeof scanEntries }) {
    setPacks(listing.packs)
    setScanEntries(listing.scan_entries)
  }

  async function loadCharacter(id: number) {
    const request = ++requestId.current
    setCpuId(id); setContent(null); setDirty({}); setLoading(true); setError(null)
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
    setScanning(true); setError(null)
    try {
      const result = await rescanContentPacks(accessToken)
      updateListing(result.registry)
    } catch (caught) {
      setError(message(caught))
      try { updateListing(await listContentPacks(accessToken)) } catch { /* retain last listing */ }
    } finally { setScanning(false) }
  }

  useEffect(() => {
    let active = true
    void listLocalCharacters(accessToken).then((items) => {
      if (!active) return
      setCpus(items)
      if (items.length) void loadCharacter(items[0].id)
      else setLoading(false)
    }).catch((caught) => { if (active) { setError(message(caught)); setLoading(false) } })
    return () => { active = false; requestId.current += 1 }
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
    if (!content || cpuId === null || !Object.keys(dirty).length) return
    const prompts: Record<string, { positive?: string; negative?: string }> = {}
    const framing: { level: number; kind: 'profile' | 'full_body' | 'cg'; positive?: string; negative?: string }[] = []
    const framingRows = new Map<string, typeof framing[number]>()
    for (const [key, value] of Object.entries(dirty)) {
      const parts = key.split('.')
      if (parts[0] === 'p') {
        const group = parts[1], field = parts[2] as 'positive' | 'negative'
        prompts[group] = { ...prompts[group], [field]: value }
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
    setSaving(true); setError(null)
    try {
      const saved = await patchCharacterContent(accessToken, selectedId, {
        expected_revision: content.revision,
        ...(Object.keys(prompts).length ? { prompts } : {}),
        ...(framing.length ? { framing } : {}),
      })
      if (request === requestId.current && selectedId === cpuId) { setContent(saved); setDirty({}) }
    } catch (caught) {
      if (request === requestId.current && selectedId === cpuId) setError(message(caught))
    } finally { setSaving(false) }
  }

  return <section className="sound-panel content-panel" aria-label="캐릭터 프롬프트와 팩 관리">
    <div className="sound-panel-heading"><div><p className="eyebrow">LOCAL CONTENT</p><h2>캐릭터 프롬프트·팩</h2></div><button className="text-button" onClick={onClose} type="button">닫기</button></div>
    <div className="content-tabs" role="tablist" aria-label="콘텐츠 관리">
      <button role="tab" aria-selected={tab === 'prompts'} onClick={() => setTab('prompts')} type="button">캐릭터 편집</button>
      <button role="tab" aria-selected={tab === 'packs'} onClick={() => setTab('packs')} type="button">팩 목록·진단</button>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {tab === 'prompts' && <section className="sound-card content-editor">
      <label>캐릭터<select value={cpuId ?? ''} disabled={!cpus.length} onChange={(event) => { const id = Number(event.target.value); if (Number.isInteger(id)) void loadCharacter(id) }}>
        {cpus.map((cpu) => <option key={cpu.id} value={cpu.id}>{cpu.name} · {cpu.slug}</option>)}
      </select></label>
      {loading && <p className="muted" role="status">캐릭터 자료를 불러오는 중…</p>}
      {!loading && !cpus.length && <p className="muted">편집 가능한 캐릭터가 없습니다.</p>}
      {content && <>
        <p className="muted">저장 revision {content.revision} · 표시된 항목만 저장합니다. 비워 둔 문자열도 명시 편집값으로 기록됩니다.</p>
        <h3>캐릭터 기본 프롬프트</h3>
        {GROUPS.map(([key, label]) => <PromptFields key={key} title={label} positive={valueFor(`p.${key}.positive`, content.prompts[key].positive)} negative={valueFor(`p.${key}.negative`, content.prompts[key].negative)} positiveEdited={content.prompts[key].overrides.positive || Object.hasOwn(dirty, `p.${key}.positive`)} negativeEdited={content.prompts[key].overrides.negative || Object.hasOwn(dirty, `p.${key}.negative`)} onPositive={(value) => editPrompt(key, 'positive', value)} onNegative={(value) => editPrompt(key, 'negative', value)} />)}
        <h3>단계별 이미지 구도 P/N</h3>
        {[0, 1, 2, 3].map((level) => <details className="framing-level" key={level} open={level === 0}>
          <summary>Level {level} · {LEVELS[level]}</summary>
          {KINDS.map(([kind, label]) => {
            const pair = content.levels[String(level)][kind]
            const posKey = `f.${level}.${kind}.positive`, negKey = `f.${level}.${kind}.negative`
            return <PromptFields key={kind} title={label} positive={valueFor(posKey, pair.positive)} negative={valueFor(negKey, pair.negative)} positiveEdited={pair.overrides.positive || Object.hasOwn(dirty, posKey)} negativeEdited={pair.overrides.negative || Object.hasOwn(dirty, negKey)} onPositive={(value) => editFraming(level, kind, 'positive', value)} onNegative={(value) => editFraming(level, kind, 'negative', value)} />
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

function PromptFields({ title, positive, negative, positiveEdited, negativeEdited, onPositive, onNegative }: {
  title: string; positive: string; negative: string; positiveEdited: boolean; negativeEdited: boolean
  onPositive: (value: string) => void; onNegative: (value: string) => void
}) {
  return <fieldset className="prompt-fields"><legend>{title}</legend>
    <label>Positive {positiveEdited && <small>편집 기록</small>}<textarea rows={2} value={positive} onChange={(event) => onPositive(event.target.value)} /></label>
    <label>Negative {negativeEdited && <small>편집 기록</small>}<textarea rows={2} value={negative} onChange={(event) => onNegative(event.target.value)} /></label>
  </fieldset>
}

function message(error: unknown) { return error instanceof Error ? error.message : '요청에 실패했습니다.' }
function statusLabel(status: ContentPack['status']) {
  return status === 'normal' ? '정상' : status === 'conflict' ? '충돌' : '미해결'
}
