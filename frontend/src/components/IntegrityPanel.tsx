import { useEffect, useRef, useState } from 'react'
import {
  getIntegrityCheckHistory,
  getIntegrityScanSummary,
  getLots,
  verifyLotIntegrity,
} from '../services/api'
import type { IntegrityCheckRecord, IntegrityScanSummary, Lot } from '../types'

const ISSUE_LABELS: Record<string, string> = {
  missing_event: 'Thiếu sự kiện trong chuỗi',
  content_hash_mismatch: 'Nội dung sự kiện không khớp mã băm',
  previous_hash_mismatch: 'Liên kết đến sự kiện trước không khớp',
  downstream_unverified: 'Không thể xác minh các sự kiện tiếp theo',
}

interface IntegrityPanelProps {
  canReadLots: boolean
  canVerify: boolean
}

export function IntegrityPanel({ canReadLots, canVerify }: IntegrityPanelProps) {
  const [query, setQuery] = useState('')
  const [lots, setLots] = useState<Lot[]>([])
  const [lotId, setLotId] = useState('')
  const [loadingLots, setLoadingLots] = useState(true)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<IntegrityCheckRecord | null>(null)
  const [checkHistory, setCheckHistory] = useState<IntegrityCheckRecord[]>([])
  const [scanSummary, setScanSummary] = useState<IntegrityScanSummary | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)
  const checkRequestRef = useRef(0)

  useEffect(() => {
    if (!canVerify) return
    let active = true
    getIntegrityScanSummary()
      .then((summary) => {
        if (active) {
          setScanSummary(summary)
          setScanError(null)
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setScanSummary(null)
          setScanError(
            err instanceof Error
              ? err.message
              : 'Không thể tải tổng quan kiểm tra định kỳ.',
          )
        }
      })
    return () => {
      active = false
    }
  }, [canVerify])

  useEffect(() => {
    if (!canReadLots || !canVerify) return
    let active = true
    const timer = window.setTimeout(() => {
      getLots({ q: query, page_size: 30 })
        .then((page) => {
          if (!active) return
          setError(null)
          setLots(page.items)
          setLotId((current) =>
            current && page.items.some((lot) => lot.id === current)
              ? current
              : page.items[0]?.id ?? '',
          )
        })
        .catch((err: unknown) => {
          if (!active) return
          setLots([])
          setLotId('')
          setError(err instanceof Error ? err.message : 'Không thể tải lô hàng.')
        })
        .finally(() => { if (active) setLoadingLots(false) })
    }, 250)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [canReadLots, canVerify, query])

  useEffect(() => {
    if (!lotId) return
    let active = true
    getIntegrityCheckHistory(lotId)
      .then((checks) => { if (active) setCheckHistory(checks) })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải lịch sử kiểm tra.')
      })
    return () => { active = false }
  }, [lotId])

  const checkIntegrity = async () => {
    if (!lotId || checking) return
    const requestId = ++checkRequestRef.current
    const requestedLotId = lotId
    setChecking(true)
    setError(null)
    setReport(null)
    try {
      const check = await verifyLotIntegrity(requestedLotId)
      if (requestId !== checkRequestRef.current) return
      setReport(check)
      setCheckHistory((previous) => [check, ...previous.filter((item) => item.id !== check.id)].slice(0, 10))
    } catch (err) {
      if (requestId === checkRequestRef.current) {
        setError(err instanceof Error ? err.message : 'Không thể kiểm tra chuỗi sự kiện.')
      }
    } finally {
      if (requestId === checkRequestRef.current) setChecking(false)
    }
  }

  if (!canReadLots || !canVerify) {
    return (
      <section className="panel-card panel-box" role="status">
        Tài khoản này không có quyền kiểm tra tính toàn vẹn lô hàng.
      </section>
    )
  }

  return (
    <section className="panel-card panel-box integrity-check-panel">
      <header className="panel-head">
        <div>
          <h2>Kiểm tra tính toàn vẹn</h2>
          <p className="panel-sub">Chọn một lô để đối chiếu chuỗi sự kiện đã ghi nhận.</p>
        </div>
      </header>

      <div className="integrity-check-controls">
        <div className="form-field">
          <label htmlFor="integrity-lot-search">Tìm lô theo mã</label>
          <input
            id="integrity-lot-search"
            type="search"
            value={query}
            onChange={(event) => {
              checkRequestRef.current += 1
              setQuery(event.target.value)
              setLoadingLots(true)
              setLotId('')
              setReport(null)
              setCheckHistory([])
              setChecking(false)
              setError(null)
            }}
            placeholder="Nhập mã lô"
          />
        </div>
        <div className="form-field">
          <label htmlFor="integrity-lot">Lô hàng</label>
          <select
            id="integrity-lot"
            value={lotId}
            onChange={(event) => {
              checkRequestRef.current += 1
              setLotId(event.target.value)
              setReport(null)
              setCheckHistory([])
              setChecking(false)
              setError(null)
            }}
            disabled={loadingLots || lots.length === 0}
          >
            {lots.length === 0 && <option value="">{loadingLots ? 'Đang tải lô…' : 'Không có lô phù hợp'}</option>}
            {lots.map((lot) => (
              <option key={lot.id} value={lot.id}>
                {lot.lot_code ?? lot.id.slice(0, 8)} · {lot.product?.name ?? lot.name}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          className="ds-button ds-button-brand"
          onClick={() => void checkIntegrity()}
          disabled={!lotId || checking || loadingLots}
        >
          {checking ? 'Đang kiểm tra…' : 'Kiểm tra'}
        </button>
      </div>

      {error && <div className="alert-box alert-error" role="alert">{error}</div>}

      {canVerify && (
        <div className="integrity-scan-summary">
          <h3>Kiểm tra định kỳ toàn hệ thống</h3>
          {scanError && (
            <div className="alert-box alert-error" role="alert">{scanError}</div>
          )}
          {scanSummary && (
            <>
              <div className="integrity-scan-metrics">
                <div className="integrity-scan-metric">
                  <span className="integrity-scan-metric-label">Lần kiểm tra gần nhất</span>
                  <span className="integrity-scan-metric-value">
                    {scanSummary.last_checked_at
                      ? new Date(scanSummary.last_checked_at).toLocaleString('vi-VN', {
                          dateStyle: 'medium',
                          timeStyle: 'short',
                        })
                      : 'Chưa có'}
                  </span>
                </div>
                <div className="integrity-scan-metric">
                  <span className="integrity-scan-metric-label">Số lô đã kiểm tra</span>
                  <span className="integrity-scan-metric-value">
                    {scanSummary.checked_lot_count}
                  </span>
                </div>
                <div className="integrity-scan-metric">
                  <span className="integrity-scan-metric-label">Số lô đứt mạch</span>
                  <span className="integrity-scan-metric-value">
                    <span
                      className={`status-badge ${
                        scanSummary.broken_lot_count > 0 ? 'status-danger' : 'status-done'
                      }`}
                    >
                      {scanSummary.broken_lot_count}
                    </span>
                  </span>
                </div>
              </div>

              {scanSummary.broken_lots.length > 0 && (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th scope="col">Mã lô</th>
                        <th scope="col">Sự kiện đứt mạch</th>
                        <th scope="col">Số sự kiện</th>
                        <th scope="col">Thời điểm kiểm tra</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scanSummary.broken_lots.map((broken) => (
                        <tr key={`broken-${broken.lot_id}`}>
                          <td>{broken.lot_code ?? broken.lot_id.slice(0, 8)}</td>
                          <td>{broken.first_invalid_sequence ?? '—'}</td>
                          <td>{broken.checked_events}</td>
                          <td>
                            <time dateTime={broken.detected_at}>
                              {new Date(broken.detected_at).toLocaleString('vi-VN', {
                                dateStyle: 'medium',
                                timeStyle: 'short',
                              })}
                            </time>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {scanSummary.recent_alerts.length > 0 && (
                <div>
                  <h3>Cảnh báo gần đây</h3>
                  <div className="table-scroll">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th scope="col">Mã lô</th>
                          <th scope="col">Sự kiện đứt mạch</th>
                          <th scope="col">Số lỗi</th>
                          <th scope="col">Thời điểm phát hiện</th>
                        </tr>
                      </thead>
                      <tbody>
                        {scanSummary.recent_alerts.map((alert) => (
                          <tr key={alert.id}>
                            <td>{alert.lot_code ?? alert.lot_id.slice(0, 8)}</td>
                            <td>{alert.first_invalid_sequence ?? '—'}</td>
                            <td>{alert.issue_count}</td>
                            <td>
                              <time dateTime={alert.detected_at}>
                                {new Date(alert.detected_at).toLocaleString('vi-VN', {
                                  dateStyle: 'medium',
                                  timeStyle: 'short',
                                })}
                              </time>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
      {report && (
        <div className={`integrity-result ${report.valid ? 'integrity-result-valid' : 'integrity-result-invalid'}`} role="status">
          <strong>{report.valid ? 'Chuỗi sự kiện hợp lệ' : `Phát hiện sai lệch tại sự kiện ${report.first_invalid_sequence ?? 'không xác định'}`}</strong>
          <span>Đã kiểm tra {report.checked_events} sự kiện.</span>
          <time dateTime={report.checked_at}>
            Thời điểm kiểm tra: {new Date(report.checked_at).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' })}
          </time>
          {report.issues.length > 0 && (
            <ul>
              {report.issues.map((issue, index) => (
                <li key={`${issue.sequence_number}-${issue.kind}-${index}`}>
                  Sự kiện {issue.sequence_number}: {ISSUE_LABELS[issue.kind] ?? issue.kind}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {checkHistory.length > 0 && (
        <div className="integrity-check-history">
          <h3>Lần kiểm tra gần đây</h3>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr><th scope="col">Thời điểm</th><th scope="col">Kết quả</th><th scope="col">Sự kiện</th></tr>
              </thead>
              <tbody>
                {checkHistory.map((check) => (
                  <tr key={check.id}>
                    <td><time dateTime={check.checked_at}>{new Date(check.checked_at).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' })}</time></td>
                    <td><span className={`status-badge ${check.valid ? 'status-done' : 'status-danger'}`}>{check.valid ? 'Hợp lệ' : `Sai lệch tại sự kiện ${check.first_invalid_sequence ?? '—'}`}</span></td>
                    <td>{check.checked_events}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}
