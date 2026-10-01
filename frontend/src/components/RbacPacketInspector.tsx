import { useEffect, useRef, useState } from 'react'
import { ROLE_LABELS, type SessionUser } from '../types'

export type ProbeResult = {
  kind: 'pending' | 'allowed' | 'denied' | 'error'
  status: number | null
  message: string
}

interface RbacPacketInspectorProps {
  user: SessionUser
  rbacProbeResult: ProbeResult | null
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

function resultToPhase(result: ProbeResult): ProbePhase | null {
  if (result.kind === 'allowed') return 'permitted'
  if (result.kind === 'denied') return 'rejected'
  if (result.kind === 'error') return 'error'
  return null
}

export function RbacPacketInspector({
  user,
  rbacProbeResult,
  onRunProbe,
}: RbacPacketInspectorProps) {
  const [phase, setPhase] = useState<ProbePhase>('idle')
  const [runId, setRunId] = useState(0)
  const timersRef = useRef<number[]>([])

  const clearTimers = () => {
    timersRef.current.forEach((id) => window.clearTimeout(id))
    timersRef.current = []
  }

  useEffect(() => {
    return () => {
      timersRef.current.forEach((id) => window.clearTimeout(id))
      timersRef.current = []
    }
  }, [])

  useEffect(() => {
    if (!rbacProbeResult) return

    if (rbacProbeResult.kind === 'pending') {
      if (phase !== 'dispatching' && phase !== 'gateway' && phase !== 'evaluating') {
        setPhase('evaluating')
      }
      return
    }

    if (phase === 'dispatching' || phase === 'gateway') return

    const nextPhase = resultToPhase(rbacProbeResult)
    if (!nextPhase || phase === nextPhase) return

    if (phase === 'evaluating') {
      const timer = window.setTimeout(() => {
        setPhase(nextPhase)
      }, 150)
      timersRef.current.push(timer)
      return
    }

    setPhase(nextPhase)
  }, [rbacProbeResult, phase])

  const handleInspect = () => {
    if (phase === 'dispatching' || phase === 'gateway' || phase === 'evaluating') {
      return
    }

    clearTimers()
    setRunId((current) => current + 1)
    setPhase('dispatching')

    const timer1 = window.setTimeout(() => {
      setPhase('gateway')
    }, 220)
    timersRef.current.push(timer1)

    const timer2 = window.setTimeout(() => {
      setPhase('evaluating')
      void onRunProbe()
    }, 460)
    timersRef.current.push(timer2)
  }

  const isBusy = phase === 'dispatching' || phase === 'gateway' || phase === 'evaluating'
  const isPermitted = phase === 'permitted'
  const isRejected = phase === 'rejected'
  const isError = phase === 'error'
  const showOutcome = Boolean(rbacProbeResult && rbacProbeResult.kind !== 'pending' && !isBusy)

  return (
    <div
      className="rbac-circuit-box panel-card"
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
        <div className="circuit-node">
          <div className="circuit-node-badge caller-badge">
            <span className="node-icon-symbol" aria-hidden="true">
              👤
            </span>
          </div>
          <strong className="circuit-node-name">Người gọi (Caller)</strong>
          <span className="circuit-node-role">{ROLE_LABELS[user.role]}</span>
          <code className="circuit-node-meta">{user.email}</code>
        </div>

        <div
          className={`circuit-bus ${
            phase === 'dispatching' || phase === 'gateway' || phase === 'evaluating' || isPermitted || isRejected
              ? 'bus-active'
              : ''
          }`}
          aria-hidden="true"
        >
          <span className="bus-wire" />
          <span key={`packet-1-${runId}`} className="bus-packet packet-1" />
        </div>

        <div className="circuit-node">
          <div className="circuit-node-badge gateway-badge">
            <span className="node-icon-symbol" aria-hidden="true">
              ⚡
            </span>
          </div>
          <strong className="circuit-node-name">FastAPI Gateway</strong>
          <span className="circuit-node-role">Xác thực Phiên</span>
          <code className="circuit-node-meta">Cookie + SHA-256</code>
        </div>

        <div
          className={`circuit-bus ${
            phase === 'gateway' || phase === 'evaluating' || isPermitted || isRejected
              ? 'bus-active'
              : ''
          }`}
          aria-hidden="true"
        >
          <span className="bus-wire" />
          <span key={`packet-2-${runId}`} className="bus-packet packet-2" />
        </div>

        <div className={`circuit-node ${isRejected ? 'node-blocked' : ''}`}>
          <div
            className={`circuit-node-badge ${
              isRejected ? 'rbac-badge-danger' : 'rbac-badge'
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
              isPermitted ? 'pill-permitted' : isRejected ? 'pill-rejected' : ''
            }`}
          >
            {isPermitted ? 'Cho phép' : isRejected ? 'Chặn (403)' : isError ? 'Lỗi kiểm tra' : 'Đang đợi...'}
          </span>
        </div>

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
          {isPermitted && (
            <span key={`packet-3-${runId}`} className="bus-packet packet-3" />
          )}
        </div>

        <div className={`circuit-node ${isRejected ? 'node-unreachable' : ''}`}>
          <div className="circuit-node-badge db-badge">
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

      {showOutcome && rbacProbeResult && (
        <div
          className={`circuit-outcome-box ${
            isPermitted ? 'outcome-success' : isRejected ? 'outcome-danger' : ''
          }`}
          role="status"
          aria-live="polite"
        >
          <div className="outcome-icon" aria-hidden="true">
            {isPermitted ? '✅' : isRejected ? '🚫' : '⚠️'}
          </div>
          <div className="outcome-text">
            <strong>
              {isPermitted
                ? '200 OK — Backend Cho phép Truy cập'
                : isRejected
                  ? '403 Forbidden — Backend Chặn Theo Ma trận RBAC'
                  : rbacProbeResult.status
                    ? `HTTP ${rbacProbeResult.status} — Lỗi khi Thẩm tra`
                    : 'Lỗi kết nối khi Thẩm tra'}
            </strong>
            <p>{rbacProbeResult.message}</p>
          </div>
        </div>
      )}
    </div>
  )
}
