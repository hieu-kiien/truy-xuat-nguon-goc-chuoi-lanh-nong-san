import { useEffect } from 'react'
import { API_BASE_URL } from '../services/api'
import { ROLE_LABELS, type SessionUser } from '../types'
import type { WorkspaceTab } from './FarmWorkspace'

interface WorkspaceSidebarProps {
  user: SessionUser
  activeTab: WorkspaceTab
  sidebarOpen: boolean
  onCloseSidebar: () => void
  onTabChange: (tab: WorkspaceTab) => void
  onLogout: () => void
}

export function WorkspaceSidebar({
  user,
  activeTab,
  sidebarOpen,
  onCloseSidebar,
  onTabChange,
  onLogout,
}: WorkspaceSidebarProps) {
  useEffect(() => {
    const menuButton = document.querySelector<HTMLButtonElement>(
      '[aria-controls="dashboard-sidebar"]'
    )
    menuButton?.setAttribute('aria-expanded', String(sidebarOpen))
  }, [sidebarOpen])

  useEffect(() => {
    if (!sidebarOpen) return

    const mobileQuery = window.matchMedia('(max-width: 1024px)')
    if (!mobileQuery.matches) return

    const previousOverflow = document.body.style.overflow
    const dashboardMain = document.querySelector<HTMLElement>('.dashboard-main')
    document.body.style.overflow = 'hidden'
    if (dashboardMain) dashboardMain.inert = true

    const restoreMenuFocus = () => {
      window.requestAnimationFrame(() => {
        document
          .querySelector<HTMLButtonElement>('[aria-controls="dashboard-sidebar"]')
          ?.focus()
      })
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      onCloseSidebar()
      restoreMenuFocus()
    }

    const handleViewportChange = (event: MediaQueryListEvent) => {
      if (!event.matches) onCloseSidebar()
    }

    document.addEventListener('keydown', handleKeyDown)
    mobileQuery.addEventListener('change', handleViewportChange)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      mobileQuery.removeEventListener('change', handleViewportChange)
      document.body.style.overflow = previousOverflow
      if (dashboardMain) dashboardMain.inert = false
    }
  }, [sidebarOpen, onCloseSidebar])

  const selectTab = (tab: WorkspaceTab) => {
    onTabChange(tab)
    onCloseSidebar()
  }

  return (
    <aside
      id="dashboard-sidebar"
      className={`dashboard-sidebar ${
        sidebarOpen ? 'dashboard-sidebar-open' : ''
      }`}
      aria-label="Điều hướng chính"
    >
      <div>
        <div className="sidebar-brand">
          <div className="sidebar-brand-row">
            <div className="sidebar-brand-title">AgroChain</div>
            <span className="sidebar-brand-badge">N3-4..7</span>
          </div>
          <p className="sidebar-brand-sub" title={user.organization_name}>
            {user.organization_name}
          </p>
        </div>

        <nav className="sidebar-nav">
          <div>
            <div className="sidebar-section-label">Phân hệ Nghiệp vụ</div>
            <ul className="sidebar-nav-list">
              <li>
                <button
                  type="button"
                  onClick={() => selectTab('overview')}
                  aria-current={activeTab === 'overview' ? 'page' : undefined}
                  className={`dashboard-nav-item ${
                    activeTab === 'overview' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Tổng quan &amp; Vùng trồng</span>
                  <span className="nav-tag">N3-7</span>
                </button>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() => selectTab('security')}
                  aria-current={activeTab === 'security' ? 'page' : undefined}
                  className={`dashboard-nav-item ${
                    activeTab === 'security' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Phân quyền &amp; RLS</span>
                  <span className="nav-tag">N3-6</span>
                </button>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() => selectTab('integrity')}
                  aria-current={activeTab === 'integrity' ? 'page' : undefined}
                  className={`dashboard-nav-item ${
                    activeTab === 'integrity' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Chuỗi Hash Sự kiện</span>
                  <span className="nav-tag">N3-4</span>
                </button>
              </li>
              <li>
                <a
                  href={`${API_BASE_URL}/docs`}
                  target="_blank"
                  rel="noreferrer"
                  className="dashboard-nav-item"
                  aria-label="Mở OpenAPI Swagger trong tab mới"
                >
                  <span>OpenAPI Swagger</span>
                  <span className="nav-tag">API</span>
                </a>
              </li>
            </ul>
          </div>

          <div>
            <div className="sidebar-section-label">Trạng thái Hạ tầng</div>
            <div className="sidebar-specs-box">
              <div className="sidebar-spec-row">
                <span className="sidebar-spec-key">PostgreSQL RLS</span>
                <span className="sidebar-spec-val">ENABLED</span>
              </div>
              <div className="sidebar-spec-row">
                <span className="sidebar-spec-key">Tenant ID</span>
                <span className="sidebar-spec-val">
                  {user.organization_id.slice(0, 8)}...
                </span>
              </div>
              <div className="sidebar-spec-row">
                <span className="sidebar-spec-key">Session Auth</span>
                <span className="sidebar-spec-val">SHA-256</span>
              </div>
              <div className="sidebar-spec-row">
                <span className="sidebar-spec-key">Hash Chain</span>
                <span className="sidebar-spec-val">RFC 8785</span>
              </div>
            </div>
          </div>
        </nav>
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-user-card">
          <div className="sidebar-user-name">{user.full_name}</div>
          <div className="sidebar-user-meta" title={user.email}>
            {user.email}
          </div>
          <div className="sidebar-user-meta">
            Vai trò: <strong>{ROLE_LABELS[user.role]}</strong>
          </div>
        </div>

        <button
          type="button"
          className="ds-button ds-button-secondary ds-button-sm ds-button-block"
          onClick={onLogout}
        >
          Đăng xuất phiên
        </button>
      </div>
    </aside>
  )
}
