import { useState } from 'react'
import { hasPermission, ROLE_LABELS, type SessionUser } from '../types'

interface RbacPacketInspectorProps {
  user: SessionUser
  rbacProbeResult: string | null
  onRunProbe: () => Promise<void> | void
}

export function RbacPacketInspector({
  user,
  rbacProbeResult,
  onRunProbe,
}: RbacPacketInspectorProps) {
  const [animating, setAnimating] = useState(false)
  const canRead = hasPermission(user.role, 'farms:read')

  const handleInspect = async () => {
    setAnimating(true)
    try {
      await onRunProbe()
    } finally {
      // Allow animation to settle
      setTimeout(() => {
        setAnimating(false)
      }, 1200)
    }
  }

  const isDenied = rbacProbeResult?.startsWith('403')
  const isAllowed = rbacProbeResult?.startsWith('200')

  return (
    <div className="rbac-circuit-box panel-card" aria-label="Mô phỏng đường truyền gói tin bảo mật RBAC">
      <div className="circuit-header">
        <div>
          <span className="circuit-tag">
            <span className="circuit-pulse-dot" aria-hidden="true" />
            Kiểm soát Gói tin API &amp; Cô lập Đa tổ chức (N3-6)
          </span>
          <h3 className="circuit-title">Mô hình Tuyến Giao tiếp Bảo mật (Security Perimeter Flow)</h3>
        </div>

        <button
          type="button"
          className="ds-button ds-button-brand ds-button-sm"
          disabled={animating}
          onClick={() => void handleInspect()}
        >
          {animating ? 'Đang gửi gói tin...' : 'Phát xung kiểm tra GET /farms/'}
        </button>
      </div>

      <div className="circuit-stages-track">
        {/* Stage 1: Caller */}
        <div className="circuit-node">
          <div className="circuit-node-badge caller-badge">
            <span className="node-icon-symbol" aria-hidden="true">👤</span>
          </div>
          <strong className="circuit-node-name">Người gọi (Caller)</strong>
          <span className="circuit-node-role">{ROLE_LABELS[user.role]}</span>
          <code className="circuit-node-meta">{user.email}</code>
        </div>

        {/* Bus 1 */}
        <div className={`circuit-bus ${animating ? 'bus-active' : ''}`} aria-hidden="true">
          <span className="bus-wire" />
          <span className="bus-packet packet-1" />
        </div>

        {/* Stage 2: Gateway */}
        <div className="circuit-node">
          <div className="circuit-node-badge gateway-badge">
            <span className="node-icon-symbol" aria-hidden="true">⚡</span>
          </div>
          <strong className="circuit-node-name">FastAPI Gateway</strong>
          <span className="circuit-node-role">Xác thực Phiên</span>
          <code className="circuit-node-meta">Cookie + SHA-256</code>
        </div>

        {/* Bus 2 */}
        <div className={`circuit-bus ${animating ? 'bus-active' : ''}`} aria-hidden="true">
          <span className="bus-wire" />
          <span className="bus-packet packet-2" />
        </div>

        {/* Stage 3: RBAC Policy Engine */}
        <div
          className={`circuit-node ${
            isDenied ? 'node-blocked' : isAllowed ? 'node-passed' : ''
          }`}
        >
          <div
            className={`circuit-node-badge ${
              isDenied ? 'rbac-badge-danger' : 'rbac-badge'
            }`}
          >
            <span className="node-icon-symbol" aria-hidden="true">
              {isDenied ? '🛡️' : '🔑'}
            </span>
          </div>
          <strong className="circuit-node-name">RBAC Enforcer</strong>
          <span className="circuit-node-role">farms:read</span>
          <span
            className={`circuit-status-pill ${
              canRead ? 'pill-permitted' : 'pill-rejected'
            }`}
          >
            {canRead ? 'Cho phép' : 'Chặn (403)'}
          </span>
        </div>

        {/* Bus 3 */}
        <div
          className={`circuit-bus ${
            animating && canRead
              ? 'bus-active'
              : animating && !canRead
                ? 'bus-rejected'
                : ''
          }`}
          aria-hidden="true"
        >
          <span className="bus-wire" />
          {canRead && <span className="bus-packet packet-3" />}
        </div>

        {/* Stage 4: PostgreSQL RLS */}
        <div
          className={`circuit-node ${
            !canRead ? 'node-unreachable' : isAllowed ? 'node-passed' : ''
          }`}
        >
          <div className="circuit-node-badge db-badge">
            <span className="node-icon-symbol" aria-hidden="true">🗄️</span>
          </div>
          <strong className="circuit-node-name">PostgreSQL Engine</strong>
          <span className="circuit-node-role">FORCE RLS Policy</span>
          <code className="circuit-node-meta">Tenant: {user.organization_id.slice(0, 8)}...</code>
        </div>
      </div>

      {rbacProbeResult && (
        <div
          className={`circuit-outcome-box ${
            isAllowed ? 'outcome-success' : 'outcome-danger'
          }`}
          role="status"
        >
          <div className="outcome-icon" aria-hidden="true">
            {isAllowed ? '✅' : '🚫'}
          </div>
          <div className="outcome-text">
            <strong>{isAllowed ? '200 OK — Truy cập Hợp lệ' : '403 Forbidden — Chặn Theo Ma trận RBAC'}</strong>
            <p>{rbacProbeResult}</p>
          </div>
        </div>
      )}
    </div>
  )
}
