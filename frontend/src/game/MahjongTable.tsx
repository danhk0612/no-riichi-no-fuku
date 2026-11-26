import { SettlementScene } from './SettlementScene'
import { CharacterImage, Measurements } from '../CharacterImage'
import { HandCG } from './HandCG'
import type { SavedResultContent } from './types'
import type {
  DialogueEvent,
  GameScreenState,
  HumanObservation,
  LegalAction,
  MatchSettlement,
  PlayerSeat,
  ResultDeliveryEnvelope,
} from './types'
import { defeatStageLabel } from '../stages'
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
  onAcknowledgeResult?: (delivery: ResultDeliveryEnvelope) => void
  resultAssetObjectUrl?: string | null
  resultAssetLoadFailed?: boolean
  allowGameOverContinue?: boolean
}

function ResultDeliveryCard({ delivery, onAcknowledge, resultAssetObjectUrl, resultAssetLoadFailed }: {
  delivery: ResultDeliveryEnvelope
  onAcknowledge?: (delivery: ResultDeliveryEnvelope) => void
  resultAssetObjectUrl?: string | null
  resultAssetLoadFailed?: boolean
}) {
  const entry = delivery.head
  const payload = entry?.payload ?? {}
  const fact = payload.fact_snapshot as Record<string, any> | undefined
  const participantSnapshot = fact?.participants ?? payload.participants
  const participants = Array.isArray(participantSnapshot) ? participantSnapshot as Record<string, any>[] : []
  const nameFor = (seat: unknown) => participants.find((player) => player.seat === seat)?.name ?? `좌석 ${Number(seat) + 1}`
  const winners = Array.isArray(fact?.winners) ? fact.winners as Record<string, any>[] : []
  const winnerOffset = payload.displayed_hora_log_offset
  const winner = winners.find((item) => item.hora_log_offset === winnerOffset)
  const start = fact?.start as Record<string, any> | undefined
  const settlementPayload = payload.kind === 'settlement'
  const scores = Array.isArray(payload.scores) ? payload.scores as number[] : []
  const ranks = Array.isArray(payload.ranks) ? payload.ranks as number[] : []
  const resultRows = scores.map((score, seat) => ({ seat, score, rank: ranks[seat] })).sort((a, b) => a.rank - b.rank)
  const presentation = payload.presentation as Record<string, any> | null | undefined
  const dialogues = Array.isArray(presentation?.result_dialogues) ? presentation.result_dialogues as Record<string, any>[] : []
  const content = payload.content as SavedResultContent | undefined
  const resultAsset = content ? (content.scene?.media ? {defeat_stage: content.scene.stage} : null) : presentation?.result_asset as { id?: number; defeat_stage?: number } | null | undefined

  const transition = settlementPayload && content?.scene?.transition
  const defeatLine = transition && content?.dialogues.find(line=>line.cpu_id===content.scene?.cpu_id && line.slot==='defeat_stage_'+content.scene.stage)

  if (delivery.route === 'settlement_wait') {
    return <section className="result-delivery-card" data-result-kind="settlement-wait" role="status"><h2>정산 결과 저장 중</h2><p>저장된 국 결과는 유지됩니다. 연결을 다시 확인하면 정산 결과로 복구합니다.</p></section>
  }
  if (!entry) return null

  return (
    <section className={`${settlementPayload ? 'match-result ' : ''}result-delivery-card`} data-result-kind={settlementPayload ? 'settlement' : 'hand'} data-multiple-winners={winners.length>1 || undefined} data-ordinal={entry?.ordinal} data-event-id={entry?.event_id} aria-live="polite" aria-label={settlementPayload ? '최종 정산 결과' : '국 결과'}>
      <h2>{settlementPayload ? '동풍전 정산' : `국 결과 · ${String(start?.bakaze ?? '')}${String(start?.kyoku ?? 0)}국`}</h2>
      {settlementPayload ? (
        <>
          <ol>{resultRows.map((row) => <li key={row.seat}><strong>{row.rank}위 · {nameFor(row.seat)}</strong><span>{row.score.toLocaleString()}점</span></li>)}</ol>
          {transition && content?.scene && <SettlementScene key={delivery.generation+':'+delivery.session_id+':'+entry.event_id}
            transition={transition} stage={content.scene.stage} text={defeatLine ? defeatLine.text : null}
            url={resultAssetObjectUrl} hasCG={!!resultAsset} failed={!!resultAssetLoadFailed}/>}
          {!transition && resultAsset && resultAssetObjectUrl && <figure className="result-asset"><img src={resultAssetObjectUrl} alt={`단계 ${resultAsset.defeat_stage ?? ''} 결과 CG`} /><figcaption>단계 {resultAsset.defeat_stage ?? ''} 결과 CG</figcaption></figure>}
          {!transition && resultAsset && !resultAssetObjectUrl && <p className="result-asset-status" role="status">{resultAssetLoadFailed ? 'CG를 불러오지 못했습니다.' : 'CG를 불러오는 중입니다.'}</p>}
          {!transition && !resultAsset && <p className="result-asset-status">등록된 결과 CG가 없습니다.</p>}
          {!content && dialogues.map((dialogue, index) => <blockquote className="result-dialogue" key={`${dialogue.cpu_character_id}-${dialogue.event_key}-${index}`}><p>{String(dialogue.text ?? '')}</p></blockquote>)}
          <p className="settlement-summary">저장된 정산 결과</p>
        </>
      ) : (
        <>
          <p className="settlement-summary">{String(start?.bakaze ?? '')}{String(start?.kyoku ?? 0)}국 · 본장 {String(start?.honba ?? 0)} · 리치봉 {String(start?.kyotaku ?? 0)}</p>
          {winners.length > 0 ? (
            <section aria-label="화료자별 결과">
              {winners.map(w => <div className="settlement-summary" key={w.hora_log_offset}>
                <strong>{nameFor(w.actor)} · {w.win_kind === 'tsumo' ? '쯔모' : `론 · ${nameFor(w.target)}`}</strong>
                <p>{({ 1: '만관 미만', 2: '만관·하네만', 3: '배만 이상' } as Record<number, string>)[Number(w.score?.band)] ?? '점수 미분류'} · {w.score?.han ?? 0}판 {w.score?.fu ?? 0}부</p>
                {w.win_kind==='ron' && typeof w.score?.ron_agari==='number' && <p>론 점수 {w.score.ron_agari.toLocaleString()}점</p>}
                <ol className="result-deltas" aria-label={nameFor(w.actor)+' 화료 점수 이동'}>{(w.deltas ?? []).map((delta:number,seat:number)=><li key={seat}>{nameFor(seat)} · {delta>0?'+':''}{delta.toLocaleString()}점</li>)}</ol>
              </div>)}
              {winners.length>1 && winner && <p aria-label="현재 배경 차례">현재 배경 차례: {nameFor(winner.actor)}</p>}
            </section>
          ) : <p className="settlement-summary">유국 결과</p>}
          {Array.isArray(fact?.draws) && fact.draws.length > 0 && <p className="settlement-summary">유국 정보: {fact.draws.map((draw: Record<string, any>) => draw.reason ?? '유국').join(' · ')}</p>}
          {!winners.length && <ol className="result-deltas">{(fact?.draws?.[0]?.deltas ?? []).map((delta: number, seat: number) => <li key={seat}>{nameFor(seat)} · {delta > 0 ? '+' : ''}{delta.toLocaleString()}점</li>)}</ol>}
        </>
      )}
      {content?.dialogues.filter(line => line.text && line!==defeatLine).map(line => <blockquote className="result-dialogue" key={line.cpu_id + ':' + line.slot}>{line.text}</blockquote>)}
      {!settlementPayload && !!content?.scene?.generation_input && window.nrnfDesktop?.isDesktop && <HandCG path={`/api/local/play/sessions/${delivery.session_id}/results/${entry.event_id}/cg`} generation={delivery.generation}/>}
      {!settlementPayload && content?.scene && !content.scene.generation_input && !content.scene.media && <p className="result-asset-status">{content.scene.missing_candidates?.length
        ? '화료 CG 생략 · 미등록 후보: '+content.scene.missing_candidates.map(k=>({clothing_state:'복장 상태',situation:'화료 상황',pose:'포즈'})[k]).join(', ')
        : '화료 CG가 등록되지 않았습니다.'}</p>}
      {onAcknowledge && <button className="primary-button" onClick={() => onAcknowledge(delivery)} type="button">{settlementPayload ? '정산 확인' : '확인하고 다음 결과 보기'}</button>}
    </section>
  )
}

