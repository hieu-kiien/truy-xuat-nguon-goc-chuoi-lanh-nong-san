import { useState, useRef, useEffect } from 'react'
import { ROLE_LABELS, type SessionUser } from '../types'

interface RbacPacketInspectorProps {
  user: SessionUser
  rbacProbeResult: string | null
  onRunProbe: () => Promise<void> | void
}

export type ProbePhase =
  | 'idle'
  | 'dispatching'
  | 'gateway'
  | 'evaluating'
  | 'permitted'
  | 'rejected'
  | 'error'

export function RbacPacketInspector({
  user,
  rbacProbeResult,
  onRunProbe,
}: RbacPacketInspectorProps) {
  const [phase, setPhase] = useState<ProbePhase>('idle')
  const timersRef = useRef<number[]>([])

  // Cleanup all timers on unmount to prevent leaks
  useEffect(() => {
    return () => {
      timersRef.current.forEach((id) => window.clearTimeout(id))
      timersRef.current = []
    }
  }, [])

  // Sync animation phase strictly with the actual backend response
  useEffect(() => {
    if (phase === 'evaluating') {
      if (rbacProbeResult?.startsWith('200')) {
        const timer = window.setTimeout(() => {
          setPhase('permitted')
        }, 150)
        timersRef.current.push(timer)
      } else if (rbacProbeResult?.startsWith('403')) {
        const timer = window.setTimeout(() => {
          setPhase('rejected')
        }, 150)
        timersRef.current.push(timer)
      } else if (rbacProbeResult && !rbacProbeResult.startsWith('Đang')) {
        const timer = window.setTimeout(() => {
          setPhase('error')
        }, 150)
        timersRef.current.push(timer)
      }
    }
  }, [rbacProbeResult, phase])

  const handleInspect = () => {
    if (phase === 'dispatching' || phase === 'gateway' || phase === 'evaluating') {
      return
    }

    timersRef.current.forEach((id) => window.clearTimeout(id))
    timersRef.current = []

    // Step 1: Packet leaves caller
    setPhase('dispatching')

    // Step 2: Packet arrives at FastAPI gateway
    const timer1 = window.setTimeout(() => {
      setPhase('gateway')
    }, 220)
    timersRef.current.push(timer1)

    // Step 3: Packet reaches RBAC enforcer and fires real backend query
    const timer2 = window.setTimeout(() => {
      setPhase('evaluating')
      void onRunProbe()
    }, 460)
    timersRef.current.push(timer2)
  }

  const isBusy = phase === 'dispatching' || phase === 'gateway' || phase === 'evaluating'
  const isPermitted = phase === 'permitted'
  const isRejected = phase === 'rejected'

  return (
    <div
      className={`rbac-circuit-box panel-card ${
        isPermitted ? 'circuit-permitted' : isRejected ? 'circuit-rejected' : ''
      }`}
      aria-label="Mô phỏng đường truyền gói tin bảo mật RBAC"
    >
      <div className="circuit-header">
        <div>
          <span className="circuit-tag">
            <span className="circuit-pulse-dot" aria-hidden="true" />
            Kiểm soát Gói tin API &amp; Cô lập Đa tổ chức (N3-6)
          </span>
          <h3 className="circuit-title">
            Mô hình Tuyến Giao tiếp Bảo mật (Security Perimeter Flow)
          </h3>
        </div>

        <button
          type="button"
          className="ds-button ds-button-brand ds-button-sm"
          disabled={isBusy}
          onClick={handleInspect}
        >
          {isBusy ? 'Đang thẩm tra gói tin...' : 'Phát xung kiểm tra GET /farms/'}
        </button>
      </div>

      <div className="circuit-stages-track">
        {/* Stage 1: Caller */}
        <div className={`circuit-node ${phase === 'dispatching' ? 'node-active' : ''}`}>
          <div className="circuit-node-badge caller-badge">
            <span className="node-icon-symbol" aria-hidden="true">
              👤
            </span>
          </div>
          <strong className="circuit-node-name">Người gọi (Caller)</strong>
          <span className="circuit-node-role">{ROLE_LABELS[user.role]}</span>
          <code className="circuit-node-meta">{user.email}</code>
        </div>

        {/* Bus 1: Caller -> Gateway */}
        <div
          className={`circuit-bus ${
            phase === 'dispatching' || phase === 'gateway' || phase === 'evaluating' || isPermitted || isRejected
              ? 'bus-active'
              : ''
          }`}
          aria-hidden="true"
        >
          <span className="bus-wire" />
          <span className="bus-packet packet-1" />
        </div>

        {/* Stage 2: Gateway */}
        <div className={`circuit-node ${phase === 'gateway' ? 'node-active' : ''}`}>
          <div className="circuit-node-badge gateway-badge">
            <span className="node-icon-symbol" aria-hidden="true">
              ⚡
            </span>
          </div>
          <strong className="circuit-node-name">FastAPI Gateway</strong>
          <span className="circuit-node-role">Xác thực Phiên</span>
          <code className="circuit-node-meta">Cookie + SHA-256</code>
        </div>

        {/* Bus 2: Gateway -> RBAC */}
        <div
          className={`circuit-bus ${
            phase === 'gateway' || phase === 'evaluating' || isPermitted || isRejected
              ? 'bus-active'
              : ''
          }`}
          aria-hidden="true"
        >
          <span className="bus-wire" />
          <span className="bus-packet packet-2" />
        </div>

        {/* Stage 3: RBAC Policy Engine */}
        <div
          className={`circuit-node ${
            isRejected ? 'node-blocked' : isPermitted ? 'node-passed' : phase === 'evaluating' ? 'node-active' : ''
          }`}
        >
          <div
            className={`circuit-node-badge ${
              isRejected ? 'rbac-badge-danger' : isPermitted ? 'rbac-badge-success' : 'rbac-badge'
            }`}
          >
            <span className="node-icon-symbol" aria-hidden="true">
              {isRejected ? '🛡️' : '🔑'}
            </span>
          </div>
          <strong className="circuit-node-name">RBAC Enforcer</strong>
          <span className="circuit-node-role">farms:read</span>
          <span
            className={`circuit-status-pill ${
              isPermitted ? 'pill-permitted' : isRejected ? 'pill-rejected' : 'pill-neutral'
            }`}
          >
            {isPermitted ? 'Cho phép' : isRejected ? 'Chặn (403)' : 'Đang đợi...'}
          </span>
        </div>

        {/* Bus 3: RBAC -> PostgreSQL (Only active when backend verified 200 OK) */}
        <div
          className={`circuit-bus ${
            isPermitted
              ? 'bus-active'
              : isRejected
                ? 'bus-rejected'
                : ''
          }`}
          aria-hidden="true"
        >
          <span className="bus-wire" />
          {isPermitted && <span className="bus-packet packet-3" />}
        </div>

        {/* Stage 4: PostgreSQL RLS */}
        <div
          className={`circuit-node ${
            isRejected ? 'node-unreachable' : isPermitted ? 'node-passed' : ''
          }`}
        >
          <div className={`circuit-node-badge ${isPermitted ? 'db-badge-success' : 'db-badge'}`}>
            <span className="node-icon-symbol" aria-hidden="true">
              🗄️
            </span>
          </div>
          <strong className="circuit-node-name">PostgreSQL Engine</strong>
          <span className="circuit-node-role">FORCE RLS Policy</span>
          <code className="circuit-node-meta">
            Tenant: {user.organization_id.slice(0, 8)}...
          </code>
        </div>
      </div>

      {rbacProbeResult && (
        <div
          className={`circuit-outcome-box ${
            isPermitted ? 'outcome-success' : isRejected ? 'outcome-danger' : 'outcome-neutral'
          }`}
          role="status"
        >
          <div className="outcome-icon" aria-hidden="true">
            {isPermitted ? '✅' : isRejected ? '🚫' : 'ℹ️'}
          </div>
          <div className="outcome-text">
            <strong>
              {isPermitted
                ? '200 OK — Backend Cho phép Truy cập'
                : isRejected
                  ? '403 Forbidden — Backend Chặn Theo Ma trận RBAC'
                  : 'Kết quả Thẩm tra'}
            </strong>
            <p>{rbacProbeResult}</p>
          </div>
        </div>
      )}
    </div>
  )
}
