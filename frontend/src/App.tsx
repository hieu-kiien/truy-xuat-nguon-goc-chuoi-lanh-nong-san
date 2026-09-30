import { useState, useEffect, useCallback, useRef } from 'react'
import { FarmWorkspace, type WorkspaceTab } from './components/FarmWorkspace'
import { LoginView } from './components/LoginView'
import { ApiError, checkHealth, getCurrentUser, logout } from './services/api'
import type { SessionUser } from './types'

const THEME_STORAGE_KEY = 'ttcs_theme'
const WORKSPACE_PATHS = new Set([
  '/lots',
  '/farms',
  '/security',
  '/integrity',
])

function readLocation() {
  return {
    pathname: window.location.pathname,
    search: window.location.search,
    hash: window.location.hash,
  }
}

function safeWorkspacePath(candidate: string | null): string | null {
  if (!candidate || !candidate.startsWith('/') || candidate.startsWith('//')) {
    return null
  }

  const url = new URL(candidate, window.location.origin)
  if (url.origin !== window.location.origin || !WORKSPACE_PATHS.has(url.pathname)) {
    return null
  }
  return `${url.pathname}${url.search}${url.hash}`
}

function routeForTab(tab: WorkspaceTab): string {
  return tab === 'overview'
    ? '/farms'
    : tab === 'security'
      ? '/security'
      : tab === 'integrity'
        ? '/integrity'
        : '/lots'
}

function tabForPath(pathname: string): WorkspaceTab {
  if (pathname === '/security') return 'security'
  if (pathname === '/integrity') return 'integrity'
  if (pathname === '/farms') return 'overview'
  return 'lots'
}

function loginPath(returnTo: string): string {
  return `/login?next=${encodeURIComponent(returnTo)}`
}

export default function App() {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(null)
  const [initializing, setInitializing] = useState(true)
  const [initialLocation] = useState(readLocation)
  const [location, setLocation] = useState(initialLocation)
  const activeTab = tabForPath(location.pathname)
  const [isDark, setIsDark] = useState<boolean>(() => {
    try {
      return localStorage.getItem(THEME_STORAGE_KEY) === 'dark'
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

  const navigate = useCallback((path: string, replace = false) => {
    if (replace) {
      window.history.replaceState(null, '', path)
    } else {
      window.history.pushState(null, '', path)
    }
    setLocation(readLocation())
  }, [])

  useEffect(() => {
    const syncLocation = () => setLocation(readLocation())
    window.addEventListener('popstate', syncLocation)
    return () => window.removeEventListener('popstate', syncLocation)
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
      localStorage.setItem(THEME_STORAGE_KEY, isDark ? 'dark' : 'light')
    } catch {
      // Ignore storage errors
    }
  }, [isDark])

  useEffect(() => {
    let active = true
    const initialReturnTo =
      safeWorkspacePath(
        `${initialLocation.pathname}${initialLocation.search}${initialLocation.hash}`
      ) ?? '/lots'

    async function bootstrap() {
      try {
        await checkHealth()
        if (active) setBackendOnline(true)
      } catch {
        if (active) {
          setBackendOnline(false)
          if (initialLocation.pathname !== '/login') {
            navigate(loginPath(initialReturnTo), true)
          }
          setInitializing(false)
        }
        return
      }

      try {
        const user = await getCurrentUser()
        if (active) {
          setCurrentUser(user)
          if (
            initialLocation.pathname === '/' ||
            initialLocation.pathname === '/login'
          ) {
            const requestedReturnTo = safeWorkspacePath(
              new URLSearchParams(initialLocation.search).get('next')
            )
            navigate(requestedReturnTo ?? '/lots', true)
          } else if (!WORKSPACE_PATHS.has(initialLocation.pathname)) {
            navigate('/lots', true)
          }
        }
      } catch {
        if (active) {
          setCurrentUser(null)
          if (initialLocation.pathname !== '/login') {
            navigate(loginPath(initialReturnTo), true)
          }
        }
      } finally {
        if (active) setInitializing(false)
      }
    }

    void bootstrap()
    return () => {
      active = false
    }
  }, [initialLocation, navigate])

  const handleLogout = async () => {
    try {
      await logout()
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 401)) {
        notify('Không thể đăng xuất. Vui lòng thử lại.')
        return
      }
    }
    setCurrentUser(null)
    navigate(loginPath('/lots'), true)
    notify('Đã đăng xuất khỏi phiên làm việc')
  }

  return (
    <>
      {initializing ? (
        <div className="login-hero section-pattern init-screen">
          <div className="sticker-panel init-card">
            <h2>AgroChain đang khởi tạo...</h2>
            <p className="panel-sub">
              Đang đồng bộ trạng thái phiên làm việc với máy chủ
            </p>
          </div>
        </div>
      ) : currentUser ? (
        <FarmWorkspace
          key={currentUser.id}
          user={currentUser}
          activeTab={activeTab}
          onTabChange={(tab) => navigate(routeForTab(tab))}
          onLogout={() => void handleLogout()}
          onNotify={notify}
        />
      ) : (
        <LoginView
          backendOnline={backendOnline}
          onLoginSuccess={(user) => {
            setCurrentUser(user)
            const requestedReturnTo = safeWorkspacePath(
              new URLSearchParams(location.search).get('next')
            )
            navigate(requestedReturnTo ?? '/lots', true)
          }}
          onNotify={notify}
        />
      )}

      <nav className="sc-switcher-bar" aria-label="Điều hướng nhanh và giao diện">
        {currentUser ? (
          <>
            <button
              type="button"
              onClick={() => navigate('/lots')}
              className={`sc-switcher__btn ${
                activeTab === 'lots' ? 'sc-switcher__btn--active' : ''
              }`}
            >
              Danh sách lô
            </button>
            <button
              type="button"
              onClick={() => navigate('/farms')}
              className={`sc-switcher__btn ${
                activeTab === 'overview' ? 'sc-switcher__btn--active' : ''
              }`}
            >
              Vùng trồng
            </button>
            <button
              type="button"
              onClick={() => navigate('/security')}
              className={`sc-switcher__btn ${
                activeTab === 'security' ? 'sc-switcher__btn--active' : ''
              }`}
            >
              Phân quyền RLS
            </button>
            <button
              type="button"
              onClick={() => navigate('/integrity')}
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
                ? 'Đã chuyển sang giao diện Tối'
                : 'Đã chuyển sang giao diện Sáng'
            )
          }}
          aria-label="Chuyển đổi giao diện Sáng / Tối"
        >
          {isDark ? 'Giao diện Sáng' : 'Giao diện Tối'}
        </button>
      </nav>

      <div
        className={`toast-banner ${toastVisible ? 'show' : ''}`}
        role="status"
        aria-live="polite"
      >
        <span>{toastMessage}</span>
      </div>
    </>
  )
}
