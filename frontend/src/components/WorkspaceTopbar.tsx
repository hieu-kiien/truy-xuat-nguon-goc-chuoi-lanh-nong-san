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
        <h1 className="topbar-title">
          {activeTab === 'lots'
            ? 'Danh sách lô'
            : activeTab === 'products'
              ? 'Danh mục sản phẩm dùng chung'
              : activeTab === 'overview'
              ? 'Bảng điều khiển Vùng trồng & Giám sát Chuỗi lạnh'
              : activeTab === 'security'
                ? 'Ma trận Phân quyền RBAC & Cô lập Đa tổ chức (RLS)'
                : 'Kiểm chứng Toàn vẹn Chuỗi Sự kiện (SHA-256 + RFC 8785)'}
        </h1>
        <span className="topbar-divider">|</span>
        <span className="status-badge status-done">
          {ORG_TYPE_LABELS[user.organization_type]}
        </span>
      </div>

      <div className="topbar-actions">
        {activeTab === 'overview' && canReadFarms && (
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Lọc tên thửa, UUID, GPS..."
            className="dashboard-search"
            aria-label="Tìm kiếm vùng trồng"
          />
        )}

        {activeTab === 'overview' && canReadFarms && (
          <button
            type="button"
            className="ds-button ds-button-secondary ds-button-sm"
            onClick={onRefresh}
          >
            Làm mới
          </button>
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
