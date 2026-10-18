import type { CpuChoice, GameSessionCreated } from './game/types'

type TokenResponse = {
  access_token: string
}

export type LocalProfile = {
  player_name: string | null
  current_hp: number | null
  max_hp: number | null
}

export type LocalPlayState = {
  generation: string
  phase: 'roster_required' | 'progress' | 'ending_pending' | 'omake'
  roster: { cpu_character_id: number; defeat_stage: number }[]
  ending_event_id: string | null
  ending_payload: { version: number; cg_asset_id: string | null; music_asset_id: string | null; dialogue_text: string | null } | null
  active_session_id: string | null
  recent_session_id: string | null
  legacy_active: boolean
}

export type MediaAsset = { id: string; kind: 'image' | 'audio'; mime_type: string; byte_size: number; url: string; available: boolean | null }
export type SoundEffectSet = { id: string; label: string; active: boolean; clips: Record<string, string> }
export type BackgroundTrack = { id: string; label: string; active: boolean; media_asset_id: string; available: boolean; url: string | null }
export type SoundSelection = {
  effect_set_id: string | null; bgm_ids: string[]; effect_sets: SoundEffectSet[]; tracks: BackgroundTrack[];
  effect_set_available: boolean; bgm_available: boolean[]
  audio_packs: AudioPackSelection
}
export type AudioPackSelection = {
  schema_version: 1; revision: number; sfx_mode: 'legacy' | 'pack'; sfx_pack_id: string | null
  bgm_mode: 'legacy' | 'pack'; bgm_pack_id: string | null
  defaults: { sfx: string | null; bgm: string | null }
  packs: { id: string; kind: 'sfx' | 'bgm'; pack_id: string; revision: string }[]
  bgm_slots: Record<'title' | 'selection' | 'game' | 'result', { asset_id: string; url: string; pack_id: string; slot: string } | null>
}
export type CharacterVoiceSelection = {
  schema_version: 1; cpu_id: number; revision: number; default_pack_id: string | null
  selected_pack_id: string | null; selection_mode: 'default' | 'selected' | 'off'
  packs: { id: string; namespace: string; pack_id: string; revision: string }[]
}
export type EndingResources = { cg_asset_id: string | null; music_track_id: string | null; dialogue_text: string | null }
export type ResolvedEnding = {
  acknowledged: boolean;
  cg?: { asset_id: string | null; url: string | null; available: boolean };
  music?: { asset_id: string | null; url: string | null; available: boolean };
  dialogue_text?: string | null;
}
export type PromptPair = {
  positive: string
  negative: string
  overrides: { positive: boolean; negative: boolean }
}
export type CharacterContent = {
  schema_version: 1
  cpu_id: number
  revision: number
  pack_revision_id: string | null
  pack_source: { prompts: Record<'appearance' | 'upper_underwear' | 'lower_underwear', { positive: string; negative: string }>; levels: Record<string, { framing: Record<'profile' | 'full_body' | 'cg', { positive: string; negative: string }> }>; metadata: Record<string, unknown> | null } | null
  pack: { id: string; pack_id: string; applied_revision_id: string; applied_revision: number; registered_revision_id: string | null; update_available: boolean } | null
  prompts: Record<'appearance' | 'upper_underwear' | 'lower_underwear', PromptPair>
  measurements_cm: { height: string | null; bust: string | null; waist: string | null; hips: string | null }
  measurement_overrides: { height: boolean; bust: boolean; waist: boolean; hips: boolean }
  levels: Record<string, Record<'profile' | 'full_body' | 'cg', PromptPair & { revision: number; media: { media_id: string; url: string; digest: string } | null }>>
}
export type LocalCharacterChoice = { id: number; slug: string; name: string }
export type ContentPack = {
  id: string
  identity: [string, string, string]
  kind: 'character' | 'sfx' | 'bgm' | 'voice'
  namespace: string
  pack_id: string
  status: 'normal' | 'unresolved' | 'conflict'
  issues: string[]
  registered_revision: { id: string; revision: number; content_digest: string; manifest_digest: string } | null
  applied_revision_id: string | null
  revisions: { id: string; revision: number; content_digest: string; manifest_digest: string }[]
}
export type PackListing = { schema_version: 1; packs: ContentPack[]; scan_entries: { source: string; identity: unknown; status: string; issues: string[] }[] }

async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const response = await fetch(path, { ...init, headers })
  if (!response.ok) {
    let message = `요청에 실패했습니다. (${response.status})`
    try {
      const body = await response.json() as { detail?: string | { message?: string } }
      if (typeof body.detail === 'string') message = body.detail
      else if (body.detail && typeof body.detail.message === 'string') message = body.detail.message
    } catch {
      // Keep the status-based message for non-JSON responses.
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function registerMember(
  loginId: string,
  password: string,
  playerName: string,
): Promise<unknown> {
  return apiRequest('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      login_id: loginId,
      password,
      player_name: playerName,
    }),
  })
}

