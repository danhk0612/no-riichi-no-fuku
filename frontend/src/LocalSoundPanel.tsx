import { useEffect, useState } from 'react'
import {
  getCharacterVoiceSelection, getEndingResources, getSoundSelection, listBackgroundTracks, listLocalCharacters, listLocalMedia, listSoundEffectSets,
  putAudioPackSelection, putCharacterVoiceSelection, putEndingResources, putSoundSelection, saveBackgroundTrack, saveSoundEffectSet, uploadLocalMedia,
} from './api'
import type { AudioPackSelection, BackgroundTrack, CharacterVoiceSelection, EndingResources, MediaAsset, SoundEffectSet, SoundSelection } from './api'

const SOUND_KEYS = ['chi', 'pon', 'kan', 'riichi', 'ron', 'tsumo'] as const

export function LocalSoundPanel({ accessToken, onClose, onSelectionChanged, onPlaybackChanged }: {
  accessToken: string
  onClose: () => void
  onSelectionChanged: (selection: SoundSelection) => void
  onPlaybackChanged: () => void
}) {
  const [media, setMedia] = useState<MediaAsset[]>([])
  const [sets, setSets] = useState<SoundEffectSet[]>([])
  const [tracks, setTracks] = useState<BackgroundTrack[]>([])
  const [selection, setSelection] = useState<SoundSelection | null>(null)
  const [audioPacks, setAudioPacks] = useState<AudioPackSelection | null>(null)
  const [characters, setCharacters] = useState<{ id: number; name: string }[]>([])
  const [voiceLinks, setVoiceLinks] = useState<Record<number, CharacterVoiceSelection>>({})
  const [ending, setEnding] = useState<EndingResources>({ cg_asset_id: null, music_track_id: null, dialogue_text: null })
  const [setId, setSetId] = useState('')
  const [setLabel, setSetLabel] = useState('')
  const [setActive, setSetActive] = useState(true)
  const [clips, setClips] = useState<Record<string, string>>({})
  const [trackLabel, setTrackLabel] = useState('')
  const [trackAssetId, setTrackAssetId] = useState('')
  const [trackId, setTrackId] = useState('')
  const [trackActive, setTrackActive] = useState(true)
  const [uploadKind, setUploadKind] = useState<'image' | 'audio'>('audio')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    const [nextMedia, nextSets, nextTracks, nextSelection, nextEnding] = await Promise.all([
      listLocalMedia(accessToken), listSoundEffectSets(accessToken), listBackgroundTracks(accessToken),
      getSoundSelection(accessToken), getEndingResources(accessToken),
    ])
    setMedia(nextMedia); setSets(nextSets); setTracks(nextTracks); setSelection(nextSelection); onSelectionChanged(nextSelection); setEnding(nextEnding)
    setAudioPacks(nextSelection.audio_packs)
    const nextCharacters = await listLocalCharacters(accessToken)
    setCharacters(nextCharacters)
    const nextVoices = await Promise.all(nextCharacters.map((character) => getCharacterVoiceSelection(accessToken, character.id)))
    setVoiceLinks(Object.fromEntries(nextVoices.map((value) => [value.cpu_id, value])))
  }

  useEffect(() => { void refresh().catch((caught) => setError(message(caught))) }, [accessToken])

  function selectSet(id: string) {
    setSetId(id)
    const set = sets.find((item) => item.id === id)
    setSetLabel(set?.label ?? '')
    setSetActive(set?.active ?? true)
    setClips(set?.clips ?? {})
  }

  function selectTrack(id: string) {
    setTrackId(id)
    const track = tracks.find((item) => item.id === id)
    setTrackLabel(track?.label ?? '')
    setTrackAssetId(track?.media_asset_id ?? '')
    setTrackActive(track?.active ?? true)
  }

  async function run(action: () => Promise<void>) {
    setBusy(true); setError(null)
    try { await action() } catch (caught) { setError(message(caught)) } finally { setBusy(false) }
  }

  const audioAssets = media.filter((asset) => asset.kind === 'audio' && asset.available !== false)
  const imageAssets = media.filter((asset) => asset.kind === 'image' && asset.available !== false)

  return (
    <section className="sound-panel" aria-label="사운드와 엔딩 자료 설정">
      <div className="sound-panel-heading"><div><p className="eyebrow">LOCAL CONTENT</p><h2>사운드와 엔딩 설정</h2></div><button className="text-button" onClick={onClose} type="button">닫기</button></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="sound-panel-grid">
        <section className="sound-card">
          <h3>파일 등록</h3>
          <label>자료 종류<select value={uploadKind} onChange={(event) => setUploadKind(event.target.value as 'image' | 'audio')}><option value="audio">오디오</option><option value="image">이미지</option></select></label>
          <label>파일<input type="file" accept={uploadKind === 'audio' ? '.mp3,.wav,.ogg,audio/*' : '.jpg,.jpeg,.png,.webp,image/*'} disabled={busy} onChange={(event) => {
            const input = event.currentTarget
            const file = input.files?.[0]
            if (file) void run(async () => { await uploadLocalMedia(accessToken, uploadKind, file); await refresh(); input.value = '' })
          }} /></label>
          <p className="muted">이미지 5 MiB, 오디오 32 MiB까지. 파일은 교체·설정 변경으로 삭제되지 않습니다.</p>
          <h3>배경음 등록</h3>
          <label>편집할 배경음<select value={trackId} onChange={(event) => selectTrack(event.target.value)}><option value="">새 배경음</option>{tracks.map((track) => <option key={track.id} value={track.id}>{track.label}{track.active ? '' : ' · 비활성'}</option>)}</select></label>
          <label>표시 이름<input value={trackLabel} onChange={(event) => setTrackLabel(event.target.value)} maxLength={120} /></label>
          <label>오디오 파일<select value={trackAssetId} onChange={(event) => setTrackAssetId(event.target.value)}><option value="">선택</option>{audioAssets.map((asset) => <option key={asset.id} value={asset.id}>{asset.id.slice(0, 8)} · {asset.mime_type}</option>)}</select></label>
          {trackId && <label className="inline-check"><input type="checkbox" checked={trackActive} onChange={(event) => setTrackActive(event.target.checked)} />사용 가능</label>}
          <button disabled={busy || !trackLabel.trim() || !trackAssetId} onClick={() => void run(async () => {
            await saveBackgroundTrack(accessToken, { label: trackLabel, active: trackActive, media_asset_id: trackAssetId }, trackId || undefined)
            selectTrack(''); await refresh()
          })} type="button">{trackId ? '배경음 수정 저장' : '배경음 등록'}</button>
          <ul className="sound-list">{tracks.map((track) => <li key={track.id}><span>{track.label}{track.available ? '' : ' · 파일 없음'}</span><span><button disabled={busy} onClick={() => selectTrack(track.id)} type="button">편집</button><button disabled={busy} onClick={() => void run(async () => { await saveBackgroundTrack(accessToken, { label: track.label, active: !track.active, media_asset_id: track.media_asset_id }, track.id); await refresh() })} type="button">{track.active ? '비활성화' : '활성화'}</button></span></li>)}</ul>
        </section>
        <section className="sound-card">
          <h3>효과음 세트</h3>
          <label>편집할 세트<select value={setId} onChange={(event) => selectSet(event.target.value)}><option value="">새 세트</option>{sets.map((set) => <option key={set.id} value={set.id}>{set.label}{set.active ? '' : ' · 비활성'}</option>)}</select></label>
          <label>표시 이름<input value={setLabel} onChange={(event) => setSetLabel(event.target.value)} maxLength={120} /></label>
          <label className="inline-check"><input type="checkbox" checked={setActive} onChange={(event) => setSetActive(event.target.checked)} />사용 가능</label>
          {SOUND_KEYS.map((key) => <label key={key}>{key.toUpperCase()}<select value={clips[key] ?? ''} onChange={(event) => setClips((current) => ({ ...current, [key]: event.target.value }))}><option value="">무음</option>{audioAssets.map((asset) => <option key={asset.id} value={asset.id}>{asset.id.slice(0, 8)} · {asset.mime_type}</option>)}</select></label>)}
          <button disabled={busy || !setLabel.trim()} onClick={() => void run(async () => {
            const next = { label: setLabel, active: setActive, clips: Object.fromEntries(Object.entries(clips).filter(([, id]) => !!id)) }
            const saved = await saveSoundEffectSet(accessToken, next, setId || undefined); setSetId(saved.id); await refresh()
          })} type="button">{setId ? '세트 수정 저장' : '세트 등록'}</button>
          <h3>사용할 자료 선택</h3>
          <label>효과음 세트<select value={selection?.effect_set_id ?? ''} onChange={(event) => setSelection((current) => current ? { ...current, effect_set_id: event.target.value || null } : current)}><option value="">사용 안 함</option>{sets.filter((set) => set.active || set.id === selection?.effect_set_id).map((set) => <option key={set.id} value={set.id}>{set.label}{set.active ? '' : ' · 비활성'}</option>)}</select></label>
          <div className="track-order"><strong>배경음 순환 목록</strong>{tracks.filter((track) => track.active && track.available).map((track) => <label className="inline-check" key={track.id}><input type="checkbox" checked={selection?.bgm_ids.includes(track.id) ?? false} onChange={() => setSelection((current) => {
            if (!current) return current
            const next = current.bgm_ids.includes(track.id) ? current.bgm_ids.filter((id) => id !== track.id) : [...current.bgm_ids, track.id]
            return { ...current, bgm_ids: next }
          })} />{track.label}</label>)}</div>
          {!!selection?.bgm_ids.length && <ol className="selected-track-order" aria-label="배경음 재생 순서">{selection.bgm_ids.map((id, index) => {
            const track = tracks.find((item) => item.id === id)
            const unavailable = !track || !track.active || !track.available
            return <li key={id}>
              <span>{index + 1}. {track?.label ?? '등록되지 않은 곡'}{unavailable ? ' · 사용할 수 없음' : ''}</span>
              <span>{!unavailable && <><button aria-label={`${index + 1}번 배경음 위로`} disabled={busy || index === 0} onClick={() => setSelection((current) => current ? { ...current, bgm_ids: move(current.bgm_ids, index, index - 1) } : current)} type="button">↑</button>
                <button aria-label={`${index + 1}번 배경음 아래로`} disabled={busy || index === selection.bgm_ids.length - 1} onClick={() => setSelection((current) => current ? { ...current, bgm_ids: move(current.bgm_ids, index, index + 1) } : current)} type="button">↓</button></>}
                <button aria-label={`${index + 1}번 배경음 선택 해제`} disabled={busy} onClick={() => setSelection((current) => current ? { ...current, bgm_ids: current.bgm_ids.filter((selectedId) => selectedId !== id) } : current)} type="button">해제</button></span>
            </li>
          })}</ol>}
          <button disabled={busy || !selection} onClick={() => void run(async () => { if (!selection) return; const updated = await putSoundSelection(accessToken, selection.effect_set_id, selection.bgm_ids); setSelection(updated); onSelectionChanged(updated) })} type="button">사운드 선택 저장</button>
          {audioPacks && <>
            <h3>등록 팩 재생 전환</h3>
            <p className="muted">기존 설정과 파일은 보존됩니다. 팩 모드로 저장하면 해당 종류의 기존 재생을 중지하고 새 팩만 사용합니다.</p>
            <label>SFX 재생 방식<select value={audioPacks.sfx_mode} onChange={(event) => setAudioPacks((current) => current ? { ...current, sfx_mode: event.target.value as 'legacy' | 'pack' } : current)}><option value="legacy">기존 설정 유지</option><option value="pack">등록 팩 사용</option></select></label>
            {audioPacks.sfx_mode === 'pack' && <label>SFX 팩<select value={audioPacks.sfx_pack_id ?? ''} onChange={(event) => setAudioPacks((current) => current ? { ...current, sfx_pack_id: event.target.value || null } : current)}><option value="">지정 기본팩 사용</option>{audioPacks.packs.filter((pack) => pack.kind === 'sfx').map((pack) => <option key={pack.id} value={pack.id}>{pack.pack_id}</option>)}</select></label>}
            <label>BGM 재생 방식<select value={audioPacks.bgm_mode} onChange={(event) => setAudioPacks((current) => current ? { ...current, bgm_mode: event.target.value as 'legacy' | 'pack' } : current)}><option value="legacy">기존 설정 유지</option><option value="pack">등록 팩 사용</option></select></label>
            {audioPacks.bgm_mode === 'pack' && <label>BGM 팩<select value={audioPacks.bgm_pack_id ?? ''} onChange={(event) => setAudioPacks((current) => current ? { ...current, bgm_pack_id: event.target.value || null } : current)}><option value="">지정 기본팩 사용</option>{audioPacks.packs.filter((pack) => pack.kind === 'bgm').map((pack) => <option key={pack.id} value={pack.id}>{pack.pack_id}</option>)}</select></label>}
            <button disabled={busy} onClick={() => void run(async () => { if (!audioPacks) return; const updated = await putAudioPackSelection(accessToken, audioPacks); onPlaybackChanged(); setSelection(updated); setAudioPacks(updated.audio_packs); onSelectionChanged(updated) })} type="button">팩 재생 방식 저장</button>
          </>}
          <h3>캐릭터 음성팩 연결</h3>
          <p className="muted">기본값은 적용한 캐릭터팩의 음성 기본 참조를 사용합니다. 선택된 유효 팩의 slot 누락은 무음이며, 끔은 항상 무음입니다.</p>
          {characters.map((character) => {
            const voice = voiceLinks[character.id]
            if (!voice) return null
            return <div className="sound-voice-row" key={character.id}><strong>{character.name}</strong>
              <label>음성팩<select value={voice.selection_mode === 'off' ? 'off' : voice.selection_mode === 'selected' ? voice.selected_pack_id ?? '' : ''} onChange={(event) => setVoiceLinks((current) => ({ ...current, [character.id]: { ...voice, selection_mode: event.target.value === 'off' ? 'off' : event.target.value ? 'selected' : 'default', selected_pack_id: event.target.value && event.target.value !== 'off' ? event.target.value : null } }))}>
                <option value="">캐릭터 기본팩</option><option value="off">음성 끔</option>{voice.packs.map((pack) => <option key={pack.id} value={pack.id}>{pack.namespace}/{pack.pack_id}</option>)}
              </select></label>
              <button disabled={busy} onClick={() => void run(async () => { const saved = await putCharacterVoiceSelection(accessToken, voice); onPlaybackChanged(); setVoiceLinks((current) => ({ ...current, [character.id]: saved })) })} type="button">저장</button>
            </div>
          })}
        </section>
        <section className="sound-card">
          <h3>엔딩 자료</h3>
          <label>엔딩 CG<select value={ending.cg_asset_id ?? ''} onChange={(event) => setEnding((current) => ({ ...current, cg_asset_id: event.target.value || null }))}><option value="">미등록</option>{imageAssets.map((asset) => <option key={asset.id} value={asset.id}>{asset.id.slice(0, 8)} · {asset.mime_type}</option>)}</select></label>
          <label>엔딩 음악<select value={ending.music_track_id ?? ''} onChange={(event) => setEnding((current) => ({ ...current, music_track_id: event.target.value || null }))}><option value="">미등록</option>{tracks.filter((track) => track.active || track.id === ending.music_track_id).map((track) => <option key={track.id} value={track.id}>{track.label}{track.active ? '' : ' · 비활성'}</option>)}</select></label>
          <label>평문 엔딩 대사<textarea rows={5} maxLength={4000} value={ending.dialogue_text ?? ''} onChange={(event) => setEnding((current) => ({ ...current, dialogue_text: event.target.value || null }))} /></label>
          <button disabled={busy} onClick={() => void run(async () => { const saved = await putEndingResources(accessToken, ending); setEnding(saved) })} type="button">엔딩 자료 저장</button>
          <p className="muted">다음 엔딩부터 적용됩니다. 이미 대기 중인 엔딩 자료는 고정되어 있습니다.</p>
        </section>
      </div>
    </section>
  )
}

function message(error: unknown) { return error instanceof Error ? error.message : '요청에 실패했습니다.' }
function move(items: string[], from: number, to: number) {
  if (to < 0 || to >= items.length) return items
  const next = [...items]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}
