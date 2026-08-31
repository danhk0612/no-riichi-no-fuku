import React, { useEffect, useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { AuthPanel } from './AuthPanel'
import { CpuSelection } from './CpuSelection'
import {
  createGameSession,
  gameWebSocketUrl,
  getActiveGameSession,
  getSelectableCpus,
  loginMember,
  registerMember,
} from './api'
import { MahjongTable } from './game/MahjongTable'
import type {
  CpuChoice,
  GameClientMessage,
  GameScreenState,
  GameServerMessage,
  PlayerSeat,
} from './game/types'
import './style.css'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
}

function App() {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [cpus, setCpus] = useState<CpuChoice[] | null>(null)
  const [selectedCpuIds, setSelectedCpuIds] = useState<number[]>([])
  const [players, setPlayers] = useState<PlayerSeat[]>([])
  const [gameState, setGameState] = useState<GameScreenState>({ status: 'waiting' })
  const [busy, setBusy] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => () => socketRef.current?.close(1000), [])

  async function loadCpus(token: string) {
    const choices = await getSelectableCpus(token)
    setCpus(choices)
    setSelectedCpuIds([])
  }

  async function enterAuthenticated(token: string) {
    const activeGame = await getActiveGameSession(token)
    if (activeGame) {
      setAccessToken(token)
      setPlayers(activeGame.players)
      setCpus(null)
      setGameState({ status: 'waiting' })
      connectGame(activeGame.session_id, token, activeGame.players)
      return
    }
    await loadCpus(token)
    setAccessToken(token)
  }

  async function authenticate(loginId: string, password: string) {
    setBusy(true)
    setError(null)
    try {
      const token = await loginMember(loginId, password)
      await enterAuthenticated(token)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function register(
    loginId: string,
    password: string,
    playerName: string,
  ) {
    setBusy(true)
    setError(null)
    try {
      await registerMember(loginId, password, playerName)
      const token = await loginMember(loginId, password)
      await enterAuthenticated(token)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  function toggleCpu(cpuId: number) {
    setSelectedCpuIds((current) => current.includes(cpuId)
      ? current.filter((id) => id !== cpuId)
      : [...current, cpuId])
  }

  function connectGame(sessionId: string, token: string, seats: PlayerSeat[]) {
    const socket = new WebSocket(gameWebSocketUrl(sessionId))
    socketRef.current = socket
    let completed = false

    socket.addEventListener('open', () => {
      const message: GameClientMessage = {
        type: 'authenticate',
        access_token: token,
      }
      socket.send(JSON.stringify(message))
    })
    socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data as string) as GameServerMessage
      if (message.type === 'human_turn') {
        setGameState({
          status: 'human_turn',
          actionVersion: message.action_version,
          turn: message.turn,
          players: seats,
        })
        setError(null)
        setActionPending(false)
        return
      }
      if (message.type === 'match_complete') {
        completed = true
        setGameState({
          status: 'complete',
          result: message.result,
          settlement: message.settlement,
          players: seats,
        })
        setActionPending(false)
        socket.close(1000)
        return
      }
      setError(message.message)
      setActionPending(false)
    })
    socket.addEventListener('error', () => {
      setError('게임 서버 연결에 실패했습니다.')
      setActionPending(false)
    })
    socket.addEventListener('close', (event) => {
      if (!completed && event.code !== 1000) {
        setError(`게임 연결이 종료되었습니다. (${event.code})`)
      }
      if (socketRef.current === socket) socketRef.current = null
    })
  }

  async function startGame() {
    if (!accessToken || selectedCpuIds.length !== 3) return
    setBusy(true)
    setError(null)
    try {
      const created = await createGameSession(accessToken, selectedCpuIds)
      setPlayers(created.players)
      setGameState({ status: 'waiting' })
      setCpus(null)
      connectGame(created.session_id, accessToken, created.players)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  function submitAction(legalActionIndex: number) {
    const socket = socketRef.current
    if (
      !socket
      || socket.readyState !== WebSocket.OPEN
      || actionPending
      || gameState.status !== 'human_turn'
    ) return
    setActionPending(true)
    const message: GameClientMessage = {
      type: 'action',
      legal_action_index: legalActionIndex,
      action_version: gameState.actionVersion,
    }
    socket.send(JSON.stringify(message))
  }

  async function nextGame() {
    if (!accessToken) return
    setBusy(true)
    setError(null)
    try {
      await loadCpus(accessToken)
      setGameState({ status: 'waiting' })
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  function logout() {
    socketRef.current?.close(1000)
    socketRef.current = null
    setAccessToken(null)
    setCpus(null)
    setSelectedCpuIds([])
    setPlayers([])
    setGameState({ status: 'waiting' })
    setError(null)
  }

  return (
    <main className="shell">
      <header className="app-header">
        <p className="eyebrow">4-PLAYER RIICHI MAHJONG</p>
        <h1>No Riichi No Fuku</h1>
        <p>플레이어 1명과 CPU 3명이 진행하는 동풍전</p>
      </header>
      {!accessToken && (
        <AuthPanel
          busy={busy}
          error={error}
          onLogin={authenticate}
          onRegister={register}
        />
      )}
      {accessToken && cpus && (
        <CpuSelection
          busy={busy}
          cpus={cpus}
          error={error}
          onLogout={logout}
          onStart={startGame}
          onToggle={toggleCpu}
          selectedIds={selectedCpuIds}
        />
      )}
      {accessToken && !cpus && (
        <>
          <div className="game-toolbar">
            <span>{players.map((player) => player.name).join(' · ')}</span>
          </div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <MahjongTable
            actionsDisabled={actionPending}
            onAction={submitAction}
            onNextGame={busy ? undefined : nextGame}
            state={gameState}
          />
        </>
      )}
    </main>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
