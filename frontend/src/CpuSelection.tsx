import type { CpuChoice } from './game/types'

type CpuSelectionProps = {
  cpus: CpuChoice[]
  selectedIds: number[]
  busy: boolean
  error: string | null
  onToggle: (cpuId: number) => void
  onStart: () => void
  onLogout: () => void
}

export function CpuSelection({
  cpus,
  selectedIds,
  busy,
  error,
  onToggle,
  onStart,
  onLogout,
}: CpuSelectionProps) {
  return (
    <section className="selection-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">CHOOSE OPPONENTS</p>
          <h2>CPU 3명 선택</h2>
          <p>선택 순서대로 좌석 1, 2, 3에 배치됩니다.</p>
        </div>
        <button className="text-button" onClick={onLogout} type="button">로그아웃</button>
      </div>
      <div className="cpu-grid">
        {cpus.map((cpu) => {
          const selectedIndex = selectedIds.indexOf(cpu.id)
          const unavailable = cpu.defeat_stage > 0
          const selectionFull = selectedIds.length === 3 && selectedIndex < 0
          return (
            <button
              className={`cpu-card${selectedIndex >= 0 ? ' selected' : ''}`}
              disabled={busy || unavailable || selectionFull}
              key={cpu.id}
              onClick={() => onToggle(cpu.id)}
              type="button"
            >
              <span className="cpu-order">
                {selectedIndex >= 0 ? `${selectedIndex + 1}번 좌석` : `Stage ${cpu.defeat_stage}`}
              </span>
              <strong>{cpu.name}</strong>
              <span>{cpu.style}</span>
              <p>{cpu.short_description}</p>
              {unavailable && <small>Tier {cpu.defeat_stage} 미구현</small>}
            </button>
          )
        })}
      </div>
      {cpus.length === 0 && <p className="empty-message">선택 가능한 CPU가 없습니다.</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button
        className="primary-button start-button"
        disabled={busy || selectedIds.length !== 3}
        onClick={onStart}
        type="button"
      >
        {busy ? '세션 생성 중…' : '동풍전 시작'}
      </button>
    </section>
  )
}
