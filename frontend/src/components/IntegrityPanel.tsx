import { useEffect, useState } from 'react'
import { getLots, verifyLotIntegrity } from '../services/api'
import type { IntegrityReport, Lot } from '../types'

const ISSUE_LABELS: Record<string, string> = {
  missing_event: 'Thiếu sự kiện trong chuỗi',
  content_hash_mismatch: 'Nội dung sự kiện không khớp mã băm',
  previous_hash_mismatch: 'Liên kết đến sự kiện trước không khớp',
  downstream_unverified: 'Không thể xác minh các sự kiện tiếp theo',
}

export function IntegrityPanel() {
  const [query, setQuery] = useState('')
  const [lots, setLots] = useState<Lot[]>([])
  const [lotId, setLotId] = useState('')
  const [loadingLots, setLoadingLots] = useState(true)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<IntegrityReport | null>(null)

  useEffect(() => {
    let active = true
    const timer = window.setTimeout(() => {
      setLoadingLots(true)
      getLots({ q: query, page_size: 30 })
        .then((page) => {
          if (!active) return
          setLots(page.items)
          setLotId((current) =>
            current && page.items.some((lot) => lot.id === current)
              ? current
              : page.items[0]?.id ?? '',
          )
        })
        .catch((err: unknown) => {
          if (active) setError(err instanceof Error ? err.message : 'Không thể tải lô hàng.')
        })
        .finally(() => { if (active) setLoadingLots(false) })
    }, 250)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [query])

  const checkIntegrity = async () => {
    if (!lotId || checking) return
    setChecking(true)
    setError(null)
    setReport(null)
    try {
      setReport(await verifyLotIntegrity(lotId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể kiểm tra chuỗi sự kiện.')
    } finally {
      setChecking(false)
    }
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
            onChange={(event) => { setQuery(event.target.value); setReport(null); setError(null) }}
            placeholder="Nhập mã lô"
          />
        </div>
        <div className="form-field">
          <label htmlFor="integrity-lot">Lô hàng</label>
          <select
            id="integrity-lot"
            value={lotId}
            onChange={(event) => { setLotId(event.target.value); setReport(null) }}
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
      {report && (
        <div className={`integrity-result ${report.valid ? 'integrity-result-valid' : 'integrity-result-invalid'}`} role="status">
          <strong>{report.valid ? 'Chuỗi sự kiện hợp lệ' : `Phát hiện sai lệch tại sự kiện ${report.first_invalid_sequence ?? 'không xác định'}`}</strong>
          <span>Đã kiểm tra {report.checked_events} sự kiện.</span>
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
    </section>
  )
}
