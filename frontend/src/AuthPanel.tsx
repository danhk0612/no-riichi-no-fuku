import { useState, type FormEvent } from 'react'

type AuthPanelProps = {
  busy: boolean
  error: string | null
  onLogin: (loginId: string, password: string) => Promise<void>
  onRegister: (loginId: string, password: string, playerName: string) => Promise<void>
}

export function AuthPanel({ busy, error, onLogin, onRegister }: AuthPanelProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [playerName, setPlayerName] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (mode === 'register') await onRegister(loginId, password, playerName)
    else await onLogin(loginId, password)
  }

  return (
    <section className="entry-panel">
      <p className="eyebrow">MEMBER ACCESS</p>
      <h2>{mode === 'login' ? '로그인' : '회원가입'}</h2>
      <form onSubmit={submit}>
        <label>
          로그인 ID
          <input
            autoComplete="username"
            disabled={busy}
            maxLength={64}
            minLength={mode === 'register' ? 3 : 1}
            onChange={(event) => setLoginId(event.target.value)}
            required
            value={loginId}
          />
        </label>
        {mode === 'register' && (
          <label>
            플레이어 이름
            <input
              disabled={busy}
              maxLength={80}
              onChange={(event) => setPlayerName(event.target.value)}
              required
              value={playerName}
            />
          </label>
        )}
        <label>
          비밀번호
          <input
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            disabled={busy}
            maxLength={128}
            minLength={mode === 'register' ? 8 : 1}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" disabled={busy} type="submit">
          {busy ? '처리 중…' : (mode === 'login' ? '로그인' : '가입 후 로그인')}
        </button>
      </form>
      <button
        className="text-button"
        disabled={busy}
        onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
        type="button"
      >
        {mode === 'login' ? '새 회원으로 시작' : '기존 회원 로그인'}
      </button>
    </section>
  )
}
