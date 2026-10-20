import { useCallback, useEffect, useState } from 'react'
import { getShipmentHourlyAggregates } from '../services/api'
import type { ShipmentHourlyAggregate } from '../types'

function formatTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function HourlyAggregateList({
  shipmentId,
}: {
  shipmentId: string
}) {
  const [aggregates, setAggregates] = useState<ShipmentHourlyAggregate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setAggregates(await getShipmentHourlyAggregates(shipmentId))
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải chuỗi tổng hợp.',
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
    return <p role="status">Đang tải chuỗi tổng hợp…</p>
  }
  if (error) {
    return (
      <div className="alert-box alert-error" role="alert">
        {error}
      </div>
    )
  }
  if (aggregates.length === 0) {
    return <p>Chưa có dữ liệu đã tổng hợp.</p>
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Giờ</th>
            <th scope="col">Số lần đo</th>
            <th scope="col">Nhỏ nhất</th>
            <th scope="col">Lớn nhất</th>
            <th scope="col">Trung bình</th>
          </tr>
        </thead>
        <tbody>
          {aggregates.map((bucket) => (
            <tr key={bucket.id}>
              <td>{formatTime(bucket.bucket_start)}</td>
              <td>
                {bucket.is_gap ? (
                  <span className="status-badge status-danger">
                    Không có lần đo
                  </span>
                ) : (
                  bucket.reading_count
                )}
              </td>
              <td>{bucket.min_temperature_celsius ?? '—'}</td>
              <td>{bucket.max_temperature_celsius ?? '—'}</td>
              <td>{bucket.avg_temperature_celsius ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
