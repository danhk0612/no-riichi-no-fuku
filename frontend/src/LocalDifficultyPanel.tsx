import { useEffect, useRef, useState } from 'react'
import { getLocalDifficulty, saveLocalDifficulty } from './api'
import type { LocalDifficulty } from './api'

export function LocalDifficultyPanel({ accessToken, onClose, onSaved }: {
  accessToken: string; onClose: () => void; onSaved: () => Promise<void>
}) {
  const [saved, setSaved] = useState<LocalDifficulty | null>(null)
  const [value, setValue] = useState(5)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const load = useRef(0)
  useEffect(() => {
    const token = ++load.current
    void getLocalDifficulty(accessToken).then((result) => {
      if (load.current === token) { setSaved(result); setValue(result.setting) }
    }).catch((e: Error) => { if (load.current === token) setError(e.message) })
    return () => { load.current++ }
  }, [accessToken])
  async function save() {
    if (!saved || busy) return
    const token = load.current
    setBusy(true); setError(null); setMessage(null)
    try {
      const result = await saveLocalDifficulty(accessToken, value, saved.revision)
      if (load.current !== token) return
      setSaved(result); setValue(result.setting)
      setMessage('저장했습니다. 다음 대국부터 적용됩니다.')
      await onSaved()
    } catch (e) {
      if (load.current === token) setError(e instanceof Error ? e.message : '저장하지 못했습니다.')
    } finally { if (load.current === token) setBusy(false) }
  }
  return <section className="selection-panel difficulty-panel" aria-label="난이도 설정">
    <div className="panel-heading"><h2>난이도 설정</h2><button type="button" onClick={onClose}>닫기</button></div>
    <p>새 대국부터 적용됩니다. 진행 중인 대국은 시작할 때의 난이도를 유지합니다.</p>
    <p>완료 보충 CPU는 1, 오마케는 10입니다. 진행 초기화 후에도 설정은 유지됩니다.</p>
    <label>게임 난이도 <select aria-label="게임 난이도" value={value} disabled={!saved || busy}
      onChange={(e) => { setValue(Number(e.target.value)); setMessage(null) }}>
      {Array.from({ length: 10 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
    </select></label>
    <button type="button" disabled={!saved || busy} onClick={() => { void save() }}>{busy ? '저장 중…' : '난이도 저장'}</button>
    {message && <p role="status">{message}</p>}{error && <p className="form-error" role="alert">{error}</p>}
  </section>
}
