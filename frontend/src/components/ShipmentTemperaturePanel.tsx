import { useCallback, useEffect, useState } from 'react'
import { getShipmentReadings, getShipments } from '../services/api'
import type { Shipment, ShipmentTemperatureReading } from '../types'
import { HourlyAggregateList } from './HourlyAggregateList'

const EMPTY_READINGS: ShipmentTemperatureReading[] = []

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
    let active = true
    getShipmentReadings(shipmentId)
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
  }, [shipmentId])

  const readings =
    readingsState.id === shipmentId ? readingsState.items : EMPTY_READINGS

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
      </div>

      {loading && shipments.length === 0 && (
        <p role="status">Đang tải chuyến vận chuyển…</p>
      )}
      {!loading && shipments.length === 0 && (
        <p>Chưa có chuyến vận chuyển nào trong tổ chức của bạn.</p>
      )}

      {shipmentId && (
        <>
          <h3>Đã tổng hợp theo giờ</h3>
          <HourlyAggregateList shipmentId={shipmentId} />

          <h3>Lần đo gần đây</h3>
          {readings.length === 0 ? (
            <p>Không có lần đo thô nào được giữ lại.</p>
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