export async function loginMember(
  loginId: string,
  password: string,
): Promise<string> {
  const token = await apiRequest<TokenResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ login_id: loginId, password }),
  })
  return token.access_token
}

export function getSelectableCpus(accessToken: string): Promise<CpuChoice[]> {
  return apiRequest('/api/game/cpus', {}, accessToken)
}

export function createGameSession(
  accessToken: string,
  cpuCharacterIds: number[],
  generation?: string,
): Promise<GameSessionCreated> {
  return apiRequest('/api/game/sessions', {
    method: 'POST',
    body: JSON.stringify({ cpu_character_ids: cpuCharacterIds, ...(generation ? { generation } : {}) }),
  }, accessToken)
}

export function getLocalPlay(accessToken: string): Promise<LocalPlayState> {
  return apiRequest('/api/local/play', {}, accessToken)
}

export function getRosterCandidates(accessToken: string): Promise<CpuChoice[]> {
  return apiRequest('/api/local/play/roster-candidates', {}, accessToken)
}

export function confirmLocalRoster(accessToken: string, generation: string, ids: number[]): Promise<LocalPlayState> {
  return apiRequest('/api/local/play/roster', {
    method: 'POST', body: JSON.stringify({ generation, cpu_character_ids: ids }),
  }, accessToken)
}

export function resetLocalPlay(accessToken: string, generation: string): Promise<LocalPlayState> {
  return apiRequest('/api/local/play/reset', {
    method: 'POST', body: JSON.stringify({ generation, confirm: true }),
  }, accessToken)
}

export function acknowledgeLocalEnding(accessToken: string, generation: string, endingEventId: string): Promise<LocalPlayState> {
  return apiRequest('/api/local/play/ending/ack', {
    method: 'POST', body: JSON.stringify({ generation, ending_event_id: endingEventId }),
  }, accessToken)
}

