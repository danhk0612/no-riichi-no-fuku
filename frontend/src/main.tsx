import React, { useEffect, useMemo, useRef, useState } from 'react'
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
  getLocalMediaObjectUrl,
  getResolvedEnding,
  getSoundSelection,
} from './api'
import type { LocalPlayState, ResolvedEnding, SoundSelection } from './api'
import { LocalSoundPanel } from './LocalSoundPanel'
import { LocalContentPanel } from './LocalContentPanel'
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
  const [soundSelection, setSoundSelection] = useState<SoundSelection | null>(null)
  const [soundSettingsOpen, setSoundSettingsOpen] = useState(false)
  const [contentSettingsOpen, setContentSettingsOpen] = useState(false)
  const [soundError, setSoundError] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const resultAssetUrlRef = useRef<string | null>(null)
  const resultAssetLoadVersionRef = useRef(0)
  const desktopStartedRef = useRef(false)
  const localGenerationRef = useRef<string | null>(null)
  const localRequestTokenRef = useRef(0)
  const playedSoundEventsRef = useRef(new Set<string>())
  const gameAudioTokenRef = useRef(0)
  const activeSoundEffectsRef = useRef(new Map<string, { audio: HTMLAudioElement; url: string }>())
  const isDesktop = window.nrnfDesktop?.isDesktop === true

  useEffect(() => {
    if (!isDesktop || !accessToken) { setSoundSelection(null); return }
    let current = true
    void getSoundSelection(accessToken).then((selection) => { if (current) setSoundSelection(selection) }).catch(() => {})
    return () => { current = false }
  }, [accessToken, isDesktop])

  function stopGameAudio() {
    gameAudioTokenRef.current += 1
    for (const { audio, url } of activeSoundEffectsRef.current.values()) {
      audio.pause()
      audio.src = ''
      URL.revokeObjectURL(url)
    }
    activeSoundEffectsRef.current.clear()
  }

  function beginLocalRequest(): number {
    localRequestTokenRef.current += 1
    return localRequestTokenRef.current
  }

  function isCurrentLocalRequest(requestToken: number, generation?: string): boolean {
    return requestToken === localRequestTokenRef.current
      && (generation === undefined || localGenerationRef.current === generation)
  }

  function storeLocalPlay(play: LocalPlayState, requestToken?: number): boolean {
    if (requestToken !== undefined && requestToken !== localRequestTokenRef.current) return false
    localGenerationRef.current = play.generation
    setLocalPlay(play)
    return true
  }

  useEffect(() => () => {
    socketRef.current?.close(1000)
    stopGameAudio()
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

  async function loadLocalCpus(token: string, play: LocalPlayState, requestToken: number) {
    const expectedGeneration = play.generation
    const choices = await getRosterCandidates(token)
    if (!isCurrentLocalRequest(requestToken, expectedGeneration)) return
    const rosterIds = new Set(play.roster.map((item) => item.cpu_character_id))
    const shown = play.phase === 'roster_required' ? choices : choices.filter((cpu) => rosterIds.has(cpu.id))
    setCpus(shown)
    setSelectedCpuIds([])
    setRosterMode(play.phase === 'roster_required')
    setPlayers([])
    setGameState({ status: 'waiting' })
  }

  async function reconcileLocalPlay(token: string, requestToken: number) {
    try {
      const play = await getLocalPlay(token)
      if (!isCurrentLocalRequest(requestToken)) return
      await restoreLocalPlay(token, play, requestToken)
    } catch {
      if (requestToken === localRequestTokenRef.current) {
        setError('현재 진행 상태를 다시 불러오지 못했습니다. 새로고침 후 복구하세요.')
      }
    }
  }

  async function restoreLocalPlay(token: string, play: LocalPlayState, requestToken: number) {
    const generation = play.generation
    if (!storeLocalPlay(play, requestToken)) return
    const activeGame = await getActiveGameSession(token)
    if (!isCurrentLocalRequest(requestToken, generation)) return
    if (activeGame && activeGame.generation === generation) {
      setAccessToken(token)
      setPlayers(activeGame.players)
      setCpus(null)
      setGameState({ status: 'waiting' })
      connectGame(activeGame.session_id, token, activeGame.players, activeGame.generation)
      return
    }
    if (play.phase === 'ending_pending' && play.ending_event_id) {
      socketRef.current?.close(1000)
      socketRef.current = null
      setAccessToken(token)
      setPlayers([])
      setCpus(null)
      setGameState({ status: 'ending', generation, eventId: play.ending_event_id, payload: play.ending_payload })
      return
    }
    if (play.phase === 'omake') {
      await loadLocalCpus(token, play, requestToken)
      if (isCurrentLocalRequest(requestToken, generation)) setAccessToken(token)
      return
    }
    if (play.recent_session_id) {
      const recentGame = await getRecentGameSession(token)
      if (!isCurrentLocalRequest(requestToken, generation)) return
      if (recentGame && recentGame.generation === generation) {
        setAccessToken(token)
        setPlayers(recentGame.players)
        setCpus(null)
        setGameState({ status: 'waiting' })
        connectGame(recentGame.session_id, token, recentGame.players, recentGame.generation)
        return
      }
    }
    await loadLocalCpus(token, play, requestToken)
    if (isCurrentLocalRequest(requestToken, generation)) setAccessToken(token)
  }

  async function enterAuthenticated(token: string) {
    const requestToken = isDesktop ? beginLocalRequest() : 0
    if (isDesktop) {
      const profile = await getProfile(token)
      if (!isCurrentLocalRequest(requestToken)) return
      setDesktopProfile(profile.player_name ?? '플레이어')
      setProfileName(profile.player_name ?? '플레이어')
      const play = await getLocalPlay(token)
      if (!isCurrentLocalRequest(requestToken)) return
      await restoreLocalPlay(token, play, requestToken)
      return
    }
    let activeGame = await getActiveGameSession(token)
    if (activeGame) {
      setAccessToken(token)
      setPlayers(activeGame.players)
      setCpus(null)
      setGameState({ status: 'waiting' })
      connectGame(activeGame.session_id, token, activeGame.players, activeGame.generation)
      return
    }
    await loadCpus(token)
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
    const requestToken = localRequestTokenRef.current
    socketRef.current = socket
    setActionPending(true)
    let completed = false
    let recentDialogues: DialogueEvent[] = []

    socket.addEventListener('open', () => {
      if (socketRef.current !== socket || (isDesktop && requestToken !== localRequestTokenRef.current)) return
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
      if (socketRef.current !== socket || (isDesktop && requestToken !== localRequestTokenRef.current)) return
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
      if (message.type === 'sound_effect') {
        const identity = `${message.generation}:${message.session_id}:${message.action_version}:${message.event_index}:${message.event_key}`
        if (playedSoundEventsRef.current.has(identity)) return
        playedSoundEventsRef.current.add(identity)
        const audioToken = gameAudioTokenRef.current
        void getLocalMediaObjectUrl(token, message.url).then((url) => {
          if (audioToken !== gameAudioTokenRef.current || message.generation !== localGenerationRef.current) {
            URL.revokeObjectURL(url)
            return
          }
          const audio = new Audio(url)
          activeSoundEffectsRef.current.set(identity, { audio, url })
          const release = () => {
            if (activeSoundEffectsRef.current.get(identity)?.audio === audio) activeSoundEffectsRef.current.delete(identity)
            URL.revokeObjectURL(url)
          }
          audio.addEventListener('ended', release, { once: true })
          audio.addEventListener('error', release, { once: true })
          void audio.play().catch(() => {
            const current = audioToken === gameAudioTokenRef.current
              && message.generation === localGenerationRef.current
              && activeSoundEffectsRef.current.get(identity)?.audio === audio
            release()
            if (current) setSoundError('효과음을 재생할 수 없습니다.')
          })
        }).catch(() => {})
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
            if (completedGeneration && isCurrentLocalRequest(requestToken, completedGeneration)
              && play.generation === completedGeneration) storeLocalPlay(play, requestToken)
          }).catch(() => {})
        }
        if (message.result_asset) {
          const asset = message.result_asset
          const loadVersion = resultAssetLoadVersionRef.current
          void getResultAssetObjectUrl(token, asset.url)
            .then((objectUrl) => {
              if (loadVersion !== resultAssetLoadVersionRef.current
                || (isDesktop && requestToken !== localRequestTokenRef.current)) {
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
              if (loadVersion !== resultAssetLoadVersionRef.current
                || (isDesktop && requestToken !== localRequestTokenRef.current)) return
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
      if (socketRef.current !== socket || (isDesktop && requestToken !== localRequestTokenRef.current)) return
      setError('게임 서버 연결에 실패했습니다.')
      setActionPending(true)
    })
    socket.addEventListener('close', (event) => {
      if (socketRef.current !== socket || (isDesktop && requestToken !== localRequestTokenRef.current)) return
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
    const requestToken = isDesktop ? beginLocalRequest() : 0
    const expectedGeneration = isDesktop ? localPlay?.generation : undefined
    setBusy(true)
    setError(null)
    try {
      if (isDesktop && rosterMode && localPlay) {
        const updated = await confirmLocalRoster(accessToken, localPlay.generation, selectedCpuIds)
        if (!isCurrentLocalRequest(requestToken, expectedGeneration)) return
        storeLocalPlay(updated, requestToken)
        if (updated.phase === 'ending_pending' && updated.ending_event_id) {
          setCpus(null)
          setPlayers([])
          setGameState({ status: 'ending', generation: updated.generation, eventId: updated.ending_event_id, payload: updated.ending_payload })
          setAccessToken(accessToken)
          setError(null)
          return
        }
        await loadLocalCpus(accessToken, updated, requestToken)
        setError(null)
        return
      }
      const created = await createGameSession(accessToken, selectedCpuIds, isDesktop ? localPlay?.generation : undefined)
      if (isDesktop && !isCurrentLocalRequest(requestToken, expectedGeneration)) return
      setPlayers(created.players)
      setGameState({ status: 'waiting' })
      setCpus(null)
      connectGame(created.session_id, accessToken, created.players, created.generation)
    } catch (caught) {
      if (!isDesktop || isCurrentLocalRequest(requestToken, expectedGeneration)) setError(errorMessage(caught))
    } finally {
      if (!isDesktop || requestToken === localRequestTokenRef.current) setBusy(false)
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
    const requestToken = isDesktop ? beginLocalRequest() : 0
    setBusy(true)
    stopGameAudio()
    setError(null)
    try {
      clearResultAssetUrl()
      if (isDesktop && localPlay?.phase === 'ending_pending' && localPlay.ending_event_id) {
        setGameState({ status: 'ending', generation: localPlay.generation, eventId: localPlay.ending_event_id, payload: localPlay.ending_payload })
        return
      }
      if (isDesktop && localPlay) await loadLocalCpus(accessToken, localPlay, requestToken)
      else await loadCpus(accessToken)
      if (isDesktop && !isCurrentLocalRequest(requestToken, localPlay?.generation)) return
      setGameState({ status: 'waiting' })
    } catch (caught) {
      if (!isDesktop || requestToken === localRequestTokenRef.current) setError(errorMessage(caught))
    } finally {
      if (!isDesktop || requestToken === localRequestTokenRef.current) setBusy(false)
    }
  }

  async function continueFromEnding() {
    if (!accessToken || gameState.status !== 'ending') return
    const requestToken = beginLocalRequest()
    const expectedGeneration = gameState.generation
    setBusy(true)
    setError(null)
    try {
      const updated = await acknowledgeLocalEnding(accessToken, gameState.generation, gameState.eventId)
      if (!isCurrentLocalRequest(requestToken, expectedGeneration)) return
      await restoreLocalPlay(accessToken, updated, requestToken)
      setSoundError(null)
      clearResultAssetUrl()
    } catch (caught) {
      if (isCurrentLocalRequest(requestToken, expectedGeneration)) {
        setError(errorMessage(caught))
        await reconcileLocalPlay(accessToken, requestToken)
      }
    } finally {
      if (requestToken === localRequestTokenRef.current) setBusy(false)
    }
  }

  async function resetPlay() {
    if (!accessToken || !isDesktop || !localPlay) return
    if (!window.confirm('현재 대국과 모든 진행도, 참가 명단, 엔딩 상태를 초기화할까요? 등록 자료와 설정, 이미지·음악 파일은 보존됩니다.')) return
    const requestToken = beginLocalRequest()
    const expectedGeneration = localPlay.generation
    setBusy(true)
    setError(null)
    socketRef.current?.close(1000)
    socketRef.current = null
    stopGameAudio()
    clearResultAssetUrl()
    try {
      const updated = await resetLocalPlay(accessToken, localPlay.generation)
      if (!isCurrentLocalRequest(requestToken, expectedGeneration)) return
      await restoreLocalPlay(accessToken, updated, requestToken)
    } catch (caught) {
      if (requestToken === localRequestTokenRef.current) {
        setError(errorMessage(caught))
        await reconcileLocalPlay(accessToken, requestToken)
      }
    } finally {
      if (requestToken === localRequestTokenRef.current) setBusy(false)
    }
  }

  function logout() {
    beginLocalRequest()
    socketRef.current?.close(1000)
    socketRef.current = null
    stopGameAudio()
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
        {isDesktop && accessToken && <button className="text-button" type="button" onClick={() => setSoundSettingsOpen((open) => !open)}>사운드·자료 설정</button>}
        {isDesktop && accessToken && <button className="text-button" type="button" onClick={() => setContentSettingsOpen((open) => !open)}>캐릭터 프롬프트·팩 설정</button>}
      </header>
      {isDesktop && accessToken && soundSettingsOpen && <LocalSoundPanel accessToken={accessToken} onClose={() => setSoundSettingsOpen(false)} onSelectionChanged={setSoundSelection} />}
      {isDesktop && accessToken && contentSettingsOpen && <LocalContentPanel accessToken={accessToken} onClose={() => setContentSettingsOpen(false)} />}
      {isDesktop && soundError && <p className="form-error" role="status">{soundError}</p>}
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
            <EndingScreen accessToken={accessToken} generation={gameState.generation} eventId={gameState.eventId} fallback={gameState.payload} busy={busy} onContinue={continueFromEnding} />
          ) : <MahjongTable
            actionsDisabled={actionPending}
            allowGameOverContinue={isDesktop}
            onAction={submitAction}
            onNextGame={busy ? undefined : nextGame}
            state={gameState}
          />}
        </>
      )}
      {isDesktop && accessToken && <BackgroundMusic accessToken={accessToken} selection={soundSelection} paused={gameState.status === 'ending'} />}
    </main>
  )
}

function BackgroundMusic({ accessToken, selection, paused }: { accessToken: string; selection: SoundSelection | null; paused: boolean }) {
  const [trackId, setTrackId] = useState<string | null>(null)
  const [blocked, setBlocked] = useState(false)
  const [retryRequired, setRetryRequired] = useState(false)
  const [retryToken, setRetryToken] = useState(0)
  const audioRef = useRef<{ audio: HTMLAudioElement; url: string } | null>(null)
  const tracksRef = useRef<NonNullable<SoundSelection['tracks']>>([])
  const orderedTracks = useMemo(() => {
    if (!selection) return []
    return selection.bgm_ids.map((id) => selection.tracks.find((track) => track.id === id))
      .filter((track): track is NonNullable<typeof track> => !!track && track.active && track.available && !!track.url)
  }, [selection])
  const trackOrder = orderedTracks.map((track) => track.id).join(',')
  tracksRef.current = orderedTracks
  const selectedTrack = orderedTracks.find((item) => item.id === trackId)

  useEffect(() => {
    setTrackId((current) => orderedTracks.some((track) => track.id === current) ? current : orderedTracks[0]?.id ?? null)
  }, [trackOrder])

  useEffect(() => {
    let current = true
    let objectUrl: string | null = null
    let audio: HTMLAudioElement | null = null
    const track = selectedTrack
    if (!track || paused) {
      audioRef.current?.audio.pause()
      audioRef.current = null
      return () => { current = false }
    }
    setBlocked(false)
    setRetryRequired(false)
    void getLocalMediaObjectUrl(accessToken, track.url!).then(async (url) => {
      if (!current) { URL.revokeObjectURL(url); return }
      objectUrl = url
      audio = new Audio(url)
      const activeAudio = audio
      audioRef.current = { audio, url }
      const isCurrentAudio = () => current && audioRef.current?.audio === activeAudio
      audio.addEventListener('ended', () => {
        if (!isCurrentAudio()) return
        const currentTracks = tracksRef.current
        const index = currentTracks.findIndex((item) => item.id === track.id)
        if (currentTracks.length <= 1) {
          activeAudio.currentTime = 0
          void activeAudio.play().catch(() => { if (isCurrentAudio()) { setRetryRequired(false); setBlocked(true) } })
          return
        }
        setTrackId(currentTracks[(index + 1) % currentTracks.length]?.id ?? null)
      })
      audio.addEventListener('error', () => { if (isCurrentAudio()) { setRetryRequired(true); setBlocked(true) } }, { once: true })
      try { await audio.play() } catch { if (isCurrentAudio()) { setRetryRequired(false); setBlocked(true) } }
    }).catch(() => { if (current) { setRetryRequired(true); setBlocked(true) } })
    return () => {
      current = false
      if (audioRef.current?.audio === audio) audioRef.current = null
      audio?.pause()
      if (audio) audio.src = ''
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [accessToken, trackId, selectedTrack?.url, paused, retryToken])

  if (!blocked || paused || orderedTracks.length === 0) return null
  return <button className="text-button audio-resume" type="button" onClick={() => {
    const activeAudio = audioRef.current?.audio
    if (retryRequired || !activeAudio) { setBlocked(false); setRetryToken((current) => current + 1); return }
    void activeAudio.play()
      .then(() => { if (audioRef.current?.audio === activeAudio) setBlocked(false) })
      .catch(() => { if (audioRef.current?.audio === activeAudio) setBlocked(true) })
  }}>배경음 재생</button>
}

function EndingScreen({ accessToken, generation, eventId, fallback, busy, onContinue }: {
  accessToken: string
  generation: string
  eventId: string
  fallback: { version: number; cg_asset_id: string | null; music_asset_id: string | null; dialogue_text: string | null } | null
  busy: boolean
  onContinue: () => void
}) {
  const [resources, setResources] = useState<ResolvedEnding | null>(null)
  const [cgUrl, setCgUrl] = useState<string | null>(null)
  const [musicUrl, setMusicUrl] = useState<string | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [imageError, setImageError] = useState(false)
  const requestRef = useRef(0)

  useEffect(() => {
    let active = true
    const request = ++requestRef.current
    setResources(null); setCgUrl(null); setMusicUrl(null); setLoadError(false); setImageError(false)
    let loadedCg: string | null = null
    let loadedMusic: string | null = null
    void getResolvedEnding(accessToken, generation, eventId).then(async (resolved) => {
      if (!active || request !== requestRef.current) return
      setResources(resolved)
      if (resolved.cg?.url) {
        try {
          const url = await getLocalMediaObjectUrl(accessToken, resolved.cg.url)
          if (!active || request !== requestRef.current) URL.revokeObjectURL(url)
          else { loadedCg = url; setCgUrl(url) }
        } catch { if (active) setLoadError(true) }
      }
      if (resolved.music?.url) {
        try {
          const url = await getLocalMediaObjectUrl(accessToken, resolved.music.url)
          if (!active || request !== requestRef.current) URL.revokeObjectURL(url)
          else { loadedMusic = url; setMusicUrl(url) }
        } catch { if (active) setLoadError(true) }
      }
    }).catch(() => { if (active) setLoadError(true) })
    return () => {
      active = false
      requestRef.current += 1
      if (loadedCg) URL.revokeObjectURL(loadedCg)
      if (loadedMusic) URL.revokeObjectURL(loadedMusic)
    }
  }, [accessToken, generation, eventId])

  const text = resources?.dialogue_text ?? fallback?.dialogue_text
  return (
    <section className="match-result ending-panel" aria-label="엔딩">
      <p className="eyebrow">ENDING</p>
      <h2>모든 참가 CPU 완료</h2>
      {cgUrl && !imageError ? <img className="ending-image" src={cgUrl} alt="엔딩 CG" onError={() => { setImageError(true); setLoadError(true) }} /> : <p className="result-asset-placeholder">{resources ? '엔딩 CG가 등록되지 않았거나 파일을 읽을 수 없습니다.' : '엔딩 자료를 불러오는 중…'}</p>}
      <p>{text || '엔딩 대사가 등록되지 않았습니다.'}</p>
      {musicUrl && <audio className="ending-audio" src={musicUrl} controls autoPlay onError={() => setLoadError(true)} />}
      {loadError && <p className="muted">일부 엔딩 자료를 재생하거나 불러오지 못했습니다. 계속하기는 사용할 수 있습니다.</p>}
      <button className="primary-button" disabled={busy || resources?.acknowledged === true} onClick={onContinue} type="button">오마케로 계속하기</button>
    </section>
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
