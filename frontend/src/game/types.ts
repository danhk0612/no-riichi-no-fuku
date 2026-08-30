export type LegalAction = {
  type: number
  tile: number | null
  consume_tiles: number[]
  actor: number | null
}

export type HumanObservation = {
  player_id: number
  hands: number[][]
  discards: number[][]
  dora_indicators: number[]
  scores: number[]
  riichi_declared: boolean[]
  legal_actions: LegalAction[]
  honba: number
  riichi_sticks: number
  round_wind: number
  oya: number
}

export type HumanTurn = {
  observation: HumanObservation
  legal_actions: LegalAction[]
}

export type MatchResult = {
  scores: number[]
  ranks: number[]
}

export type PlayerSeat = {
  seat: number
  name: string
  isHuman: boolean
}

export type GameScreenState =
  | { status: 'waiting' }
  | { status: 'human_turn'; turn: HumanTurn; players: PlayerSeat[] }
  | { status: 'complete'; result: MatchResult; players: PlayerSeat[] }

export type GameClientMessage = {
  type: 'action'
  legal_action_index: number
}

export type GameServerMessage =
  | { type: 'human_turn'; turn: HumanTurn }
  | { type: 'match_complete'; result: MatchResult }
  | { type: 'error'; code: string; message: string }
