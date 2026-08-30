import type {
  GameScreenState,
  HumanObservation,
  LegalAction,
  PlayerSeat,
} from './types'
import { roundWindLabel, seatWindLabel, tileIdToDisplay } from './tiles'

const ACTION_LABELS: Record<number, string> = {
  0: '버리기',
  1: '치',
  2: '퐁',
  3: '대명깡',
  4: '론',
  5: '리치',
  6: '쯔모',
  7: '패스',
  8: '암깡',
  9: '가깡',
  10: '구종구패',
  11: '키타',
}

type MahjongTableProps = {
  state: GameScreenState
  onAction: (legalActionIndex: number) => void
  actionsDisabled?: boolean
  onNextGame?: () => void
}

function Tile({ tileId, disabled = false, onClick }: {
  tileId: number
  disabled?: boolean
  onClick?: () => void
}) {
  const tile = tileIdToDisplay(tileId)
  const className = `tile tile-${tile.suit}${tile.red ? ' tile-red' : ''}`
  if (onClick) {
    return (
      <button
        className={className}
        disabled={disabled}
        onClick={onClick}
        type="button"
      >
        {tile.label}
      </button>
    )
  }
  return <span className={className}>{tile.label}</span>
}

function TileRow({ tiles, emptyText }: { tiles: number[]; emptyText: string }) {
  if (tiles.length === 0) {
    return <span className="empty-tiles">{emptyText}</span>
  }
  return (
    <div className="tile-row">
      {tiles.map((tileId) => <Tile key={tileId} tileId={tileId} />)}
    </div>
  )
}

function SeatPanel({
  player,
  observation,
}: {
  player: PlayerSeat
  observation: HumanObservation
}) {
  const seat = player.seat
  return (
    <section className={`seat seat-${seat}`} aria-label={`${player.name} 좌석`}>
      <header>
        <span className="wind">
          {seatWindLabel(seat, observation.oya)}
        </span>
        <strong>{player.name}</strong>
        {player.isHuman && <span className="human-badge">PLAYER</span>}
      </header>
      <p className="score">{observation.scores[seat].toLocaleString()}점</p>
      {observation.riichi_declared[seat] && <p className="riichi">리치</p>}
      <div className="discards">
        <TileRow tiles={observation.discards[seat]} emptyText="버림패 없음" />
      </div>
    </section>
  )
}

function actionDescription(action: LegalAction): string {
  const tiles = [action.tile, ...action.consume_tiles]
    .filter((tile): tile is number => tile !== null)
    .map((tile) => tileIdToDisplay(tile).label)
    .join(' ')
  return tiles
    ? `${ACTION_LABELS[action.type] ?? '행동'} · ${tiles}`
    : (ACTION_LABELS[action.type] ?? `행동 ${action.type}`)
}

function HumanHand({
  observation,
  legalActions,
  onAction,
  disabled,
}: {
  observation: HumanObservation
  legalActions: LegalAction[]
  onAction: (index: number) => void
  disabled: boolean
}) {
  const discardIndexByTile = new Map<number, number>()
  legalActions.forEach((action, index) => {
    if (action.type === 0 && action.tile !== null) {
      discardIndexByTile.set(action.tile, index)
    }
  })
  const nonDiscardActions = legalActions
    .map((action, index) => ({ action, index }))
    .filter(({ action }) => action.type !== 0)

  return (
    <section className="human-controls" aria-label="플레이어 행동">
      <h2>내 손패</h2>
      <div className="hand">
        {observation.hands[0].map((tileId) => {
          const actionIndex = discardIndexByTile.get(tileId)
          return (
            <Tile
              key={tileId}
              tileId={tileId}
              disabled={disabled || actionIndex === undefined}
              onClick={
                actionIndex === undefined ? undefined : () => onAction(actionIndex)
              }
            />
          )
        })}
      </div>
      <div className="action-bar">
        {nonDiscardActions.length === 0 && <p>버릴 패를 선택하세요.</p>}
        {nonDiscardActions.map(({ action, index }) => (
          <button
            disabled={disabled}
            key={index}
            onClick={() => onAction(index)}
            type="button"
          >
            {actionDescription(action)}
          </button>
        ))}
      </div>
    </section>
  )
}

function ActiveTable({
  state,
  onAction,
  actionsDisabled,
}: {
  state: Extract<GameScreenState, { status: 'human_turn' }>
  onAction: (index: number) => void
  actionsDisabled: boolean
}) {
  const { observation } = state.turn
  const playersBySeat = new Map(state.players.map((player) => [player.seat, player]))
  const players = [0, 1, 2, 3].map((seat) => playersBySeat.get(seat) ?? ({
    seat,
    name: `좌석 ${seat + 1}`,
    isHuman: seat === 0,
  }))

  return (
    <>
      <section className="mahjong-table" aria-label="마작 테이블">
        {players.map((player) => (
          <SeatPanel key={player.seat} player={player} observation={observation} />
        ))}
        <div className="round-status">
          <strong>{roundWindLabel(observation.round_wind)}풍전</strong>
          <span>본장 {observation.honba}</span>
          <span>리치봉 {observation.riichi_sticks}</span>
          <span>도라</span>
          <TileRow tiles={observation.dora_indicators} emptyText="없음" />
        </div>
      </section>
      <HumanHand
        observation={observation}
        legalActions={state.turn.legal_actions}
        onAction={onAction}
        disabled={actionsDisabled}
      />
    </>
  )
}

function CompletedTable({
  state,
  onNextGame,
}: {
  state: Extract<GameScreenState, { status: 'complete' }>
  onNextGame?: () => void
}) {
  const playersBySeat = new Map(state.players.map((player) => [player.seat, player]))
  const rows = state.result.ranks
    .map((rank, seat) => ({
      rank,
      score: state.result.scores[seat],
      name: playersBySeat.get(seat)?.name ?? `좌석 ${seat + 1}`,
    }))
    .sort((left, right) => left.rank - right.rank)

  return (
    <section className="match-result">
      <h2>동풍전 종료</h2>
      <ol>
        {rows.map((row) => (
          <li key={row.rank}>
            <strong>{row.rank}위 · {row.name}</strong>
            <span>{row.score.toLocaleString()}점</span>
          </li>
        ))}
      </ol>
      <p className="settlement-summary">
        {state.settlement.last_place_seat === 0
          ? `플레이어 HP ${state.settlement.current_hp}`
          : `CPU 진행 단계 ${state.settlement.defeat_stage}`}
      </p>
      {onNextGame && (
        <button className="primary-button" onClick={onNextGame} type="button">
          다음 대국 선택
        </button>
      )}
    </section>
  )
}

export function MahjongTable({
  state,
  onAction,
  actionsDisabled = false,
  onNextGame,
}: MahjongTableProps) {
  if (state.status === 'waiting') {
    return (
      <section className="waiting-panel">
        <p className="eyebrow">GAME SESSION</p>
        <h2>대국 연결 전</h2>
        <p>CPU를 선택하고 서버 세션에 연결하면 마작 테이블이 표시됩니다.</p>
      </section>
    )
  }
  if (state.status === 'complete') {
    return <CompletedTable state={state} onNextGame={onNextGame} />
  }
  return (
    <ActiveTable
      state={state}
      onAction={onAction}
      actionsDisabled={actionsDisabled}
    />
  )
}
