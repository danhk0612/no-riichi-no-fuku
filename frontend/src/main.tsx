import React, { useEffect, useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { AuthPanel } from './AuthPanel'
import { CpuSelection } from './CpuSelection'
import {
  createGameSession,
  getLocalPlay,
  getRosterCandidates,
  confirmLocalRoster,
  resetLocalPlay,
  acknowledgeLocalEnding,
  gameWebSocketUrl,
  getActiveGameSession,
  getProfile,
  getRecentGameSession,
  getResultAssetObjectUrl,
  getSelectableCpus,
  loginMember,
  registerMember,
  updatePlayerName,
} from './api'
import type { LocalPlayState } from './api'
import { MahjongTable } from './game/MahjongTable'
import type {
  CpuChoice,
  DialogueEvent,
  GameClientMessage,
  GameScreenState,
  GameServerMessage,
  PlayerSeat,
} from './game/types'
import './style.css'

declare global {
  interface Window { nrnfDesktop?: { isDesktop: true } }
}

const DESKTOP_SESSION = 'local-desktop-session'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
}

function App() {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [cpus, setCpus] = useState<CpuChoice[] | null>(null)
  const [selectedCpuIds, setSelectedCpuIds] = useState<number[]>([])
  const [localPlay, setLocalPlay] = useState<LocalPlayState | null>(null)
  const [rosterMode, setRosterMode] = useState(false)
  const [players, setPlayers] = useState<PlayerSeat[]>([])
  const [gameState, setGameState] = useState<GameScreenState>({ status: 'waiting' })
  const [busy, setBusy] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [desktopProfile, setDesktopProfile] = useState<string | null>(null)
  const [profileName, setProfileName] = useState('')
  const [profileBusy, setProfileBusy] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)
  const resultAssetUrlRef = useRef<string | null>(null)
  const resultAssetLoadVersionRef = useRef(0)
  const desktopStartedRef = useRef(false)
  const localGenerationRef = useRef<string | null>(null)
  const isDesktop = window.nrnfDesktop?.isDesktop === true

  function storeLocalPlay(play: LocalPlayState) {
    localGenerationRef.current = play.generation
    setLocalPlay(play)
  }

  useEffect(() => () => {
    socketRef.current?.close(1000)
    if (resultAssetUrlRef.current) URL.revokeObjectURL(resultAssetUrlRef.current)
  }, [])

  function clearResultAssetUrl() {
    resultAssetLoadVersionRef.current += 1
    if (resultAssetUrlRef.current) {
      URL.revokeObjectURL(resultAssetUrlRef.current)
      resultAssetUrlRef.current = null
    }
  }

  async function loadCpus(token: string) {
    const choices = await getSelectableCpus(token)
    setCpus(choices)
    setSelectedCpuIds([])
  }

  async function loadLocalCpus(token: string, play: LocalPlayState) {
    const expectedGeneration = play.generation
    const choices = await getRosterCandidates(token)
    if (localGenerationRef.current !== expectedGeneration) return
    const rosterIds = new Set(play.roster.map((item) => item.cpu_character_id))
    const shown = play.phase === 'roster_required' ? choices : choices.filter((cpu) => rosterIds.has(cpu.id))
    setCpus(shown)
    setSelectedCpuIds([])
    setRosterMode(play.phase === 'roster_required')
  }

  async function enterAuthenticated(token: string) {
    if (isDesktop) {
      const profile = await getProfile(token)
      setDesktopProfile(profile.player_name ?? '플레이어')
      setProfileName(profile.player_name ?? '플레이어')
    }
    let activeGame = await getActiveGameSession(token)
    let play: LocalPlayState | null = null
    if (isDesktop) {
      play = await getLocalPlay(token)
      storeLocalPlay(play)
      if (!activeGame && play.recent_session_id) activeGame = await getRecentGameSession(token)
    }
    if (activeGame) {
      setAccessToken(token)
      setPlayers(activeGame.players)
      setCpus(null)
      setGameState({ status: 'waiting' })
      connectGame(activeGame.session_id, token, activeGame.players, activeGame.generation)
      return
    }
    if (isDesktop && play?.phase === 'ending_pending' && play.ending_event_id) {
      setAccessToken(token)
      setGameState({ status: 'ending', generation: play.generation, eventId: play.ending_event_id, payload: play.ending_payload })
      return
    }
    if (isDesktop && play) await loadLocalCpus(token, play)
    else await loadCpus(token)
    setAccessToken(token)
  }

  useEffect(() => {
    if (!isDesktop || desktopStartedRef.current) return
    desktopStartedRef.current = true
    void enterAuthenticated(DESKTOP_SESSION).catch((caught: unknown) => {
      setError(errorMessage(caught))
    })
  }, [isDesktop])

  async function savePlayerName() {
    if (!accessToken || !isDesktop) return
    setProfileBusy(true)
    setError(null)
    try {
      const profile = await updatePlayerName(accessToken, profileName.trim())
      setDesktopProfile(profile.player_name ?? '플레이어')
      setProfileName(profile.player_name ?? '플레이어')
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setProfileBusy(false)
    }
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

  function connectGame(sessionId: string, token: string, seats: PlayerSeat[], sessionGeneration?: string | null) {
    const socket = new WebSocket(gameWebSocketUrl(sessionId))
    socketRef.current = socket
    setActionPending(true)
    let completed = false
    let recentDialogues: DialogueEvent[] = []

    socket.addEventListener('open', () => {
      if (socketRef.current !== socket) return
      const message: GameClientMessage = {
        type: 'authenticate',
        access_token: token,
        ...(isDesktop && (sessionGeneration || localPlay)
          ? { generation: sessionGeneration ?? localPlay?.generation }
          : {}),
      }
      socket.send(JSON.stringify(message))
    })
    socket.addEventListener('message', (event) => {
      if (socketRef.current !== socket) return
      const message = JSON.parse(event.data as string) as GameServerMessage
      if (isDesktop && 'generation' in message && message.generation && localGenerationRef.current
        && message.generation !== localGenerationRef.current) return
      if (message.type === 'dialogue_event') {
        recentDialogues = [...recentDialogues, {
          cpu_character_id: message.cpu_character_id,
          seat: message.seat,
          event_key: message.event_key,
          text: message.text,
        }].slice(-10)
        const dialogues = recentDialogues
        setGameState((current) => current.status === 'human_turn'
          ? { ...current, recentDialogues: dialogues }
          : current)
        return
      }
      if (message.type === 'human_turn') {
        setGameState({
          status: 'human_turn',
          actionVersion: message.action_version,
          turn: message.turn,
          players: seats,
          recentDialogues,
        })
        setError(null)
        setActionPending(false)
        return
      }
      if (message.type === 'match_complete') {
        completed = true
        clearResultAssetUrl()
        setGameState({
          status: 'complete',
          result: message.result,
          settlement: message.settlement,
          players: seats,
          resultAsset: message.result_asset,
          resultAssetObjectUrl: null,
          resultAssetLoadFailed: false,
          resultDialogue: message.result_dialogue,
          resultDialogues: message.result_dialogues ?? (message.result_dialogue ? [message.result_dialogue] : []),
          endingEventId: message.ending_event_id,
        })
        if (isDesktop) {
          const completedGeneration = message.generation ?? localGenerationRef.current
          void getLocalPlay(token).then((play) => {
            if (play.generation === completedGeneration && localGenerationRef.current === completedGeneration) storeLocalPlay(play)
          }).catch(() => {})
        }
        if (message.result_asset) {
          const asset = message.result_asset
          const loadVersion = resultAssetLoadVersionRef.current
          void getResultAssetObjectUrl(token, asset.url)
            .then((objectUrl) => {
              if (loadVersion !== resultAssetLoadVersionRef.current) {
                URL.revokeObjectURL(objectUrl)
                return
              }
              setGameState((current) => {
                if (
                  current.status !== 'complete'
                  || current.resultAsset?.id !== asset.id
                ) {
                  URL.revokeObjectURL(objectUrl)
                  return current
                }
                resultAssetUrlRef.current = objectUrl
                return { ...current, resultAssetObjectUrl: objectUrl }
              })
            })
            .catch((caught) => {
              if (loadVersion !== resultAssetLoadVersionRef.current) return
              setError(errorMessage(caught))
              setGameState((current) => (
                current.status === 'complete' && current.resultAsset?.id === asset.id
                  ? { ...current, resultAssetLoadFailed: true }
                  : current
              ))
            })
        }
        setActionPending(false)
        socket.close(1000)
        return
      }
      setError(message.message)
      setActionPending(false)
    })
    socket.addEventListener('error', () => {
      if (socketRef.current !== socket) return
      setError('게임 서버 연결에 실패했습니다.')
      setActionPending(true)
    })
    socket.addEventListener('close', (event) => {
      if (socketRef.current !== socket) return
      if (!completed) {
        setActionPending(true)
        const recovery = isDesktop
          ? '새로고침 후 저장된 대국에 복귀할 수 있습니다.'
          : '새로고침 후 다시 로그인하면 저장된 대국에 복귀할 수 있습니다.'
        setError(`게임 연결이 종료되었습니다. (${event.code}) ${recovery}`)
      }
      socketRef.current = null
    })
  }

  async function startGame() {
    if (!accessToken || (rosterMode ? selectedCpuIds.length < 3 : selectedCpuIds.length !== 3)) return
    setBusy(true)
    setError(null)
    try {
      if (isDesktop && rosterMode && localPlay) {
        const updated = await confirmLocalRoster(accessToken, localPlay.generation, selectedCpuIds)
        storeLocalPlay(updated)
        await loadLocalCpus(accessToken, updated)
        setError(null)
        return
      }
      const created = await createGameSession(accessToken, selectedCpuIds, isDesktop ? localPlay?.generation : undefined)
      setPlayers(created.players)
      setGameState({ status: 'waiting' })
      setCpus(null)
      connectGame(created.session_id, accessToken, created.players, created.generation)
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
      ...(isDesktop && localPlay ? { generation: localPlay.generation } : {}),
    }
    socket.send(JSON.stringify(message))
  }

  async function nextGame() {
    if (!accessToken) return
    setBusy(true)
    setError(null)
    try {
      clearResultAssetUrl()
      if (isDesktop && localPlay?.phase === 'ending_pending' && localPlay.ending_event_id) {
        setGameState({ status: 'ending', generation: localPlay.generation, eventId: localPlay.ending_event_id, payload: localPlay.ending_payload })
        return
      }
      if (isDesktop && localPlay) await loadLocalCpus(accessToken, localPlay)
      else await loadCpus(accessToken)
      setGameState({ status: 'waiting' })
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function continueFromEnding() {
    if (!accessToken || gameState.status !== 'ending') return
    setBusy(true)
    setError(null)
    try {
      const updated = await acknowledgeLocalEnding(accessToken, gameState.generation, gameState.eventId)
      storeLocalPlay(updated)
      clearResultAssetUrl()
      await loadLocalCpus(accessToken, updated)
      setGameState({ status: 'waiting' })
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function resetPlay() {
    if (!accessToken || !isDesktop || !localPlay) return
    if (!window.confirm('현재 대국과 모든 진행도, 참가 명단, 엔딩 상태를 초기화할까요? 등록 자료와 설정, 이미지·음악 파일은 보존됩니다.')) return
    setBusy(true)
    setError(null)
    socketRef.current?.close(1000)
    socketRef.current = null
    clearResultAssetUrl()
    try {
      const updated = await resetLocalPlay(accessToken, localPlay.generation)
      storeLocalPlay(updated)
      await loadLocalCpus(accessToken, updated)
      setGameState({ status: 'waiting' })
      setPlayers([])
    } catch (caught) {
      setError(errorMessage(caught))
      const fresh = await getLocalPlay(accessToken).catch(() => null)
      if (fresh) storeLocalPlay(fresh)
    } finally {
      setBusy(false)
    }
  }

  function logout() {
    socketRef.current?.close(1000)
    socketRef.current = null
    clearResultAssetUrl()
    setAccessToken(null)
    setCpus(null)
    setSelectedCpuIds([])
    setLocalPlay(null)
    localGenerationRef.current = null
    setRosterMode(false)
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
      {!isDesktop && !accessToken && (
        <AuthPanel
          busy={busy}
          error={error}
          onLogin={authenticate}
          onRegister={register}
        />
      )}
      {isDesktop && !accessToken && (
        <p className={error ? 'form-error' : 'waiting-panel'} role={error ? 'alert' : 'status'}>
          {error ?? '로컬 프로필을 불러오는 중…'}
        </p>
      )}
      {accessToken && cpus && (
        <>
          {isDesktop && <ProfileEditor busy={profileBusy} name={profileName} onNameChange={setProfileName} onSave={savePlayerName} />}
          <CpuSelection
            busy={busy}
            cpus={cpus}
            error={error}
            onLogout={logout}
            onReset={isDesktop ? resetPlay : undefined}
            showLogout={!isDesktop}
            rosterMode={isDesktop && rosterMode}
            allowCompleted={!!localPlay && (localPlay.phase === 'omake' || localPlay.roster.filter((cpu) => cpu.defeat_stage < 3).length < 3)}
            onStart={startGame}
            onToggle={toggleCpu}
            selectedIds={selectedCpuIds}
          />
        </>
      )}
      {accessToken && !cpus && (
        <>
          <div className="game-toolbar">
            {isDesktop && <ProfileEditor busy={profileBusy} name={profileName} onNameChange={setProfileName} onSave={savePlayerName} />}
            <span>{players.map((player) => player.name).join(' · ') || desktopProfile}</span>
            {isDesktop && <button className="text-button" disabled={busy} onClick={resetPlay} type="button">초기화</button>}
          </div>
          {error && <p className="form-error" role="alert">{error}</p>}
          {gameState.status === 'ending' ? (
            <section className="match-result ending-panel" aria-label="엔딩">
              <p className="eyebrow">ENDING</p>
              <h2>모든 참가 CPU 완료</h2>
              <p>{gameState.payload?.dialogue_text ?? '엔딩 대사가 등록되지 않았습니다.'}</p>
              <p className="result-asset-placeholder">엔딩 CG와 음악은 아직 등록되지 않았습니다.</p>
              <button className="primary-button" disabled={busy} onClick={continueFromEnding} type="button">오마케로 계속하기</button>
            </section>
          ) : <MahjongTable
            actionsDisabled={actionPending}
            allowGameOverContinue={isDesktop}
            onAction={submitAction}
            onNextGame={busy ? undefined : nextGame}
            state={gameState}
          />}
        </>
      )}
    </main>
  )
}

function ProfileEditor({ busy, name, onNameChange, onSave }: {
  busy: boolean
  name: string
  onNameChange: (value: string) => void
  onSave: () => void
}) {
  return (
    <div className="profile-editor">
      <label>플레이어 이름 <input aria-label="플레이어 이름" maxLength={80} value={name} onChange={(event) => onNameChange(event.target.value)} /></label>
      <button disabled={busy || !name.trim()} onClick={onSave} type="button">이름 저장</button>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
