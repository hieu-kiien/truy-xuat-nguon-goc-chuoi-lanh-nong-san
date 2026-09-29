import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, getSessionUser, login, logout, type SessionUser } from './services/api'
import FarmManagementPage from './pages/FarmManagementPage'
import Icon from './Icon'

function safeReturnPath(path: string | null): string | null {
  if (!path || !path.startsWith('/') || path.startsWith('//') || path.includes('\\')) {
    return null
  }
  return path
}

function initialReturnPath(): string {
  const queryPath = safeReturnPath(new URLSearchParams(window.location.search).get('next'))
  const savedPath = safeReturnPath(window.history.state?.returnPath ?? null)
  const currentPath = `${window.location.pathname}${window.location.search}`
  if (queryPath) return queryPath
  if (savedPath) return savedPath
  if (window.location.pathname === '/login' || window.location.pathname === '/') return '/lots'
  return safeReturnPath(currentPath) ?? '/lots'
}

function LoginForm({ onLogin }: { onLogin: (user: SessionUser) => void }) {
  const [email, setEmail] = useState(import.meta.env.DEV ? 'admin@gmail.com' : '')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    setPending(true)
    setError('')
    try {
      onLogin(await login({ email, password }))
    } catch (loginError) {
      if (loginError instanceof ApiError && loginError.status === 401) {
        setError('Email hoặc mật khẩu không đúng.')
      } else if (loginError instanceof ApiError) {
        setError('Dịch vụ đăng nhập đang gặp sự cố. Vui lòng thử lại sau.')
      } else {
        setError('Không kết nối được máy chủ. Hãy kiểm tra backend trên cổng 8000.')
      }
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-layout" aria-labelledby="login-title">
        <div className="auth-panel">
          <a className="auth-brand" href="/" aria-label="Nông sản chuỗi lạnh">
            <span className="brand-mark" aria-hidden="true"><Icon name="sprout" size={22} /></span>
            <span>Nông sản <small>TRUY XUẤT NGUỒN GỐC</small></span>
          </a>
          <div className="auth-content">
            <p className="eyebrow">KHÔNG GIAN LÀM VIỆC</p>
            <h1 id="login-title">Đăng nhập</h1>
            <p className="auth-description">Tiếp tục quản lý vùng trồng và nông sản của tổ chức bạn.</p>
            {import.meta.env.DEV && (
              <p className="demo-account-hint">Tài khoản demo: <strong>admin@gmail.com</strong></p>
            )}
            <form className="auth-form" onSubmit={handleSubmit}>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                autoComplete="username"
                type="email"
                required
                maxLength={320}
                placeholder="admin@gmail.com"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value)
                  setError('')
                }}
              />
              <label htmlFor="password">Mật khẩu</label>
              <div className="password-field">
                <input
                  id="password"
                  autoComplete="current-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  maxLength={1024}
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value)
                    setError('')
                  }}
                />
                <button
                  className="password-toggle"
                  type="button"
                  aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((visible) => !visible)}
                >
                  <Icon name={showPassword ? 'eyeOff' : 'eye'} size={18} />
                </button>
              </div>
              {error && <p className="form-error" role="alert">{error}</p>}
              <button className="primary-button" disabled={pending} type="submit">
                {pending ? 'Đang đăng nhập…' : 'Đăng nhập'}
              </button>
            </form>
          </div>
          <p className="auth-footnote"><Icon name="lock" size={15} /> Phiên làm việc được bảo vệ</p>
        </div>
        <aside className="auth-visual" aria-label="Hành trình nông sản">
          <p className="visual-kicker"><span /> NÔNG SẢN · CHUỖI LẠNH</p>
          <div className="visual-copy">
            <h2>Từ vùng trồng<br />đến chuỗi lạnh.</h2>
            <p>Một hành trình rõ ràng bắt đầu từ thông tin vùng trồng.</p>
          </div>
          <div className="journey-list" aria-hidden="true">
            <div className="journey-step">
              <span className="journey-icon"><Icon name="leaf" size={18} /></span>
              <span><strong>Vùng trồng</strong><small>Nơi nông sản bắt đầu</small></span>
            </div>
            <div className="journey-step">
              <span className="journey-icon"><Icon name="package" size={18} /></span>
              <span><strong>Lô nông sản</strong><small>Thông tin theo từng lô</small></span>
            </div>
            <div className="journey-step">
              <span className="journey-icon"><Icon name="lock" size={18} /></span>
              <span><strong>Bảo quản</strong><small>Gắn kết chuỗi lạnh</small></span>
            </div>
          </div>
        </aside>
      </section>
    </main>
  )
}

function LotsLanding({ user, onLogout }: { user: SessionUser; onLogout: () => void }) {
  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/lots"><span aria-hidden="true"><Icon name="sprout" size={21} /></span> Nông sản chuỗi lạnh</a>
        <nav className="main-nav" aria-label="Điều hướng chính">
          <a className="active" href="/lots" aria-current="page">Lô hàng</a>
          {(user.role === 'grower' || user.role === 'organization_admin') && <a href="/farms">Thửa đất</a>}
        </nav>
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
          <span className="empty-icon"><Icon name="package" size={34} /></span>
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
        window.history.replaceState({ returnPath: requestedPath }, '', '/login')
      })
      .finally(() => {
        if (active) setCheckingSession(false)
      })

    const handleExpiredSession = () => {
      const requested = `${window.location.pathname}${window.location.search}`
      const safePath = safeReturnPath(requested) ?? '/lots'
      setReturnPath(safePath)
      setUser(null)
      window.history.replaceState({ returnPath: safePath }, '', '/login')
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
      window.history.replaceState({}, '', '/login')
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

  if (window.location.pathname === '/farms') {
    return <FarmManagementPage user={user} onLogout={handleLogout} />
  }

  return <LotsLanding user={user} onLogout={handleLogout} />
}
