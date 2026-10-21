import { useCallback, useEffect, useState } from 'react'
import { ingestTelemetryReadings, getShipments } from '../services/api'
import { readingError } from '../utils/validation'
import type { Shipment, TelemetryIngestResult } from '../types'

function nowLocalInput(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60 * 1000
  return new Date(now.getTime() - offset).toISOString().slice(0, 16)
}

/** Check one reading before it is sent to the server. */
export function ShipmentReadingForm() {
  const [shipments, setShipments] = useState<Shipment[]>([])
  const [shipmentId, setShipmentId] = useState('')
  const [temperature, setTemperature] = useState('')
  const [recordedAt, setRecordedAt] = useState(nowLocalInput)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TelemetryIngestResult | null>(null)

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

  const shipment = shipments.find((item) => item.id === shipmentId)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (saving || !shipment) return
    const problem = readingError(temperature, recordedAt)
    if (problem) {
      setError(problem)
      return
    }
    const moment = new Date(recordedAt)
    setSaving(true)
    setError(null)
    setResult(null)
    try {
      const payload = await ingestTelemetryReadings({
        container_code: shipment.container_code,
        readings: [
          {
            recorded_at: moment.toISOString(),
            temperature_celsius: String(Number(temperature)),
          },
        ],
      })
      setResult(payload)
      setTemperature('')
      setRecordedAt(nowLocalInput())
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể ghi nhận số đo nhiệt độ.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section
      className="panel-card panel-box"
      aria-label="Ghi nhận số đo nhiệt độ của chuyến vận chuyển"
    >
      <header className="panel-head">
        <div>
          <h2>Ghi nhận số đo nhiệt độ</h2>
          <p className="panel-sub">
            Số đo được gắn vào chuyến theo mã thùng lạnh. Số đo trùng với số đã
            lưu sẽ bị bỏ qua, không ghi hai lần.
          </p>
        </div>
      </header>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}

      {result && (
        <div className="alert-box alert-success" role="status">
          <p>
            Đã ghi {result.ingested_count} lần đo, bỏ qua {result.duplicate_count}{' '}
            lần đo trùng. Chuyến hiện có {result.total_readings} lần đo.
          </p>
          {result.violations_detected > 0 && (
            <p>
              Phát hiện {result.violations_detected} lần vượt ngưỡng trong lần ghi
              này. Xem danh sách vi phạm ở màn hình chuỗi nhiệt độ.
            </p>
          )}
        </div>
      )}

      <form onSubmit={submit} className="integrity-check-controls">
        <div className="form-field">
          <label htmlFor="reading-shipment">Chuyến vận chuyển</label>
          <select
            id="reading-shipment"
            value={shipmentId}
            onChange={(event) => setShipmentId(event.target.value)}
            disabled={shipments.length === 0}
          >
            {shipments.length === 0 && (
              <option value="">Chưa có chuyến vận chuyển</option>
            )}
            {shipments.map((item) => (
              <option key={item.id} value={item.id}>
                {item.shipment_code} · {item.container_code} · {item.status}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="reading-temperature">Nhiệt độ (°C)</label>
          <input
            id="reading-temperature"
            type="number"
            step="0.1"
            required
            value={temperature}
            onChange={(event) => setTemperature(event.target.value)}
            placeholder="4.5"
          />
        </div>
        <div className="form-field">
          <label htmlFor="reading-recorded-at">Thời điểm ghi nhận</label>
          <input
            id="reading-recorded-at"
            type="datetime-local"
            required
            max={nowLocalInput()}
            value={recordedAt}
            onChange={(event) => setRecordedAt(event.target.value)}
          />
        </div>
        <button
          type="submit"
          className="ds-button ds-button-brand"
          disabled={saving || !shipment}
        >
          {saving ? 'Đang ghi…' : 'Ghi số đo'}
        </button>
      </form>

      {loading && shipments.length === 0 && (
        <p role="status">Đang tải chuyến vận chuyển…</p>
      )}
      {!loading && shipments.length === 0 && (
        <p>Chưa có chuyến vận chuyển nào để ghi số đo.</p>
      )}
    </section>
  )
}
