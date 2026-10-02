import { useState, useEffect, useCallback, useRef } from 'react'
import { FarmWorkspace, type WorkspaceTab } from './components/FarmWorkspace'
import { LoginView } from './components/LoginView'
import { checkHealth, getCurrentUser, logout } from './services/api'
import type { SessionUser } from './types'

const THEME_STORAGE_KEY = 'ttcs_theme'

export default function App() {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(null)
  const [initializing, setInitializing] = useState(true)
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('overview')
  const changeTab = useCallback((tab: WorkspaceTab) => setActiveTab(tab), [])
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

  const toggleTheme = useCallback(() => {
    setIsDark((prev) => {
      const next = !prev
      notify(next ? 'Đã chuyển sang giao diện Tối' : 'Đã chuyển sang giao diện Sáng')
      return next
    })
  }, [notify])

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

  useEffect(() => () => { if (toastTimerRef.current !== null) window.clearTimeout(toastTimerRef.current) }, [])

  const handleLogout = async () => {
    try {
      await logout()
      setCurrentUser(null)
      notify('Đã đăng xuất khỏi phiên làm việc')
    } catch (error) {
      notify(error instanceof Error ? `Chưa thể đăng xuất trên máy chủ: ${error.message}` : 'Không thể đăng xuất; vui lòng thử lại.')
    }
  }

  return (
    <>
      {initializing ? (
        <div className="init-screen">
          <div className="init-card"><span className="init-mark">AC</span><span className="micro-label">SECURE WORKSPACE</span>
            <h2>Đang khởi tạo AgroChain.</h2>
            <p>Đồng bộ phiên làm việc với máy chủ…</p>
          </div>
        </div>
      ) : currentUser ? (
        <FarmWorkspace
          key={currentUser.id}
          user={currentUser}
          backendOnline={backendOnline}
          activeTab={activeTab}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          onTabChange={changeTab}
          onSwitchUser={(nextUser) => setCurrentUser(nextUser)}
          onLogout={() => void handleLogout()}
          onNotify={notify}
        />
      ) : (
        <LoginView
          backendOnline={backendOnline}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          onLoginSuccess={(user) => {
            setCurrentUser(user)
            setActiveTab('overview')
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
