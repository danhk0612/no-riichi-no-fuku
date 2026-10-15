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
  return (
    <section className="selection-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">CHOOSE OPPONENTS</p>
          <h2>{rosterMode ? '이번 플레이 참가 CPU 확정' : '대국 상대 CPU 3명 선택'}</h2>
          <p>{rosterMode ? '확정한 명단은 초기화 전까지 바꿀 수 없습니다. 최소 3명을 선택하세요.' : '참가 명단 안에서 서로 다른 CPU 3명을 선택합니다. 3단계 CPU는 미완료가 3명 미만일 때 참가할 수 있습니다.'}</p>
        </div>
        <div className="selection-actions">
          {onReset && <button className="text-button" disabled={busy} onClick={onReset} type="button">진행 초기화</button>}
          {showLogout && <button className="text-button" onClick={onLogout} type="button">로그아웃</button>}
        </div>
      </div>
      <div className="cpu-grid">
        {cpus.map((cpu) => {
          const selectedIndex = selectedIds.indexOf(cpu.id)
          const unavailable = !rosterMode && cpu.defeat_stage >= 3 && !allowCompleted
          const selectionFull = !rosterMode && selectedIds.length === 3 && selectedIndex < 0
          return (
            <button
              className={`cpu-card${selectedIndex >= 0 ? ' selected' : ''}`}
              disabled={busy || unavailable || selectionFull}
              key={cpu.id}
              onClick={() => onToggle(cpu.id)}
              type="button"
            >
              <span className="cpu-order">
                {selectedIndex >= 0 ? (rosterMode ? '참가 명단' : `${selectedIndex + 1}번 좌석`) : '선택 가능'}
              </span>
              <span className="cpu-profile">
                {!cpu.profile_image_key && (
                  <span
                    aria-label="프로필 이미지 없음"
                    className="profile-placeholder"
                  >
                    {cpu.name.slice(0, 1)}
                  </span>
                )}
                <strong>{cpu.name}</strong>
              </span>
              <span className="cpu-stage">{defeatStageLabel(cpu.defeat_stage)}</span>
              <span>{cpu.style}</span>
              <p>{cpu.short_description}</p>
              {unavailable && <small>최종 완료 · 현재 대국 선택 불가</small>}
            </button>
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