export function listLocalMedia(accessToken: string): Promise<MediaAsset[]> { return apiRequest('/api/local/media', {}, accessToken) }
export function uploadLocalMedia(accessToken: string, kind: 'image' | 'audio', file: File): Promise<MediaAsset> {
  const form = new FormData(); form.set('kind', kind); form.set('file', file)
  return apiRequest('/api/local/media', { method: 'POST', body: form }, accessToken)
}
export function listSoundEffectSets(accessToken: string): Promise<SoundEffectSet[]> { return apiRequest('/api/local/sound-effect-sets', {}, accessToken) }
export function saveSoundEffectSet(accessToken: string, values: Omit<SoundEffectSet, 'id'>, id?: string): Promise<SoundEffectSet> {
  return apiRequest(`/api/local/sound-effect-sets${id ? `/${id}` : ''}`, { method: id ? 'PATCH' : 'POST', body: JSON.stringify(values) }, accessToken)
}
export function listBackgroundTracks(accessToken: string): Promise<BackgroundTrack[]> { return apiRequest('/api/local/background-tracks', {}, accessToken) }
export function saveBackgroundTrack(accessToken: string, values: { label: string; active: boolean; media_asset_id: string }, id?: string): Promise<BackgroundTrack> {
  return apiRequest(`/api/local/background-tracks${id ? `/${id}` : ''}`, { method: id ? 'PATCH' : 'POST', body: JSON.stringify(values) }, accessToken)
}
export function getSoundSelection(accessToken: string): Promise<SoundSelection> { return apiRequest('/api/local/sound-selection', {}, accessToken) }
export function putSoundSelection(accessToken: string, effectSetId: string | null, bgmIds: string[]): Promise<SoundSelection> {
  return apiRequest('/api/local/sound-selection', { method: 'PUT', body: JSON.stringify({ effect_set_id: effectSetId, bgm_ids: bgmIds }) }, accessToken)
}
export function putAudioPackSelection(accessToken: string, selection: AudioPackSelection): Promise<SoundSelection> {
  return apiRequest('/api/local/audio-pack-selection', { method: 'PUT', body: JSON.stringify({
    expected_revision: selection.revision,
    sfx_mode: selection.sfx_mode, sfx_pack_id: selection.sfx_pack_id,
    bgm_mode: selection.bgm_mode, bgm_pack_id: selection.bgm_pack_id,
  }) }, accessToken).then(() => getSoundSelection(accessToken))
}
export function getCharacterVoiceSelection(accessToken: string, cpuId: number): Promise<CharacterVoiceSelection> {
  return apiRequest(`/api/local/characters/${cpuId}/voice-selection`, {}, accessToken)
}
export function putCharacterVoiceSelection(accessToken: string, value: CharacterVoiceSelection): Promise<CharacterVoiceSelection> {
  return apiRequest(`/api/local/characters/${value.cpu_id}/voice-selection`, { method: 'PUT', body: JSON.stringify({
    expected_revision: value.revision, selection_mode: value.selection_mode,
    selected_pack_id: value.selected_pack_id,
  }) }, accessToken)
}
export function getEndingResources(accessToken: string): Promise<EndingResources> { return apiRequest('/api/local/ending-resources', {}, accessToken) }
export function getCharacterContent(accessToken: string, cpuId: number): Promise<CharacterContent> {
  return apiRequest(`/api/local/characters/${cpuId}/content`, {}, accessToken)
}
export function listLocalCharacters(accessToken: string): Promise<LocalCharacterChoice[]> {
  return apiRequest('/api/admin/cpus', {}, accessToken)
}
export function patchCharacterContent(accessToken: string, cpuId: number, changes: {
  expected_revision: number
  prompts?: Record<string, { positive?: string; negative?: string }>
  framing?: { level: number; kind: 'profile' | 'full_body' | 'cg'; positive?: string; negative?: string }[]
  measurements_cm?: Partial<Record<'height' | 'bust' | 'waist' | 'hips', string | null>>
}): Promise<CharacterContent> {
  return apiRequest(`/api/local/characters/${cpuId}/content`, { method: 'PATCH', body: JSON.stringify(changes) }, accessToken)
}
export function listContentPacks(accessToken: string): Promise<PackListing> { return apiRequest('/api/local/packs', {}, accessToken) }
export function rescanContentPacks(accessToken: string): Promise<{ registry: PackListing }> {
  return apiRequest('/api/local/packs/rescan', { method: 'POST' }, accessToken)
}
export function putEndingResources(accessToken: string, values: EndingResources): Promise<EndingResources> {
  return apiRequest('/api/local/ending-resources', { method: 'PUT', body: JSON.stringify(values) }, accessToken)
}
export function getResolvedEnding(accessToken: string, generation: string, eventId: string): Promise<ResolvedEnding> {
  const params = new URLSearchParams({ generation, event_id: eventId })
  return apiRequest(`/api/local/play/ending?${params}`, {}, accessToken)
}
export async function getLocalMediaObjectUrl(accessToken: string, url: string): Promise<string> {
  const response = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!response.ok) throw new Error(`미디어를 불러오지 못했습니다. (${response.status})`)
  return URL.createObjectURL(await response.blob())
}

export function getActiveGameSession(
  accessToken: string,
): Promise<GameSessionCreated | null> {
  return apiRequest('/api/game/sessions/active', {}, accessToken)
}

export function getRecentGameSession(
  accessToken: string,
): Promise<GameSessionCreated | null> {
  return apiRequest('/api/game/sessions/recent', {}, accessToken)
}

export function getProfile(accessToken: string): Promise<LocalProfile> {
  return apiRequest('/api/profile/me', {}, accessToken)
}

export function updatePlayerName(accessToken: string, playerName: string): Promise<LocalProfile> {
  return apiRequest('/api/profile/me', {
    method: 'PATCH',
    body: JSON.stringify({ player_name: playerName }),
  }, accessToken)
}

export function gameWebSocketUrl(sessionId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/game/sessions/${sessionId}/ws`
}

export async function getResultAssetObjectUrl(
  accessToken: string,
  url: string,
): Promise<string> {
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) {
    throw new Error(`결과 CG를 불러오지 못했습니다. (${response.status})`)
  }
  return URL.createObjectURL(await response.blob())
}

export function applyCharacterPack(accessToken: string, cpuId: number, changes: {
  expected_revision: number; pack_id: string; registered_revision_id: string
}): Promise<CharacterContent> {
  return apiRequest(`/api/local/characters/${cpuId}/pack-application`, { method: 'POST', body: JSON.stringify(changes) }, accessToken)
}

export type LocalDifficulty = { version: 1; revision: number; setting: number; applies_to: 'next_match' }
export function getLocalDifficulty(accessToken: string): Promise<LocalDifficulty> {
  return apiRequest('/api/local/difficulty', {}, accessToken)
}
export function saveLocalDifficulty(accessToken: string, setting: number, expectedRevision: number): Promise<LocalDifficulty> {
  return apiRequest('/api/local/difficulty', { method: 'PUT', body: JSON.stringify({ setting, expected_revision: expectedRevision }) }, accessToken)
}
