import { useState, useEffect, useCallback, useRef } from 'react'
import { FarmWorkspace, type WorkspaceTab } from './components/FarmWorkspace'
import { LoginView } from './components/LoginView'
import { PublicInvitationView } from './components/PublicInvitationView'
import { PublicTracePage } from './components/PublicTracePage'
import { ApiError, checkHealth, getCurrentUser, logout } from './services/api'
import type { SessionUser } from './types'

const THEME_STORAGE_KEY = 'ttcs_theme'
const WORKSPACE_PATHS = new Set([
  '/lots',
  '/handovers',
  '/products',
  '/farms',
  '/security',
  '/audit',
  '/integrity',
  '/cold-chain-stats',
  '/cold-chain',
  '/cold-chain-ops',
  '/organization',
])
// Trang công khai: ai cũng xem được, không yêu cầu đăng nhập (S-48, N3-65, N3-30).
const PUBLIC_PATHS = new Set(['/truy-xuat', '/trace'])
const PUBLIC_INVITATION_PATHS = new Set(['/moi-dai-nhiep', '/invitations/accept'])
const PUBLIC_TRACE_CODE_PATH = /^\/(?:trace|truy-xuat)\/([^/?#]+)\/?$/i
const LOT_DETAIL_PATH = /^\/lots\/([0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/i

function isPublicInvitationPath(pathname: string): boolean {
  return PUBLIC_INVITATION_PATHS.has(pathname)
}

function isPublicPath(pathname: string): boolean {
  return (
    PUBLIC_PATHS.has(pathname) ||
    PUBLIC_TRACE_CODE_PATH.test(pathname) ||
    isPublicInvitationPath(pathname)
  )
}

function isWorkspacePath(pathname: string): boolean {
  return WORKSPACE_PATHS.has(pathname) || LOT_DETAIL_PATH.test(pathname)
}

function lotIdForPath(pathname: string): string | null {
  return LOT_DETAIL_PATH.exec(pathname)?.[1] ?? null
}

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
  if (url.origin !== window.location.origin || !isWorkspacePath(url.pathname)) {
    return null
  }
  return `${url.pathname}${url.search}${url.hash}`
}

function routeForTab(tab: WorkspaceTab): string {
  if (tab === 'overview') return '/farms'
  if (tab === 'handovers') return '/handovers'
  if (tab === 'products') return '/products'
  if (tab === 'security') return '/audit'
  if (tab === 'integrity') return '/integrity'
  if (tab === 'cold-chain-stats') return '/cold-chain-stats'
  if (tab === 'cold-chain') return '/cold-chain'
  if (tab === 'cold-chain-ops') return '/cold-chain-ops'
  if (tab === 'organization') return '/organization'
  return '/lots'
}

function tabForPath(pathname: string): WorkspaceTab {
  if (pathname === '/farms') return 'overview'
  if (pathname === '/handovers') return 'handovers'
  if (pathname === '/products') return 'products'
  if (pathname === '/security' || pathname === '/audit') return 'security'
  if (pathname === '/integrity') return 'integrity'
  if (pathname === '/cold-chain-stats') return 'cold-chain-stats'
  if (pathname === '/cold-chain') return 'cold-chain'
  if (pathname === '/cold-chain-ops') return 'cold-chain-ops'
  if (pathname === '/organization') return 'organization'
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
  const selectedLotId = lotIdForPath(location.pathname)
  const currentUserRef = useRef<SessionUser | null>(null)
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
    }, 2400)
  }, [])

  const navigate = useCallback((path: string, replace = false) => {
    const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`
    if (path === currentPath) return

    if (replace) {
      window.history.replaceState(null, '', path)
    } else {
      window.history.pushState(null, '', path)
    }
    setLocation(readLocation())
  }, [])

  const toggleTheme = useCallback(() => {
    setIsDark((prev) => {
      const next = !prev
      notify(next ? 'Đã chuyển sang giao diện Tối' : 'Đã chuyển sang giao diện Sáng')
      return next
    })
  }, [notify])

  useEffect(() => {
    const syncLocation = () => {
      let nextLocation = readLocation()
      if (
        !currentUserRef.current &&
        nextLocation.pathname !== '/login' &&
        !isPublicPath(nextLocation.pathname)
      ) {
        const returnTo =
          safeWorkspacePath(
            `${nextLocation.pathname}${nextLocation.search}${nextLocation.hash}`
          ) ?? '/lots'
        window.history.replaceState(null, '', loginPath(returnTo))
        nextLocation = readLocation()
      } else if (
        currentUserRef.current &&
        !isWorkspacePath(nextLocation.pathname) &&
        !isPublicPath(nextLocation.pathname)
      ) {
        window.history.replaceState(null, '', '/lots')
        nextLocation = readLocation()
      }
      setLocation(nextLocation)
    }
    const handleDocumentClick = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return
      }
      const target = event.target instanceof Element ? event.target.closest('a') : null
      if (!target || target.target || target.hasAttribute('download')) {
        return
      }
      const href = target.getAttribute('href')
      const workspaceTarget = safeWorkspacePath(href)
      if (!workspaceTarget) {
        return
      }
      event.preventDefault()
      navigate(workspaceTarget)
    }
    window.addEventListener('popstate', syncLocation)
    document.addEventListener('click', handleDocumentClick)
    return () => {
      window.removeEventListener('popstate', syncLocation)
      document.removeEventListener('click', handleDocumentClick)
    }
  }, [navigate])

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
      const startsOnPublicPage = isPublicPath(initialLocation.pathname)
      if (startsOnPublicPage) {
        if (active) setInitializing(false)
        return
      }
      try {
        await checkHealth()
        if (active) setBackendOnline(true)
      } catch {
        if (active) {
          setBackendOnline(false)
          if (initialLocation.pathname !== '/login' && !startsOnPublicPage) {
            navigate(loginPath(initialReturnTo), true)
          }
          setInitializing(false)
        }
        return
      }

      try {
        const user = await getCurrentUser()
        if (active) {
          currentUserRef.current = user
          setCurrentUser(user)
          if (
            initialLocation.pathname === '/' ||
            initialLocation.pathname === '/login'
          ) {
            const requestedReturnTo = safeWorkspacePath(
              new URLSearchParams(initialLocation.search).get('next')
            )
            navigate(requestedReturnTo ?? '/lots', true)
          } else if (
            !isWorkspacePath(initialLocation.pathname) &&
            !isPublicPath(initialLocation.pathname)
          ) {
            navigate('/lots', true)
          }
        }
      } catch {
        if (active) {
          currentUserRef.current = null
          setCurrentUser(null)
          if (initialLocation.pathname !== '/login' && !startsOnPublicPage) {
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

  useEffect(() => {
    if (backendOnline !== false) return
    let active = true
    const interval = window.setInterval(async () => {
      try {
        await checkHealth()
        if (active) {
          setBackendOnline(true)
        }
      } catch {
        // Still waking up
      }
    }, 5000)

    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [backendOnline])


  const handleLogout = async () => {
    try {
      await logout()
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 401)) {
        notify('Không thể đăng xuất. Vui lòng thử lại.')
        return
      }
    }
    currentUserRef.current = null
    setCurrentUser(null)
    navigate(loginPath('/lots'), true)
    notify('Đã đăng xuất khỏi phiên làm việc')
  }

  return (
    <>
      {initializing ? (
        <div className="login-hero section-pattern init-screen">
          <div className="panel-card init-card">
            <h2>AgroChain đang khởi tạo...</h2>
            <p className="panel-sub">
              Đang đồng bộ trạng thái phiên làm việc với máy chủ
            </p>
          </div>
        </div>
      ) : isPublicInvitationPath(location.pathname) ? (
        <PublicInvitationView />
      ) : isPublicPath(location.pathname) ? (
        // Trang công khai luôn hiển thị bản công khai, kể cả khi đang đăng nhập:
        // nhân viên mở link trên tem QR sẽ thấy đúng trải nghiệm của người tiêu dùng.
        <PublicTracePage />
      ) : currentUser ? (
        <FarmWorkspace
          key={`${currentUser.id}:${location.pathname}:${location.search}`}
          user={currentUser}
          activeTab={activeTab}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          onTabChange={(tab) => navigate(routeForTab(tab))}
          onLogout={() => void handleLogout()}
          onNotify={notify}
          selectedLotId={selectedLotId}
          onOpenLot={(lotId) => navigate(`/lots/${lotId}`)}
          onBackToLots={() => navigate('/lots')}
        />
      ) : (
        <LoginView
          backendOnline={backendOnline}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          onLoginSuccess={(user) => {
            currentUserRef.current = user
            setCurrentUser(user)
            const requestedReturnTo = safeWorkspacePath(
              new URLSearchParams(location.search).get('next')
            )
            navigate(requestedReturnTo ?? '/lots', true)
          }}
          onNotify={notify}
        />
      )}

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
