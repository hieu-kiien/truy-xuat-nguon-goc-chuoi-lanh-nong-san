import { ROLE_PERMISSIONS, type SessionUser } from '../types'

interface SecurityPanelProps {
  user: SessionUser
  rbacProbeResult: string | null
  onRunProbe: () => void
}

export function SecurityPanel({
  user,
  rbacProbeResult,
  onRunProbe,
}: SecurityPanelProps) {
  const grantedPermissions = ROLE_PERMISSIONS[user.role] ?? []

  return (
    <div className="dashboard-panels">
      <section className="sticker-panel panel-box">
        <div className="panel-head">
          <h2>Thông tin Phiên &amp; Ngữ cảnh Đa tổ chức (RLS)</h2>
          <p className="panel-sub">
            Dữ liệu truy vấn được lọc tự động theo biến phiên của PostgreSQL
          </p>
        </div>

        <div className="info-stack">
          <div className="info-item">
            <span className="info-item-label">Người dùng đang xác thực</span>
            <strong className="info-item-value">
              {user.full_name} ({user.email})
            </strong>
          </div>

          <div className="info-item">
            <span className="info-item-label">
              Biến phiên PostgreSQL (app.current_organization)
            </span>
            <div>
              <code>{user.organization_id}</code>
            </div>
          </div>

          <div className="info-item">
            <span className="info-item-label">Quyền hạn RBAC được cấp</span>
            <div className="badge-row">
              {grantedPermissions.map((perm) => (
                <span key={perm} className="status-badge status-done">
                  {perm}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="sticker-panel panel-box">
        <div className="panel-head">
          <h2>Kiểm chứng Bảo mật API Thực tế</h2>
          <p className="panel-sub">
            Gửi yêu cầu trực tiếp tới endpoint <code>GET /api/v1/farms/</code> để
            kiểm tra phản hồi phân quyền từ máy chủ Backend.
          </p>
        </div>

        <button
          type="button"
          className="ds-button ds-button-brand ds-button-sm"
          onClick={onRunProbe}
        >
          Gửi yêu cầu kiểm tra quyền truy cập API
        </button>

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
    </div>
  )
}
