import { useEffect, useState } from 'react'
import { getColdChainViolationStats } from '../services/api'
import type { ColdChainViolationStats } from '../types'

const RANGE_PRESETS = [
  { label: '7 ngày', days: 7 },
  { label: '30 ngày', days: 30 },
  { label: '90 ngày', days: 90 },
  { label: 'Tất cả', days: 0 },
] as const

function isoStartOfDay(days: number): string | undefined {
  if (days <= 0) return undefined
  const moment = new Date()
  moment.setDate(moment.getDate() - days)
  moment.setHours(0, 0, 0, 0)
  return moment.toISOString()
}

function formatMinutes(minutes: number): string {
  const total = Math.round(minutes)
  const hours = Math.floor(total / 60)
  const rest = total % 60
  if (hours === 0) return `${rest} phút`
  if (rest === 0) return `${hours} giờ`
  return `${hours} giờ ${rest} phút`
}

export function ColdChainStatsPanel() {
  const [stats, setStats] = useState<ColdChainViolationStats | null>(null)
  const [rangeDays, setRangeDays] = useState<number>(30)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const timer = window.setTimeout(() => {
      setLoading(true)
      getColdChainViolationStats({ from: isoStartOfDay(rangeDays) })
        .then((payload) => {
          if (!active) return
          setStats(payload)
          setError(null)
        })
        .catch((err: unknown) => {
          if (!active) return
          setStats(null)
          setError(
            err instanceof Error
              ? err.message
              : 'Không thể tải thống kê vi phạm chuỗi lạnh.',
          )
        })
        .finally(() => {
          if (active) setLoading(false)
        })
    }, 150)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [rangeDays])

  return (
    <section className="panel-card panel-box cold-chain-stats-panel">
      <header className="panel-head">
        <div>
          <h2>Thống kê vi phạm chuỗi lạnh</h2>
          <p className="panel-sub">
            Số chuyến, số vi phạm, tổng thời lượng vi phạm và tỷ lệ chuyến có vi
            phạm của từng đơn vị vận chuyển. Khoảng thời gian tính theo thời điểm
            mở chuyến vận chuyển.
          </p>
        </div>
        <div className="cold-chain-stats-ranges">
          {RANGE_PRESETS.map((preset) => (
            <button
              key={preset.days}
              type="button"
              className={`ds-button ${
                rangeDays === preset.days ? 'ds-button-brand' : 'ds-button-secondary'
              } ds-button-sm`}
              onClick={() => setRangeDays(preset.days)}
              aria-pressed={rangeDays === preset.days}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </header>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}

      {loading && !stats && <p role="status">Đang tải thống kê…</p>}

      {stats && (
        <>
          <div className="integrity-check-history">
            <h3>Tổng quan</h3>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Chỉ số</th>
                    <th scope="col">Giá trị</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Số chuyến vận chuyển</td>
                    <td>{stats.total_shipment_count}</td>
                  </tr>
                  <tr>
                    <td>Số vi phạm</td>
                    <td>{stats.total_violation_count}</td>
                  </tr>
                  <tr>
                    <td>Tổng thời lượng vi phạm</td>
                    <td>{formatMinutes(stats.total_violation_minutes)}</td>
                  </tr>
                  <tr>
                    <td>Tỷ lệ chuyến có vi phạm</td>
                    <td>{stats.violation_shipment_rate.toFixed(2)}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <h3>Bảng theo đơn vị vận chuyển</h3>
          {stats.carriers.length === 0 ? (
            <p role="status">Chưa có chuyến vận chuyển nào trong khoảng thời gian này.</p>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Đơn vị vận chuyển</th>
                    <th scope="col">Số chuyến</th>
                    <th scope="col">Số vi phạm</th>
                    <th scope="col">Tổng thời lượng</th>
                    <th scope="col">Tỷ lệ chuyến có vi phạm</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.carriers.map((carrier) => (
                    <tr key={carrier.carrier_organization_id}>
                      <td>{carrier.carrier_organization_name || carrier.carrier_organization_id}</td>
                      <td>{carrier.shipment_count}</td>
                      <td>
                        {carrier.violation_count}
                        {carrier.violation_count > 0 && (
                          <span className="panel-sub">
                            {' '}
                            (nhiệt cao {carrier.high_temp_violation_count}, nhiệt thấp{' '}
                            {carrier.low_temp_violation_count})
                          </span>
                        )}
                      </td>
                      <td>{formatMinutes(carrier.total_violation_minutes)}</td>
                      <td>
                        <span
                          className={`status-badge ${
                            carrier.violation_shipment_rate > 0 ? 'status-danger' : 'status-done'
                          }`}
                        >
                          {carrier.violation_shipment_rate.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}
