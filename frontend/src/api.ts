import type { CpuChoice, GameSessionCreated } from './game/types'

type TokenResponse = {
  access_token: string
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
): Promise<GameSessionCreated> {
  return apiRequest('/api/game/sessions', {
    method: 'POST',
    body: JSON.stringify({ cpu_character_ids: cpuCharacterIds }),
  }, accessToken)
}

export function gameWebSocketUrl(sessionId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/game/sessions/${sessionId}/ws`
}
