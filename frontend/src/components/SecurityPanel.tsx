import {
  ORG_TYPE_LABELS,
  ROLE_LABELS,
  ROLE_PERMISSIONS,
  type RoleCode,
  type SessionUser,
} from '../types'

interface SecurityPanelProps {
  user: SessionUser
  rbacProbeResult: string | null
  onRunProbe: () => void
}

const ALL_ROLES: RoleCode[] = [
  'grower',
  'organization_admin',
  'inspector',
  'cooperative',
  'transporter',
  'distributor',
  'system_admin',
]

export function SecurityPanel({
  user,
  rbacProbeResult,
  onRunProbe,
}: SecurityPanelProps) {
  const grantedPermissions = ROLE_PERMISSIONS[user.role] ?? []

  return (
    <div className="dashboard-split-equal">
      <section className="panel-card panel-box">
        <div className="panel-head">
          <h2>Bảo mật và quyền truy cập</h2>
        </div>

        <div className="info-grid-2">
          <div className="info-item">
            <span className="info-item-label">Tài khoản xác thực</span>
            <strong className="info-item-value">{user.full_name}</strong>
            <div className="panel-sub">{user.email}</div>
          </div>

          <div className="info-item">
            <span className="info-item-label">Đơn vị</span>
            <strong className="info-item-value">{user.organization_name}</strong>
            <div className="panel-sub">
              Loại hình: {ORG_TYPE_LABELS[user.organization_type]}
            </div>
          </div>

          <div className="info-item">
            <span className="info-item-label">
              Mã đơn vị
            </span>
            <code>{user.organization_id}</code>
          </div>

          <div className="info-item">
            <span className="info-item-label">Quyền RBAC hiện tại</span>
            <div className="badge-row">
              {grantedPermissions.map((perm) => (
                <span key={perm} className="status-badge status-done">
                  {perm}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="action-row alert-spaced">
          <button
            type="button"
            className="ds-button ds-button-brand ds-button-sm"
            onClick={onRunProbe}
          >
            Kiểm tra quyền xem vùng trồng
          </button>
          <span className="panel-sub">
            Kiểm tra phản hồi 200 OK hoặc 403 Forbidden từ máy chủ
          </span>
        </div>

        {rbacProbeResult && (
          <div
            className={`alert-box alert-spaced ${
              rbacProbeResult.startsWith('200') ? 'alert-success' : 'alert-error'
            }`}
            role="status"
          >
            {rbacProbeResult}
          </div>
        )}
      </section>

      <section className="data-table-wrapper panel-card">
        <div className="data-table-header">
          <div>
            <h2 className="section-title">
              Quyền theo vai trò
            </h2>
            <p className="panel-sub">
              Các quyền được cấu hình cho từng vai trò trong ứng dụng.
            </p>
          </div>
        </div>

        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Mã Vai trò</th>
                <th>Tên Nghiệp vụ</th>
                <th>farms:read</th>
                <th>farms:write</th>
                <th>lots:read_all</th>
                <th>Phiên hiện tại</th>
              </tr>
            </thead>
            <tbody>
              {ALL_ROLES.map((roleCode) => {
                const perms = ROLE_PERMISSIONS[roleCode] ?? []
                const isCurrent = user.role === roleCode
                return (
                  <tr
                    key={roleCode}
                    className={isCurrent ? 'row-editing' : undefined}
                  >
                    <td>
                      <code>{roleCode}</code>
                    </td>
                    <th scope="row" className="cell-strong">
                      {ROLE_LABELS[roleCode]}
                    </th>
                    <td>
                      {perms.includes('farms:read') ? (
                        <span className="status-badge status-done">Cho phép</span>
                      ) : (
                        <span className="status-badge status-neutral">Chặn</span>
                      )}
                    </td>
                    <td>
                      {perms.includes('farms:write') ? (
                        <span className="status-badge status-done">Cho phép</span>
                      ) : (
                        <span className="status-badge status-neutral">Chặn</span>
                      )}
                    </td>
                    <td>
                      {perms.includes('lots:read_all') ? (
                        <span className="status-badge status-done">Toàn cục</span>
                      ) : (
                        <span className="status-badge status-neutral">—</span>
                      )}
                    </td>
                    <td>
                      {isCurrent ? (
                        <span className="status-badge status-done">Đang dùng</span>
                      ) : (
                        <span className="panel-sub">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
