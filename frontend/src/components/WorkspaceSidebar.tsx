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
  const selectTab = (tab: WorkspaceTab) => {
    onTabChange(tab)
    onCloseSidebar()
  }

  return (
    <aside
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
                <span className="sidebar-spec-val">FORCE ON</span>
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
