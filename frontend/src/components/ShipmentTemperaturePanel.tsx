import { useCallback, useEffect, useState } from 'react'
import {
  getShipmentColdChainLimits,
  getShipmentReadings,
  getShipments,
} from '../services/api'
import type {
  Shipment,
  ShipmentColdChainLimits,
  ShipmentTemperatureReading,
} from '../types'
import { HourlyAggregateList } from './HourlyAggregateList'
import { ShipmentViolationList } from './ShipmentViolationList'

const EMPTY_READINGS: ShipmentTemperatureReading[] = []

const RANGES = [
  { days: 7, label: '7 ngày' },
  { days: 30, label: '30 ngày' },
  { days: 90, label: '90 ngày' },
  { days: 0, label: 'Tất cả' },
]

function formatTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function ShipmentTemperaturePanel() {
  const [shipments, setShipments] = useState<Shipment[]>([])
  const [shipmentId, setShipmentId] = useState('')
  const [readingsState, setReadings] = useState<{
    id: string
    items: ShipmentTemperatureReading[]
  }>({ id: '', items: EMPTY_READINGS })
  const [limitsState, setLimits] = useState<{
    id: string
    payload: ShipmentColdChainLimits
  } | null>(null)
  const [rangeDays, setRangeDays] = useState(30)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const list = await getShipments()
      setShipments(list)
      setShipmentId((current) => current || list[0]?.id || '')
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải chuyến vận chuyển.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load()
    }, 150)
    return () => {
      window.clearTimeout(timer)
    }
  }, [load])

  useEffect(() => {
    if (!shipmentId) {
      return
    }
    const from =
      rangeDays > 0
        ? new Date(Date.now() - rangeDays * 24 * 60 * 60 * 1000).toISOString()
        : undefined
    let active = true
    getShipmentReadings(shipmentId, { from })
      .then((raw) => {
        if (!active) return
        setReadings({ id: shipmentId, items: raw })
        setError(null)
      })
      .catch((err: unknown) => {
        if (!active) return
        setReadings({ id: shipmentId, items: [] })
        setError(
          err instanceof Error ? err.message : 'Không thể tải chuỗi nhiệt độ.',
        )
      })
    return () => {
      active = false
    }
  }, [shipmentId, rangeDays])

  useEffect(() => {
    if (!shipmentId) {
      return
    }
    let active = true
    getShipmentColdChainLimits(shipmentId)
      .then((payload) => {
        if (active) setLimits({ id: shipmentId, payload })
      })
      .catch(() => {
        if (active) setLimits(null)
      })
    return () => {
      active = false
    }
  }, [shipmentId])

  const readings =
    readingsState.id === shipmentId ? readingsState.items : EMPTY_READINGS
  const limits = limitsState?.id === shipmentId ? limitsState.payload : null

  return (
    <section
      className="panel-card panel-box"
      aria-label="Chuỗi nhiệt độ của chuyến vận chuyển"
    >
      <header className="panel-head">
        <div>
          <h2>Chuỗi nhiệt độ theo giờ</h2>
          <p className="panel-sub">
            Lần đo cũ hơn 30 ngày được gom thành giá trị tổng hợp theo giờ. Giờ
            không có lần đo nào vẫn hiện rõ để không nhầm là thiếu dữ liệu.
          </p>
        </div>
      </header>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}

      <div className="integrity-check-controls">
        <div className="form-field">
          <label htmlFor="shipment-temperature-select">Chuyến vận chuyển</label>
          <select
            id="shipment-temperature-select"
            value={shipmentId}
            onChange={(event) => setShipmentId(event.target.value)}
            disabled={shipments.length === 0}
          >
            {shipments.length === 0 && (
              <option value="">Chưa có chuyến vận chuyển</option>
            )}
            {shipments.map((shipment) => (
              <option key={shipment.id} value={shipment.id}>
                {shipment.shipment_code} · {shipment.container_code} ·{' '}
                {shipment.status}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="shipment-temperature-range">Khoảng thời gian</label>
          <select
            id="shipment-temperature-range"
            value={rangeDays}
            onChange={(event) => setRangeDays(Number(event.target.value))}
          >
            {RANGES.map((range) => (
              <option key={range.days} value={range.days}>
                {range.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {limits && (
        <div className="alert-box alert-info" role="status">
          <p>
            Ngưỡng hiệu lực: {limits.min_temp_celsius}°C đến{' '}
            {limits.max_temp_celsius}°C, phát hiện vi phạm sau{' '}
            {limits.delay_minutes} phút.{' '}
            {limits.from_snapshot
              ? 'Ngưỡng được chốt khi mở chuyến, đổi cấu hình sau này không áp dụng lại cho chuyến này.'
              : 'Chuyến chưa chốt ngưỡng, đang dùng cấu hình hiện tại của từng loại hàng.'}
          </p>
        </div>
      )}

      {loading && shipments.length === 0 && (
        <p role="status">Đang tải chuyến vận chuyển…</p>
      )}
      {!loading && shipments.length === 0 && (
        <p>Chưa có chuyến vận chuyển nào trong tổ chức của bạn.</p>
      )}

      {shipmentId && (
        <>
          <h3>Vi phạm chuỗi lạnh</h3>
          <ShipmentViolationList shipmentId={shipmentId} />

          <h3>Đã tổng hợp theo giờ</h3>
          <HourlyAggregateList shipmentId={shipmentId} />

          <h3>Lần đo gần đây</h3>
          {readings.length === 0 ? (
            <p>Không có lần đo thô nào trong khoảng thời gian đã chọn.</p>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Thời điểm</th>
                    <th scope="col">Nhiệt độ</th>
                  </tr>
                </thead>
                <tbody>
                  {readings.map((reading) => (
                    <tr key={reading.id}>
                      <td>{formatTime(reading.recorded_at)}</td>
                      <td>{reading.temperature_celsius}</td>
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
