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
      <section className="sticker-panel panel-box">
        <div className="panel-head">
          <h2>Ngữ cảnh Phiên &amp; Cô lập Đa tổ chức (PostgreSQL RLS)</h2>
          <span className="status-badge status-done">FORCE RLS: BẬT</span>
        </div>

        <div className="info-grid-2">
          <div className="info-item">
            <span className="info-item-label">Tài khoản xác thực</span>
            <strong className="info-item-value">{user.full_name}</strong>
            <div className="panel-sub">{user.email}</div>
          </div>

          <div className="info-item">
            <span className="info-item-label">Đơn vị chủ quản (Tenant)</span>
            <strong className="info-item-value">{user.organization_name}</strong>
            <div className="panel-sub">
              Loại hình: {ORG_TYPE_LABELS[user.organization_type]}
            </div>
          </div>

          <div className="info-item">
            <span className="info-item-label">
              Biến phiên DB (app.current_organization)
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

        <pre className="code-block-compact">
          {`-- Chính sách PostgreSQL RLS áp dụng tự động trên bảng farms:
SET LOCAL app.current_organization = '${user.organization_id}';
CREATE POLICY farms_tenant_isolation ON farms
  USING (organization_id = current_setting('app.current_organization', true)::uuid);`}
        </pre>

        <div className="action-row alert-spaced">
          <button
            type="button"
            className="ds-button ds-button-brand ds-button-sm"
            onClick={onRunProbe}
          >
            Kiểm chứng thực tế: Gọi GET /api/v1/farms/
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

      <section className="data-table-wrapper sticker-panel">
        <div className="data-table-header">
          <div>
            <h2 className="section-title">
              Ma trận Phân quyền RBAC Toàn hệ thống (N3-6)
            </h2>
            <p className="panel-sub">
              Đối chiếu 7 vai trò nghiệp vụ và các quyền hạn được cấp phát
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
