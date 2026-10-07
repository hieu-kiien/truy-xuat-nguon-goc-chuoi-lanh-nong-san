import { hasPermission, ROLE_LABELS, type SessionUser } from '../types'
import type { WorkspaceTab } from './FarmWorkspace'

interface WorkspaceSidebarProps {
  user: SessionUser
  activeTab: WorkspaceTab
  sidebarOpen: boolean
  onCloseSidebar: () => void
  onTabChange: (tab: WorkspaceTab) => void
  onLogout: () => void
  pendingHandoverCount?: number | null
}

export function WorkspaceSidebar({
  user,
  activeTab,
  sidebarOpen,
  onCloseSidebar,
  onTabChange,
  onLogout,
  pendingHandoverCount,
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
          </div>
          <p className="sidebar-brand-sub" title={user.organization_name}>
            {user.organization_name}
          </p>
        </div>

        <nav className="sidebar-nav">
          <div>
            <div className="sidebar-section-label">Phân hệ Nghiệp vụ</div>
            <ul className="sidebar-nav-list">
              {hasPermission(user.role, 'lots:read') && <li>
                <button
                  type="button"
                  onClick={() => selectTab('lots')}
                  className={`dashboard-nav-item ${
                    activeTab === 'lots' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Danh sách lô</span>
                </button>
              </li>}
              {hasPermission(user.role, 'products:read') && <li>
                <button
                  type="button"
                  onClick={() => selectTab('products')}
                  className={`dashboard-nav-item ${
                    activeTab === 'products' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Sản phẩm</span>
                </button>
              </li>}
              {(hasPermission(user.role, 'handovers:create') ||
                hasPermission(user.role, 'handovers:resolve')) && <li>
                <button
                  type="button"
                  onClick={() => selectTab('handovers')}
                  className={`dashboard-nav-item ${
                    activeTab === 'handovers' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Bàn giao</span>
                  {pendingHandoverCount != null && pendingHandoverCount > 0 && (
                    <span className="handover-pending-count" aria-label={`${pendingHandoverCount} yêu cầu cần xác nhận`}>
                      {pendingHandoverCount}
                    </span>
                  )}
                </button>
              </li>}
              {hasPermission(user.role, 'farms:read') && <li>
                <button
                  type="button"
                  onClick={() => selectTab('overview')}
                  className={`dashboard-nav-item ${
                    activeTab === 'overview' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Vùng trồng</span>
                </button>
              </li>}
              {hasPermission(user.role, 'security:read') && <li>
                <button
                  type="button"
                  onClick={() => selectTab('security')}
                  className={`dashboard-nav-item ${
                    activeTab === 'security' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Phân quyền</span>
                </button>
              </li>}
              {hasPermission(user.role, 'events:verify') && <li>
                <button
                  type="button"
                  onClick={() => selectTab('integrity')}
                  className={`dashboard-nav-item ${
                    activeTab === 'integrity' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Tính toàn vẹn</span>
                </button>
              </li>}
            </ul>
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