function Tile({ tileId, disabled = false, onClick }: {
  tileId: number
  disabled?: boolean
  onClick?: () => void
}) {
  const tile = tileIdToDisplay(tileId)
  const className = `tile tile-${tile.suit}${tile.red ? ' tile-red' : ''}`
  const face = <><span className="tile-value">{tile.suit === 'honor' ? tile.label : tile.label.slice(0, -1)}</span>{tile.suit !== 'honor' && <small className="tile-suit">{tile.label.slice(-1)}</small>}{tile.red && <i className="aka-mark" aria-hidden="true" />}</>
  const name = (tile.red ? '적도라 ' : '') + tile.label
  if (onClick) {
    return (
      <button
        className={className}
        aria-label={name}
        disabled={disabled}
        onClick={onClick}
        type="button"
      >
        {face}
      </button>
    )
  }
  return <span className={className} title={name}>{face}</span>
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
  dialogue,
}: {
  player: PlayerSeat
  observation: HumanObservation
  dialogue?: DialogueEvent
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
      {!player.isHuman && player.detail && <details className="seat-details">
        <summary aria-label={player.name+' 캐릭터 정보'}><CharacterImage url={player.detail.images.profile} label={player.name+' 프로필'} className="seat-face"/></summary>
        <div className="seat-bio"><CharacterImage url={player.detail.images.full_body} label={player.name+' 전신'} className="seat-body"/>
          <p>Level {player.detail.stage} · {player.detail.style}</p><Measurements values={player.detail.measurements_cm}/>
          <p>{player.detail.description}</p><dl aria-label="마작 스펙">
          {Object.entries({aggression:'공격 성향',defense:'수비 성향',call_preference:'부로 선호',riichi_preference:'리치 선호',hand_value_preference:'타점 선호',speed_preference:'속도 선호'}).map(([k,label])=>
            player.detail?.stats[k]!=null && <div key={k}><dt>{label}</dt><dd>{player.detail.stats[k]}</dd></div>)}</dl></div>
      </details>}
      <p className="score">{observation.scores[seat].toLocaleString()}점</p>
      {observation.riichi_declared[seat] && <p className="riichi">리치</p>}
      {dialogue && !player.isHuman && (
        <div className="speech-bubble">
          <p>{dialogue.text}</p>
        </div>
      )}
      {observation.melds[seat].length > 0 && (
        <div className="melds" aria-label={`${player.name} 공개 조합`}>
          {observation.melds[seat].map((meld, index) => (
            <div className="meld" key={index} aria-label={`조합 ${index + 1}`}>
              <small>{meld.opened ? '부로' : '암깡'}</small>
              <TileRow tiles={meld.tiles} emptyText="" />
            </div>
          ))}
        </div>
      )}
      <div className="discards" aria-label={`${player.name} 버림패`} title="각 좌석에서 마지막으로 버린 패는 아래쪽 금색 선으로 표시합니다.">
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
      <header className="hand-heading"><h2>내 손패</h2><p role="status">{disabled ? '행동 처리 중' : nonDiscardActions.length ? '가능한 행동을 선택하세요.' : '버릴 패를 선택하세요.'}</p></header>
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
        {nonDiscardActions.map(({ action, index }) => (
          <button
            disabled={disabled}
            data-action={action.type}
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

  // 각 좌석별 최신 대사 찾기 (좌석별로 가장 최근 대사만)
  const dialogueBySeat = new Map<number, DialogueEvent>()
  for (const dialogue of state.recentDialogues) {
    dialogueBySeat.set(dialogue.seat, dialogue)
  }

  return (
    <>
      <section className="mahjong-table" aria-label="마작 테이블">
        {players.map((player) => (
          <SeatPanel
            key={player.seat}
            player={player}
            observation={observation}
            dialogue={dialogueBySeat.get(player.seat)}
          />
        ))}
        <div className="round-status">
          <strong>{roundWindLabel(observation.round_wind)}{observation.kyoku_index % 4 + 1}국</strong>
          <div className="round-counters"><span>본장 {observation.honba}</span><span>리치봉 {observation.riichi_sticks}</span></div>
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
  allowGameOverContinue,
}: {
  state: Extract<GameScreenState, { status: 'complete' }>
  onNextGame?: () => void
  allowGameOverContinue: boolean
}) {
  const playersBySeat = new Map(state.players.map((player) => [player.seat, player]))
  const rows = state.result.ranks
    .map((rank, seat) => ({
      rank,
      score: state.result.scores[seat],
      name: playersBySeat.get(seat)?.name ?? `좌석 ${seat + 1}`,
    }))
    .sort((left, right) => left.rank - right.rank)
  const localResult = 'progression_version' in state.settlement ? state.settlement : null
  const localSettlement = localResult !== null
  const legacySettlement = localSettlement ? null : state.settlement as MatchSettlement
  const defeatedSeat = localResult ? state.result.ranks.indexOf(4) : legacySettlement?.last_place_seat
  const defeatedCpuName = defeatedSeat !== undefined && defeatedSeat !== 0
    ? playersBySeat.get(defeatedSeat)?.name ?? 'CPU'
    : null

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
        {localResult
          ? (localResult.mode === 'omake'
            ? '오마케 대국 · 진행 이벤트와 캐릭터 대사는 발생하지 않습니다.'
            : localResult.cpu_character_id === null
              ? '플레이어 진행도는 변경되지 않았습니다.'
              : localResult.stage_changed
                ? `${defeatedCpuName} · ${defeatStageLabel(localResult.defeat_stage ?? 0)}`
                : `${defeatedCpuName} · 완료 CPU · 진행도 변화 없음`)
          : legacySettlement?.last_place_seat === 0
            ? (allowGameOverContinue ? '플레이어 진행도 변화 없음' : `플레이어 HP ${legacySettlement.current_hp}`)
            : `${defeatedCpuName} · ${defeatStageLabel(legacySettlement?.defeat_stage ?? 0)}`}
      </p>
      {(state.resultDialogues?.length ? state.resultDialogues : (state.resultDialogue ? [state.resultDialogue] : [])).map((dialogue, index) => (
        <blockquote className="result-dialogue" key={`${dialogue.cpu_character_id}-${dialogue.event_key}-${index}`}>
          <strong>{defeatedCpuName ?? 'CPU 결과 대사'}</strong>
          <p>{dialogue.text}</p>
        </blockquote>
      ))}
      {legacySettlement && legacySettlement.cpu_character_id !== null && (
        <figure className="result-asset">
          {state.resultAsset && state.resultAssetObjectUrl
            ? (
                <img
                  alt={`${defeatedCpuName} ${defeatStageLabel(state.resultAsset.defeat_stage)} 결과 CG`}
                  src={state.resultAssetObjectUrl}
                />
              )
            : state.resultAsset
              ? (
                  <p className="result-asset-placeholder">
                    {state.resultAssetLoadFailed
                      ? '결과 CG를 불러오지 못했습니다.'
                      : '결과 CG를 불러오는 중입니다.'}
                  </p>
                )
              : (
                  <p className="result-asset-placeholder">
                    이 단계의 결과 CG는 아직 등록되지 않았습니다.
                  </p>
                )}
          <figcaption>
            {defeatStageLabel(state.settlement.defeat_stage ?? 0)} 결과 CG 슬롯
          </figcaption>
        </figure>
      )}
      {legacySettlement?.game_over && !allowGameOverContinue && (
        <p className="settlement-summary" role="status">게임 오버 · HP가 모두 소진되었습니다.</p>
      )}
      {onNextGame && (localSettlement || !legacySettlement?.game_over || allowGameOverContinue) && (
        <button className="primary-button" onClick={onNextGame} type="button">
          {localSettlement && state.endingEventId ? '엔딩 화면 보기' : '다음 대국 선택'}
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
  onAcknowledgeResult,
  resultAssetObjectUrl,
  resultAssetLoadFailed,
  allowGameOverContinue = false,
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
    return <CompletedTable state={state} onNextGame={onNextGame} allowGameOverContinue={allowGameOverContinue} />
  }
  if (state.status === 'result_delivery' || state.status === 'settlement_wait') {
    return <ResultDeliveryCard key={`${state.delivery.generation}:${state.delivery.session_id}:${state.delivery.head?.event_id ?? 'empty'}`} delivery={state.delivery} onAcknowledge={onAcknowledgeResult} resultAssetObjectUrl={resultAssetObjectUrl} resultAssetLoadFailed={resultAssetLoadFailed} />
  }
  if (state.status === 'ending') {
    return (
      <section className="match-result ending-panel" aria-label="엔딩">
        <p className="eyebrow">ENDING</p>
        <h2>모든 참가 CPU 완료</h2>
        <p>{state.payload?.dialogue_text ?? '엔딩 대사가 등록되지 않았습니다.'}</p>
        <p className="result-asset-placeholder">엔딩 CG와 음악은 아직 등록되지 않았습니다.</p>
      </section>
    )
  }
  return (
    <ActiveTable
      state={state}
      onAction={onAction}
      actionsDisabled={actionsDisabled}
    />
  )
}
