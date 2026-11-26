import { useState } from 'react'
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
  const [viewId,setViewId]=useState<number|null>(null)
  const viewed=cpus.find(c=>c.id===viewId) ?? cpus.find(c=>c.id===selectedIds.at(-1)) ?? cpus[0]
  return (
    <section className="selection-panel opponent-selection">
      <div className="panel-heading">
        <div>
          <p className="selection-count" aria-live="polite">{selectedIds.length}명 선택 · {rosterMode ? '최소 3명' : '정원 3명'}</p>
          <h2>{rosterMode ? '이번 플레이 참가 CPU 확정' : '대국 상대 CPU 3명 선택'}</h2>
          <p>{rosterMode ? '확정한 명단은 초기화 전까지 바꿀 수 없습니다. 최소 3명을 선택하세요.' : '참가 명단 안에서 서로 다른 CPU 3명을 선택합니다. 3단계 CPU는 미완료가 3명 미만일 때 참가할 수 있습니다.'}</p>
        </div>
        <div className="selection-actions">
          {onReset && <button className="text-button" disabled={busy} onClick={onReset} type="button">진행 초기화</button>}
          {showLogout && <button className="text-button" onClick={onLogout} type="button">로그아웃</button>}
        </div>
      </div>
      {viewed && <section className="cpu-preview" aria-label="캐릭터 미리보기">
        <CharacterImage url={viewed.stage_images?.cg} label="단계 CG" className="preview-cg"/>
        <CharacterImage url={viewed.stage_images?.full_body} label="전신" className="preview-body"/>
        <div className="preview-copy"><h3>{viewed.name}</h3><p>Level {viewed.defeat_stage} · {defeatStageLabel(viewed.defeat_stage)}</p>
          <Measurements values={viewed.measurements_cm}/></div>
      </section>}
      <div className="cpu-grid">
        {cpus.map((cpu) => {
          const selectedIndex = selectedIds.indexOf(cpu.id)
          const unavailable = !rosterMode && cpu.defeat_stage >= 3 && !allowCompleted
          const selectionFull = !rosterMode && selectedIds.length === 3 && selectedIndex < 0
          return (
            <div key={cpu.id} onMouseEnter={()=>setViewId(cpu.id)} onFocus={()=>setViewId(cpu.id)} tabIndex={busy || unavailable || selectionFull ? 0 : undefined}>
            <button
              className={`cpu-card${selectedIndex >= 0 ? ' selected' : ''}`}
              aria-pressed={selectedIndex >= 0}
              disabled={busy || unavailable || selectionFull}
              onClick={() => {setViewId(cpu.id);onToggle(cpu.id)}}
              type="button"
            >
              <span className="cpu-order">
                {selectedIndex >= 0 ? (rosterMode ? '참가 명단' : `${selectedIndex + 1}번 좌석`) : unavailable ? '완료 CPU' : selectionFull ? '좌석 마감' : '선택 가능'}
              </span>
              <span className="cpu-profile">
                <CharacterImage url={cpu.stage_images?.profile} label={cpu.name+' 프로필'} className="roster-face"/>
                <strong>{cpu.name}</strong>
              </span>
              <span className="cpu-stage">{defeatStageLabel(cpu.defeat_stage)}</span>
              {!rosterMode && cpu.difficulty_preview && <span>다음 대국 난이도 {cpu.difficulty_preview.level}/10</span>}
              {cpu.measurements_cm && Object.entries({ height: '키', bust: '가슴(B)', waist: '허리(W)', hips: '엉덩이(H)' }).filter(([key]) => cpu.measurements_cm?.[key as keyof typeof cpu.measurements_cm]).map(([key, label]) => <span key={key}>{label} {cpu.measurements_cm?.[key as keyof typeof cpu.measurements_cm]} cm</span>)}
              <span>{cpu.style}</span>
              <p>{cpu.short_description}</p>
              {unavailable && <small>최종 완료 · 현재 대국 선택 불가</small>}
            </button></div>
          )
        })}
      </div>
      <div className="stage-guide" aria-label="패배 단계 안내">
        {DEFEAT_STAGE_LABELS.map((label, stage) => (
          <span key={label}>Stage {stage}: {label}</span>
        ))}
      </div>
      {cpus.length === 0 && <p className="empty-message">선택 가능한 CPU가 없습니다.</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button
        className="primary-button start-button"
        disabled={busy || (rosterMode ? selectedIds.length < 3 : selectedIds.length !== 3)}
        onClick={onStart}
        type="button"
      >
        {busy ? (rosterMode ? '명단 저장 중…' : '세션 생성 중…') : (rosterMode ? '참가 명단 확정' : '동풍전 시작')}
      </button>
    </section>
  )
}
