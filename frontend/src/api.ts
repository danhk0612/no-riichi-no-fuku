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

async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const response = await fetch(path, { ...init, headers })
  if (!response.ok) {
    let message = `요청에 실패했습니다. (${response.status})`
    try {
      const body = await response.json() as { detail?: string }
      if (typeof body.detail === 'string') message = body.detail
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
