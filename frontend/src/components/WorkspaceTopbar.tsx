import { ORG_TYPE_LABELS, type SessionUser } from '../types'
import type { WorkspaceTab } from './FarmWorkspace'

interface WorkspaceTopbarProps {
  user: SessionUser
  activeTab: WorkspaceTab
  canReadFarms: boolean
  searchQuery: string
  isDark: boolean
  onToggleSidebar: () => void
  onSearchChange: (value: string) => void
  onRefresh: () => void
  onToggleTheme: () => void
}

const TAB_TITLES: Record<WorkspaceTab, string> = {
  lots: 'Lô hàng',
  products: 'Sản phẩm',
  handovers: 'Bàn giao',
  overview: 'Vùng trồng',
  security: 'Phân quyền & bảo mật',
  integrity: 'Kiểm tra tính toàn vẹn',
}

export function WorkspaceTopbar({
  user,
  activeTab,
  canReadFarms,
  searchQuery,
  isDark,
  onToggleSidebar,
  onSearchChange,
  onRefresh,
  onToggleTheme,
}: WorkspaceTopbarProps) {
  const showOverviewActions = activeTab === 'overview' && canReadFarms

  return (
    <header className="dashboard-topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="dashboard-menu-btn"
          aria-label="Mở thanh điều hướng"
          onClick={onToggleSidebar}
        >
          Menu
        </button>
        <h1 className="topbar-title">{TAB_TITLES[activeTab] ?? 'Không gian làm việc'}</h1>
        <span className="topbar-divider">|</span>
        <span className="status-badge status-done">
          {ORG_TYPE_LABELS[user.organization_type]}
        </span>
      </div>

      <div className="topbar-actions">
        {showOverviewActions && (
          <>
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Lọc tên thửa, UUID, GPS..."
              className="dashboard-search"
              aria-label="Tìm kiếm vùng trồng"
            />
            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm"
              onClick={onRefresh}
            >
              Làm mới
            </button>
          </>
        )}


        <button
          type="button"
          className="ds-button ds-button-secondary ds-button-sm"
          onClick={onToggleTheme}
        >
          {isDark ? 'Sáng' : 'Tối'}
        </button>
      </div>
    </header>
  )
}
