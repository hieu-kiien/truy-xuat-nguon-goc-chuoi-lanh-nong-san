import { useState, useEffect } from 'react'
import { FarmWorkspace } from './components/FarmWorkspace'
import { LoginView } from './components/LoginView'
import { API_BASE_URL, checkHealth, getCurrentUser, logout } from './services/api'
import { ROLE_LABELS, type SessionUser } from './types'

export default function App() {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(null)
  const [initializing, setInitializing] = useState(true)

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
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <h1>Hệ thống Truy xuất Nguồn gốc Chuỗi lạnh Nông sản</h1>
            <div className="brand-meta">
              <span
                className={`status-dot ${
                  backendOnline === true
                    ? 'dot-online'
                    : backendOnline === false
                      ? 'dot-offline'
                      : 'dot-pending'
                }`}
              />
              <span>
                API:{' '}
                <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
                  {API_BASE_URL}/docs
                </a>
              </span>
            </div>
          </div>

          {currentUser && (
            <div className="user-bar">
              <div className="user-info">
                <div className="user-name">{currentUser.full_name}</div>
                <div className="user-sub">
                  {currentUser.organization_name} &bull;{' '}
                  {ROLE_LABELS[currentUser.role]}
                </div>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void handleLogout()}
              >
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="main-content">
        {backendOnline === false && (
          <div className="alert alert-error" role="alert">
            Không thể kết nối tới máy chủ Backend tại <code>{API_BASE_URL}</code>. Vui
            lòng kiểm tra lại trạng thái máy chủ.
          </div>
        )}

        {initializing ? (
          <div className="loading-panel">Đang khởi tạo phiên làm việc...</div>
        ) : currentUser ? (
          <FarmWorkspace key={currentUser.id} user={currentUser} />
        ) : (
          <LoginView onLoginSuccess={(user) => setCurrentUser(user)} />
        )}
      </main>
    </div>
  )
}
