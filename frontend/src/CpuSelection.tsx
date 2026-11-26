import './opponent-selection.css'
import {LiveImage,ImageSettings} from './LiveImage'
import { useContext,useRef,useState } from 'react'
import { CharacterImage, Measurements } from './CharacterImage'
import type { CpuChoice } from './game/types'
import { defeatStageLabel } from './stages'

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
  const gallery = useRef<HTMLDialogElement>(null)
  const fullBody = viewed && <>
    <button type="button" className="gallery-open" aria-haspopup="dialog" onClick={()=>gallery.current?.showModal()}>전신 보기</button>
    <dialog ref={gallery} className="selection-gallery" aria-label={viewed.name+' 전신'}>
      <header><h2>{viewed.name}</h2><button type="button" onClick={()=>gallery.current?.close()}>닫기</button></header>
      <CharacterImage key={viewed.id} cpu={viewed.id} level={viewed.defeat_stage} kind="full_body" url={viewed.stage_images?.full_body} label="전신" className="gallery-body"/>
      {settings.available && <div className="gallery-cg">단계 CG <LiveImage cpu={viewed.id} level={viewed.defeat_stage} kind="cg" controlsOnly className="" label="단계 CG"/></div>}
    </dialog>
  </>
  if (!rosterMode) {

    return <section className="opponent-sheet" aria-labelledby="opponent-title">
      <header className="sheet-heading"><span className="east-mark" aria-label="동풍전">東</span><h2 id="opponent-title">대국 상대 선택</h2>
        <span className="seat-count" aria-live="polite">선택 <b>{selectedIds.length}</b> / 3</span></header>
      {viewed && <section className="dossier" aria-label="캐릭터 미리보기">
        <div className="scene-picture"><CharacterImage cpu={viewed.id} level={viewed.defeat_stage} kind="cg" url={viewed.stage_images?.cg} label="단계 CG" className="scene-art" imageOnly/></div>
        <div className="dossier-info"><h3>{viewed.name}</h3><p>{viewed.short_description}</p>
          <dl><div><dt>대국 성향</dt><dd>{styles[viewed.style] ?? viewed.style}</dd></div>
            <div><dt>의상 단계</dt><dd>{defeatStageLabel(viewed.defeat_stage)}</dd></div>
            {viewed.difficulty_preview && <div><dt>난이도</dt><dd>다음 대국 난이도 {viewed.difficulty_preview.level}/10</dd></div>}
            {Object.values(viewed.measurements_cm ?? {}).some(Boolean) && <div><dt>신체 정보</dt><dd><Measurements values={viewed.measurements_cm}/></dd></div>}
          </dl>
          {fullBody}
        </div>
      </section>}
      <div className="opponent-line">{cpus.map(cpu=>{
        const index=selectedIds.indexOf(cpu.id)
        const completed=cpu.defeat_stage>=3 && !allowCompleted
        const full=selectedIds.length===3 && index<0
        return <div key={cpu.id} className="candidate" data-viewed={viewed?.id===cpu.id} onMouseEnter={()=>setViewId(cpu.id)} onFocus={()=>setViewId(cpu.id)}
          tabIndex={completed || full || busy ? 0 : undefined}>
          <button type="button" className={'cpu-card'+(index>=0?' selected':'')} aria-pressed={index>=0} disabled={busy||completed||full}
            aria-label={cpu.name+(index>=0?' · 선택됨':completed?' · 완료 CPU':full?' · 3명 선택 완료':'')} onClick={()=>{setViewId(cpu.id);onToggle(cpu.id)}}>
            <CharacterImage cpu={cpu.id} level={cpu.defeat_stage} kind="profile" imageOnly url={cpu.stage_images?.profile} label={cpu.name+' 프로필'} className="candidate-face"/>
            {index>=0 && <span className="seat-check">✓</span>}
            <strong>{cpu.name}</strong>{completed && <small>완료 CPU</small>}
          </button>
          {settings.available && <span className="card-image-tools">face-tools</span>}
        </div>
      })}</div>
      {!cpus.length && <p>선택 가능한 CPU가 없습니다.</p>}
      {error && <p role="alert">{error}</p>}
      <footer className="draft-footer"><strong>선택한 상대</strong><ol aria-label="선택한 상대">{[0,1,2].map(i=><li key={i}>{cpus.find(cpu=>cpu.id===selectedIds[i])?.name ?? '미선택'}</li>)}</ol>
        <button className="primary-button start-button" type="button" disabled={busy||selectedIds.length!==3} onClick={onStart}>{busy?'세션 생성 중…':'동풍전 시작'}</button></footer>
      <div className="sheet-bottom">
        {onReset && <button type="button" disabled={busy} onClick={onReset}>진행 초기화</button>}
        {showLogout && <button type="button" onClick={onLogout}>로그아웃</button>}</div>
    </section>
  }
  return (
    <section className="selection-panel opponent-selection">
      <div className="panel-heading">
        <div>
          <p className="selection-count" aria-live="polite">{selectedIds.length}명 선택 · 최소 3명</p>
          <h2>상대 선택</h2>
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
          {fullBody}
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
              {selectedIndex>=0 && <span className="seat-check" aria-hidden="true">✓</span>}
              <span className="cpu-profile">
                <CharacterImage cpu={cpu.id} level={cpu.defeat_stage} kind="profile" imageOnly url={cpu.stage_images?.profile} label={cpu.name+' 프로필'} className="roster-face"/>
                <strong>{cpu.name}</strong>
              </span>
              <span className="cpu-stage">{defeatStageLabel(cpu.defeat_stage)}</span>
              {cpu.measurements_cm && Object.entries({ height: '키', bust: '가슴(B)', waist: '허리(W)', hips: '엉덩이(H)' }).filter(([key]) => cpu.measurements_cm?.[key as keyof typeof cpu.measurements_cm]).map(([key, label]) => <span key={key}>{label} {cpu.measurements_cm?.[key as keyof typeof cpu.measurements_cm]} cm</span>)}

            </button>{settings.available && <span className="card-image-tools">roster-tools</span>}</div>
          )
        })}
      </div>
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
