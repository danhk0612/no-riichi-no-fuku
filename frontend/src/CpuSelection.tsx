import './opponent-selection.css'
import {LiveImage,ImageSettings} from './LiveImage'
import { useContext,useState } from 'react'
import { CharacterImage, Measurements } from './CharacterImage'
import type { CpuChoice } from './game/types'
import { DEFEAT_STAGE_LABELS, defeatStageLabel } from './stages'

type CpuSelectionProps = {
  cpus: CpuChoice[]
  selectedIds: number[]
  busy: boolean
  error: string | null
  onToggle: (cpuId: number) => void
  onStart: () => void
  onLogout: () => void
  onReset?: () => void
  showLogout?: boolean
  rosterMode?: boolean
  allowCompleted?: boolean
}

const styles:Record<string,string> = {balanced:'균형형', defensive:'수비형', aggressive:'공격형', 'menzen-riichi':'멘젠 리치형', 'fast-call':'속공 부로형', 'high-value':'고타점형'}

export function CpuSelection({
  cpus,
  selectedIds,
  busy,
  error,
  onToggle,
  onStart,
  onLogout,
  onReset,
  showLogout = true,
  rosterMode = false,
  allowCompleted = false,
}: CpuSelectionProps) {
  const settings=useContext(ImageSettings)
  const [viewId,setViewId]=useState<number|null>(null)
  const viewed=cpus.find(c=>c.id===viewId) ?? cpus.find(c=>c.id===selectedIds.at(-1)) ?? cpus[0]
  if (!rosterMode) {

    return <section className="opponent-sheet" aria-labelledby="opponent-title">
      <header className="sheet-heading"><span className="east-mark" aria-label="동풍전">東</span><h2 id="opponent-title">대국 상대 선택</h2><span className="sheet-hint">함께할 상대 3명을 고르세요</span>
        <span className="seat-count" aria-live="polite">선택 <b>{selectedIds.length}</b> / 3</span></header>
      {viewed && <section className="dossier" aria-label="캐릭터 미리보기">
        <div className="scene-picture"><CharacterImage cpu={viewed.id} level={viewed.defeat_stage} kind="cg" url={viewed.stage_images?.cg} label="단계 CG" className="scene-art" imageOnly/></div>
        <div className="dossier-info"><h3>{viewed.name}</h3><p>{viewed.short_description}</p>
          <dl><div><dt>대국 성향</dt><dd>{styles[viewed.style] ?? viewed.style}</dd></div>
            <div><dt>의상 단계</dt><dd>{defeatStageLabel(viewed.defeat_stage)}</dd></div>
            {viewed.difficulty_preview && <div><dt>난이도</dt><dd>다음 대국 난이도 {viewed.difficulty_preview.level}/10</dd></div>}
            {Object.values(viewed.measurements_cm ?? {}).some(Boolean) && <div><dt>신체 정보</dt><dd><Measurements values={viewed.measurements_cm}/></dd></div>}
          </dl>
          <details key={viewed.id} className="art-tools"><summary>전신 · 단계 안내 · 이미지 관리</summary>
            <p>미완료 상대가 3명 미만이면 완료한 상대도 선택할 수 있습니다.</p>
            <ul>{DEFEAT_STAGE_LABELS.map((label, stage) => <li key={label}>{stage}단계 · {label}</li>)}</ul>
            <CharacterImage cpu={viewed.id} level={viewed.defeat_stage} kind="full_body" url={viewed.stage_images?.full_body} label="전신" className="dossier-body"/>
            {settings.available && <div>단계 CG <LiveImage cpu={viewed.id} level={viewed.defeat_stage} kind="cg" controlsOnly className="" label="단계 CG"/></div>}
          </details>
        </div>
      </section>}
      <div className="opponent-line">{cpus.map(cpu=>{
        const index=selectedIds.indexOf(cpu.id)
        const completed=cpu.defeat_stage>=3 && !allowCompleted
        const full=selectedIds.length===3 && index<0
        return <div key={cpu.id} className="candidate" data-viewed={viewed?.id===cpu.id} onMouseEnter={()=>setViewId(cpu.id)} onFocus={()=>setViewId(cpu.id)}
          tabIndex={completed || full || busy ? 0 : undefined}>
          <button type="button" className={'cpu-card'+(index>=0?' selected':'')} aria-pressed={index>=0} disabled={busy||completed||full}
            aria-label={cpu.name+(index>=0?' · '+(index+1)+'번 좌석':completed?' · 완료 CPU':full?' · 좌석 마감':' · 선택 가능')} onClick={()=>{setViewId(cpu.id);onToggle(cpu.id)}}>
            <CharacterImage cpu={cpu.id} level={cpu.defeat_stage} kind="profile" imageOnly url={cpu.stage_images?.profile} label={cpu.name+' 프로필'} className="candidate-face"/>
            {index>=0 && <span className="seat-check">✓ {index+1}</span>}
            <strong>{cpu.name}</strong>{completed && <small>완료 CPU</small>}
          </button>
          {settings.available && <details className="face-tools"><summary aria-label={cpu.name+' 프로필 관리'}>···</summary>
            <LiveImage cpu={cpu.id} level={cpu.defeat_stage} kind="profile" controlsOnly label={cpu.name+' 프로필'} className=""/></details>}
        </div>
      })}</div>
      {!cpus.length && <p>선택 가능한 CPU가 없습니다.</p>}
      {error && <p role="alert">{error}</p>}
      <footer className="draft-footer"><strong>좌석 순서</strong><ol aria-label="선택한 상대 좌석 순서">{[0,1,2].map(i=><li key={i}><b>{i+1}</b>{cpus.find(cpu=>cpu.id===selectedIds[i])?.name ?? '빈 좌석'}</li>)}</ol>
        <button className="primary-button start-button" type="button" disabled={busy||selectedIds.length!==3} onClick={onStart}>{busy?'세션 생성 중…':'동풍전 시작'}</button></footer>
      <div className="sheet-bottom"><span>Tab 이동　·　Enter 선택</span>
        {onReset && <button type="button" disabled={busy} onClick={onReset}>진행 초기화</button>}
        {showLogout && <button type="button" onClick={onLogout}>로그아웃</button>}</div>
    </section>
  }
  return (
    <section className="selection-panel opponent-selection">
      <div className="panel-heading">
        <div>
          <p className="selection-count" aria-live="polite">{selectedIds.length}명 선택 · 최소 3명</p>
          <h2>이번 플레이 참가 CPU 확정</h2>
          <p>함께 플레이할 CPU를 3명 이상 선택하세요. 명단은 진행 초기화 전까지 유지됩니다. 다음 화면에서 첫 동풍전 상대 3명을 고릅니다.</p>
        </div>
        <div className="selection-actions">
          {onReset && <button className="text-button" disabled={busy} onClick={onReset} type="button">진행 초기화</button>}
          {showLogout && <button className="text-button" onClick={onLogout} type="button">로그아웃</button>}
        </div>
      </div>
      {viewed && <section className="cpu-preview" aria-label="캐릭터 미리보기">
        <div className="roster-scene">
          <CharacterImage cpu={viewed.id} level={viewed.defeat_stage} kind="cg" url={viewed.stage_images?.cg} label="단계 CG" className="preview-cg" imageOnly/>
        </div>
        <div className="preview-copy"><h3>{viewed.name}</h3><p>{viewed.short_description}</p>
          <dl><div><dt>대국 성향</dt><dd>{styles[viewed.style] ?? viewed.style}</dd></div>
            <div><dt>의상 단계</dt><dd>{defeatStageLabel(viewed.defeat_stage)}</dd></div></dl>
          <Measurements values={viewed.measurements_cm}/>
          <details key={viewed.id}><summary>전신 · 이미지 관리</summary>
            <CharacterImage cpu={viewed.id} level={viewed.defeat_stage} kind="full_body" url={viewed.stage_images?.full_body} label="전신" className="preview-body"/>
            {settings.available && <LiveImage cpu={viewed.id} level={viewed.defeat_stage} kind="cg" controlsOnly className="" label="단계 CG"/>}
          </details>
        </div>
      </section>}
      <div className="cpu-grid">
        {cpus.map((cpu) => {
          const selectedIndex = selectedIds.indexOf(cpu.id)
          return (
            <div key={cpu.id} onMouseEnter={()=>setViewId(cpu.id)} onFocus={()=>setViewId(cpu.id)} tabIndex={busy ? 0 : undefined}>
            <button
              className={`cpu-card${selectedIndex >= 0 ? ' selected' : ''}`}
              aria-pressed={selectedIndex >= 0}
              disabled={busy}
              onClick={() => {setViewId(cpu.id);onToggle(cpu.id)}}
              type="button"
            >
              <span className="cpu-order">
                {selectedIndex >= 0 ? '참가 명단' : '선택 가능'}
              </span>
              <span className="cpu-profile">
                <CharacterImage cpu={cpu.id} level={cpu.defeat_stage} kind="profile" imageOnly url={cpu.stage_images?.profile} label={cpu.name+' 프로필'} className="roster-face"/>
                <strong>{cpu.name}</strong>
              </span>
              <span className="cpu-stage">{defeatStageLabel(cpu.defeat_stage)}</span>
              {cpu.measurements_cm && Object.entries({ height: '키', bust: '가슴(B)', waist: '허리(W)', hips: '엉덩이(H)' }).filter(([key]) => cpu.measurements_cm?.[key as keyof typeof cpu.measurements_cm]).map(([key, label]) => <span key={key}>{label} {cpu.measurements_cm?.[key as keyof typeof cpu.measurements_cm]} cm</span>)}

            </button>{settings.available && <details className="roster-tools"><summary aria-label={cpu.name+' 프로필 관리'}>···</summary><LiveImage cpu={cpu.id} level={cpu.defeat_stage} kind="profile" controlsOnly label={cpu.name+' 프로필'} className="roster-face"/></details>}</div>
          )
        })}
      </div>
      <details className="roster-guide"><summary>패배 단계 안내</summary><div className="stage-guide" aria-label="패배 단계 안내">
        {DEFEAT_STAGE_LABELS.map((label, stage) => (
          <span key={label}>Stage {stage}: {label}</span>
        ))}
      </div>
      </details>
      {cpus.length === 0 && <p className="empty-message">선택 가능한 CPU가 없습니다.</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button
        className="primary-button start-button"
        disabled={busy || selectedIds.length < 3}
        onClick={onStart}
        type="button"
      >
        {busy ? '명단 저장 중…' : '참가 명단 확정'}
      </button>
    </section>
  )
}
