export type LegalAction = {
  type: number
  tile: number | null
  consume_tiles: number[]
  actor: number | null
}

export type Meld = {
  meld_type: number
  tiles: number[]
  called_tile: number
  from_who: number
  opened: boolean
}

export type HumanObservation = {
  player_id: number
  hands: number[][]
  melds: Meld[][]
  discards: number[][]
  dora_indicators: number[]
  scores: number[]
  riichi_declared: boolean[]
  legal_actions: LegalAction[]
  honba: number
  riichi_sticks: number
  round_wind: number
  kyoku_index: number
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

export type CpuDifficulty = { seat: number; cpu_character_id: number; level: number; profile_version: string; reason: string }

export type CpuChoice = {
  id: number
  slug: string
  name: string
  age_adult: boolean
  style: string
  short_description: string
  long_description: string | null
  profile_image_key: string | null
  defeat_stage: number
  content_revision?: number
  measurements_cm?: { height: string | null; bust: string | null; waist: string | null; hips: string | null }
  difficulty_preview?: { level: number; profile_version: string; reason: string } | null
  difficulty_setting_revision?: number | null
}

export type GameSessionCreated = {
  session_id: string
  players: PlayerSeat[]
  generation?: string | null
  cpu_difficulties?: CpuDifficulty[] | null
}

export type ResultDeliveryEntry = {
  ordinal: number
  event_id: string
  kind: 'hand' | 'settlement'
  payload: Record<string, unknown>
}

export type ResultDeliveryEnvelope = {
  version: 1
  generation: string
  session_id: string
  delivery_revision: number
  acked_ordinal: number
  head: ResultDeliveryEntry | null
  terminal_ordinal: number | null
  route: 'result' | 'human_turn' | 'settlement_wait' | 'ending' | 'selection'
  action_version: number | null
}

export type GameScreenState =
  | { status: 'waiting' }
  | {
      status: 'human_turn'
      cpuDifficulties?: CpuDifficulty[] | null
      actionVersion: number
      turn: HumanTurn
      players: PlayerSeat[]
      recentDialogues: DialogueEvent[]
    }
  | {
      status: 'complete'
      cpuDifficulties?: CpuDifficulty[] | null
      result: MatchResult
      settlement: MatchSettlement | LocalMatchSettlement
      players: PlayerSeat[]
      resultAsset: ResultAsset | null
      resultAssetObjectUrl: string | null
      resultAssetLoadFailed: boolean
      resultDialogue: ResultDialogue | null
      resultDialogues?: ResultDialogue[]
      endingEventId?: string | null
    }
  | { status: 'result_delivery'; delivery: ResultDeliveryEnvelope }
  | { status: 'settlement_wait'; delivery: ResultDeliveryEnvelope }
  | { status: 'ending'; generation: string; eventId: string; payload: { version: number; cg_asset_id: string | null; music_asset_id: string | null; dialogue_text: string | null } | null }

export type MatchSettlement = {
  last_place_seat: number
  current_hp: number | null
  cpu_character_id: number | null
  defeat_stage: number | null
  game_over: boolean
  cpu_completed: boolean
}

export type LocalMatchSettlement = {
  progression_version: 2
  mode: 'progress' | 'omake'
  cpu_character_id: number | null
  defeat_stage: number | null
  stage_changed: boolean
  cpu_completed: boolean
}

export type ResultAsset = {
  id: number
  cpu_character_id: number
  defeat_stage: number
  mime_type: string | null
  url: string
}

export type ResultDialogue = {
  cpu_character_id: number
  event_key: string
  text: string
}

export type GameClientMessage =
  | { type: 'authenticate'; access_token: string; generation?: string }
  | { type: 'action'; legal_action_index: number; action_version: number; generation?: string }

export type DialogueEvent = {
  cpu_character_id: number
  seat: number
  event_key: string
  text: string
}

export type GameServerMessage =
  | ({ type: 'result_delivery' } & ResultDeliveryEnvelope)
  | { type: 'human_turn'; cpu_difficulties?: CpuDifficulty[] | null; action_version: number; turn: HumanTurn; generation?: string | null; session_id?: string }
  | {
      type: 'match_complete'
      cpu_difficulties?: CpuDifficulty[] | null
      result: MatchResult
      settlement: MatchSettlement
      result_asset: ResultAsset | null
      result_dialogue: ResultDialogue | null
      result_dialogues?: ResultDialogue[]
      ending_event_id?: string | null
      generation?: string | null
      session_id?: string
    }
  | { type: 'dialogue_event'; cpu_character_id: number; seat: number; event_key: string; text: string }
  | { type: 'sound_effect'; generation: string; session_id: string; action_version: number; event_index: number; event_key: string; asset_id: string; url: string }
  | { type: 'voice_effect'; generation: string; session_id: string; action_version: number; event_index: number; actor_seat: number | null; event_key: string; source_kind?: 'action' | 'result'; asset_id: string; url: string }
  | { type: 'error'; code: string; message: string }
