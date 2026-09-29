import { useEffect, useState, type FormEvent } from 'react'
import { getSessionUser, login, logout, type SessionUser } from './services/api'

function safeReturnPath(path: string | null): string | null {
  if (!path || !path.startsWith('/') || path.startsWith('//') || path.includes('\\')) {
    return null
  }
  return path
}

function initialReturnPath(): string {
  const queryPath = safeReturnPath(new URLSearchParams(window.location.search).get('next'))
  const currentPath = `${window.location.pathname}${window.location.search}`
  if (queryPath) return queryPath
  if (window.location.pathname === '/login' || window.location.pathname === '/') return '/lots'
  return currentPath
}

function LoginForm({ onLogin }: { onLogin: (user: SessionUser) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    setPending(true)
    setError('')
    try {
      onLogin(await login({ email, password }))
    } catch {
      setError('Email hoặc mật khẩu không đúng.')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="brand-mark" aria-hidden="true">🌾</div>
        <p className="eyebrow">NÔNG SẢN · CHUỖI LẠNH</p>
        <h1 id="login-title">Đăng nhập</h1>
        <p className="muted">Đăng nhập vào không gian làm việc của tổ chức bạn.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            autoComplete="username"
            type="email"
            required
            maxLength={320}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <label htmlFor="password">Mật khẩu</label>
          <input
            id="password"
            autoComplete="current-password"
            type="password"
            required
            maxLength={1024}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={pending} type="submit">
            {pending ? 'Đang đăng nhập…' : 'Đăng nhập'}
          </button>
        </form>
      </section>
    </main>
  )
}

function LotsLanding({ user, onLogout }: { user: SessionUser; onLogout: () => void }) {
  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/lots"><span aria-hidden="true">🌾</span> Nông sản chuỗi lạnh</a>
        <div className="user-menu">
          <span>{user.full_name}</span>
          <button className="quiet-button" onClick={onLogout} type="button">Đăng xuất</button>
        </div>
      </header>
      <section className="content-panel">
        <p className="eyebrow">{user.organization_name}</p>
        <h1>Danh sách lô</h1>
        <p className="muted">Bạn đã đăng nhập vào tổ chức của mình.</p>
        <div className="empty-state">
          <span className="empty-icon" aria-hidden="true">📦</span>
          <h2>Chưa có lô nào</h2>
          <p>Các lô nông sản của tổ chức sẽ hiển thị tại đây.</p>
        </div>
      </section>
    </main>
  )
}

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [returnPath, setReturnPath] = useState(initialReturnPath)

  useEffect(() => {
    let active = true
    const requestedPath = initialReturnPath()

    getSessionUser()
      .then((sessionUser) => {
        if (!active) return
        setUser(sessionUser)
        if (window.location.pathname === '/login' || window.location.pathname === '/') {
          window.history.replaceState({}, '', requestedPath)
        }
      })
      .catch(() => {
        if (!active) return
        window.history.replaceState({}, '', `/login?next=${encodeURIComponent(requestedPath)}`)
      })
      .finally(() => {
        if (active) setCheckingSession(false)
      })

    const handleExpiredSession = () => {
      const requested = `${window.location.pathname}${window.location.search}`
      const safePath = safeReturnPath(requested) ?? '/lots'
      setReturnPath(safePath)
      setUser(null)
      window.history.replaceState({}, '', `/login?next=${encodeURIComponent(safePath)}`)
    }
    window.addEventListener('auth:expired', handleExpiredSession)

    return () => {
      active = false
      window.removeEventListener('auth:expired', handleExpiredSession)
    }
  }, [])

  async function handleLogout() {
    try {
      await logout()
    } finally {
      setUser(null)
      setReturnPath('/lots')
      window.history.replaceState({}, '', '/login?next=%2Flots')
    }
  }

  if (checkingSession) {
    return <main className="loading-screen" role="status">Đang kiểm tra phiên đăng nhập…</main>
  }

  if (!user) {
    return (
      <LoginForm
        onLogin={(sessionUser) => {
          setUser(sessionUser)
          window.history.replaceState({}, '', returnPath)
        }}
      />
    )
  }

  return <LotsLanding user={user} onLogout={handleLogout} />
}
