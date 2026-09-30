import { useState, useEffect, useCallback, useRef } from 'react'
import { FarmWorkspace, type WorkspaceTab } from './components/FarmWorkspace'
import { LoginView } from './components/LoginView'
import { checkHealth, getCurrentUser, logout } from './services/api'
import type { SessionUser } from './types'

export default function App() {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(null)
  const [initializing, setInitializing] = useState(true)
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('overview')
  const [isDark, setIsDark] = useState<boolean>(() => {
    try {
      return localStorage.getItem('anime-theme') === 'dark'
    } catch {
      return false
    }
  })

  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [toastVisible, setToastVisible] = useState(false)
  const toastTimerRef = useRef<number | null>(null)

  const notify = useCallback((message: string) => {
    setToastMessage(message)
    setToastVisible(true)
    if (toastTimerRef.current !== null) {
      window.clearTimeout(toastTimerRef.current)
    }
    toastTimerRef.current = window.setTimeout(() => {
      setToastVisible(false)
    }, 2600)
  }, [])

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.remove('light')
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
      root.classList.add('light')
    }
    try {
      localStorage.setItem('anime-theme', isDark ? 'dark' : 'light')
    } catch {
      // Ignore storage errors
    }
  }, [isDark])

  useEffect(() => {
    let active = true

    async function bootstrap() {
      try {
        await checkHealth()
        if (active) setBackendOnline(true)
      } catch {
        if (active) {
          setBackendOnline(false)
          setInitializing(false)
        }
        return
      }

      try {
        const user = await getCurrentUser()
        if (active) setCurrentUser(user)
      } catch {
        if (active) setCurrentUser(null)
      } finally {
        if (active) setInitializing(false)
      }
    }

    void bootstrap()
    return () => {
      active = false
    }
  }, [])

  const handleLogout = async () => {
    await logout()
    setCurrentUser(null)
    notify('Đã đăng xuất khỏi phiên làm việc')
  }

  return (
    <>
      {initializing ? (
        <div
          className="login-hero section-pattern"
          style={{ alignItems: 'center', textAlign: 'center' }}
        >
          <div className="sticker-panel" style={{ padding: '32px 48px' }}>
            <h2 style={{ fontSize: '22px', marginBottom: '6px' }}>
              AgroChain đang khởi tạo...
            </h2>
            <p style={{ fontSize: '14px', color: 'var(--body-subtle)' }}>
              Đang đồng bộ trạng thái phiên làm việc với máy chủ
            </p>
          </div>
        </div>
      ) : currentUser ? (
        <FarmWorkspace
          key={currentUser.id}
          user={currentUser}
          activeTab={activeTab}
          onTabChange={(tab) => setActiveTab(tab)}
          onLogout={() => void handleLogout()}
          onNotify={notify}
        />
      ) : (
        <LoginView
          backendOnline={backendOnline}
          onLoginSuccess={(user) => {
            setCurrentUser(user)
            setActiveTab('overview')
          }}
          onNotify={notify}
        />
      )}

      <nav className="sc-switcher-bar" aria-label="Điều hướng nhanh và giao diện">
        {currentUser ? (
          <>
            <button
              type="button"
              onClick={() => setActiveTab('overview')}
              className={`sc-switcher__btn ${
                activeTab === 'overview' ? 'sc-switcher__btn--active' : ''
              }`}
            >
              Vùng trồng
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('security')}
              className={`sc-switcher__btn ${
                activeTab === 'security' ? 'sc-switcher__btn--active' : ''
              }`}
            >
              Phân quyền RLS
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('integrity')}
              className={`sc-switcher__btn ${
                activeTab === 'integrity' ? 'sc-switcher__btn--active' : ''
              }`}
            >
              Chuỗi Hash
            </button>
          </>
        ) : (
          <span className="sc-switcher__btn sc-switcher__btn--active">
            Xác thực phiên
          </span>
        )}

        <button
          type="button"
          className="sc-switcher__btn"
          onClick={() => {
            setIsDark((prev) => !prev)
            notify(
              !isDark
                ? 'Đã chuyển sang giao diện Tối (Dark Forest)'
                : 'Đã chuyển sang giao diện Sáng (Classroom Mint)'
            )
          }}
          aria-label="Chuyển đổi giao diện Sáng / Tối"
        >
          {isDark ? '☀ Sáng' : '☾ Tối'}
        </button>
      </nav>

      <div
        className={`anime-toast ${toastVisible ? 'show' : ''}`}
        role="status"
        aria-live="polite"
      >
        <span>✦</span>
        <span>{toastMessage}</span>
      </div>
    </>
  )
}
