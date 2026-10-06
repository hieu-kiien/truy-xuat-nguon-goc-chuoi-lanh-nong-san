import { hasPermission, ROLE_LABELS, type SessionUser } from '../types'
import type { WorkspaceTab } from './FarmWorkspace'

interface WorkspaceSidebarProps {
  user: SessionUser
  activeTab: WorkspaceTab
  pendingHandoverCount: number
  sidebarOpen: boolean
  onCloseSidebar: () => void
  onTabChange: (tab: WorkspaceTab) => void
  onLogout: () => void
}

export function WorkspaceSidebar({
  user,
  activeTab,
  pendingHandoverCount,
  sidebarOpen,
  onCloseSidebar,
  onTabChange,
  onLogout,
}: WorkspaceSidebarProps) {
  const canReadLots = hasPermission(user.role, 'lots:read')
  const canReadProducts = hasPermission(user.role, 'products:read')
  const canReadFarms = hasPermission(user.role, 'farms:read')
  const canManageSecurity = user.role === 'organization_admin' || user.role === 'system_admin'
  const canVerifyEvents = hasPermission(user.role, 'events:verify')
  const canCreateHandovers = hasPermission(user.role, 'handovers:create')

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
            <div className="sidebar-section-label">CÔNG VIỆC</div>
            <ul className="sidebar-nav-list">
              {canReadLots && <li>
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
              {canReadProducts && <li>
                <button
                  type="button"
                  onClick={() => selectTab('products')}
                  className={`dashboard-nav-item ${
                    activeTab === 'products' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Danh mục sản phẩm</span>
                </button>
              </li>}
              {canCreateHandovers && <li>
                <button
                  type="button"
                  onClick={() => selectTab('handovers')}
                  className={`dashboard-nav-item ${activeTab === 'handovers' ? 'dashboard-nav-item-active' : ''}`}
                >
                  <span>Bàn giao</span>
                  {pendingHandoverCount > 0 && <span className="handover-nav-count" aria-label={`${pendingHandoverCount} yêu cầu đang chờ`}>{pendingHandoverCount}</span>}
                </button>
              </li>}
              {canReadFarms && <li>
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
              {canManageSecurity && <li>
                <button
                  type="button"
                  onClick={() => selectTab('security')}
                  className={`dashboard-nav-item ${
                    activeTab === 'security' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Bảo mật</span>
                </button>
              </li>}
              {canVerifyEvents && <li>
                <button
                  type="button"
                  onClick={() => selectTab('integrity')}
                  className={`dashboard-nav-item ${
                    activeTab === 'integrity' ? 'dashboard-nav-item-active' : ''
                  }`}
                >
                  <span>Kiểm tra toàn vẹn</span>
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
