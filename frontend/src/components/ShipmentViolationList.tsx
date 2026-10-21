import { useCallback, useEffect, useState } from 'react'
import { getShipmentViolations } from '../services/api'
import type { ShipmentViolation } from '../types'

function formatTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

const VIOLATION_LABELS: Record<string, string> = {
  high_temp: 'Vượt ngưỡng trên',
  low_temp: 'Vượt ngưỡng dưới',
}

export function ShipmentViolationList({
  shipmentId,
}: {
  shipmentId: string
}) {
  const [violations, setViolations] = useState<ShipmentViolation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setViolations(await getShipmentViolations(shipmentId))
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải danh sách vi phạm.',
      )
    } finally {
      setLoading(false)
    }
  }, [shipmentId])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load()
    }, 150)
    return () => {
      window.clearTimeout(timer)
    }
  }, [load])

  if (loading) {
    return <p role="status">Đang tải vi phạm chuỗi lạnh…</p>
  }
  if (error) {
    return (
      <div className="alert-box alert-error" role="alert">
        {error}
      </div>
    )
  }
  if (violations.length === 0) {
    return <p>Chuyến này chưa có vi phạm nào được ghi nhận.</p>
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Loại</th>
            <th scope="col">Bắt đầu</th>
            <th scope="col">Kết thúc</th>
            <th scope="col">Thời lượng</th>
            <th scope="col">Nhiệt độ đỉnh</th>
          </tr>
        </thead>
        <tbody>
          {violations.map((violation, index) => (
            <tr key={violation.id ?? `${violation.started_at}-${index}`}>
              <td>{VIOLATION_LABELS[violation.violation_type] ?? violation.violation_type}</td>
              <td>{formatTime(violation.started_at)}</td>
              <td>
                {violation.is_settled
                  ? formatTime(violation.ended_at)
                  : 'Đang diễn ra'}
              </td>
              <td>{Math.round(violation.duration_minutes)} phút</td>
              <td>{violation.peak_temperature_celsius}°C</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
