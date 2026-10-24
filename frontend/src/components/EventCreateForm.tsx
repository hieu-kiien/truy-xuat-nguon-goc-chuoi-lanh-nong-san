import { useRef, useState, type FormEvent } from 'react'
import { createEvent } from '../services/api'
import type { Lot } from '../types'

interface EventCreateFormProps {
  lot: Lot
  onCreated?: () => void
  onSuccess?: () => void
  onClose?: () => void
  onNotify?: (message: string) => void
}

export function EventCreateForm({
  lot,
  onCreated,
  onSuccess,
  onClose,
  onNotify,
}: EventCreateFormProps) {
  const [type, setType] = useState('packaging')
  const [note, setNote] = useState('')
  const [temperature, setTemperature] = useState('')
  const [place, setPlace] = useState(lot.current_location?.name ?? '')
  const [confirmed, setConfirmed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const busy = useRef(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!confirmed || busy.current || saved) return
    busy.current = true
    setSaving(true)
    setError('')
    try {
      await createEvent({
        lot_id: lot.id,
        event_type: type,
        payload: {
          ...(note.trim() ? { note: note.trim() } : {}),
          ...(place.trim() ? { location: place.trim() } : {}),
          ...(temperature ? { temperature_celsius: temperature } : {}),
        },
      })
      setSaved(true)
      onNotify?.('Đã ghi nhận sự kiện vào chuỗi băm bất biến SHA-256 thành công!')
      onSuccess?.()
      onCreated?.()
      if (onClose) {
        onClose()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể ghi nhận sự kiện.')
    } finally {
      busy.current = false
      setSaving(false)
    }
  }

  return (
    <section className="panel-card panel-box" aria-labelledby="event-create-title">
      <h2 id="event-create-title">Ghi nhận hoạt động chuỗi lạnh</h2>
      {error && <p className="alert-box alert-error" role="alert">{error}</p>}
      {saved && !onClose ? (
        <>
          <p role="status">Đã lưu sự kiện vào lịch sử lô.</p>
          <a className="ds-button ds-button-brand" href={`/lots/${lot.id}?view=history`}>
            Xem sự kiện vừa ghi
          </a>
        </>
      ) : (
        <form onSubmit={(event) => void submit(event)}>
          <fieldset className="transform-fields" disabled={saving}>
            <legend>Thông tin hoạt động</legend>
            <label>
              Hoạt động
              <select value={type} onChange={(event) => setType(event.target.value)}>
                <option value="packaging">Sơ chế / đóng gói</option>
                <option value="cold_storage">Bảo quản kho lạnh</option>
                <option value="transport">Vận chuyển</option>
                <option value="inspection">Kiểm tra chất lượng</option>
              </select>
            </label>
            <label>
              Địa điểm hoạt động (không bắt buộc)
              <input
                value={place}
                maxLength={500}
                placeholder="Ví dụ: Kho lạnh Sa Đéc"
                onChange={(event) => setPlace(event.target.value)}
              />
            </label>
            <label>
              Nhiệt độ đo được (°C, không bắt buộc)
              <input
                type="number"
                step="0.1"
                min="-273.1"
                max="1000"
                value={temperature}
                onChange={(event) => setTemperature(event.target.value)}
                placeholder="Ví dụ: 4.5"
              />
            </label>
            <label>
              Ghi chú (không bắt buộc)
              <textarea
                maxLength={1000}
                placeholder="Ghi công việc đã thực hiện và kết quả quan sát."
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </label>
            <label>
              <span>
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                />{' '}
                Tôi đã kiểm tra thông tin. Sự kiện đã lưu không thể sửa hoặc xóa.
              </span>
            </label>
            <div className="action-row" style={{ justifyContent: 'flex-end', marginTop: '0.5rem' }}>
              {onClose && (
                <button type="button" className="ds-button ds-button-secondary" onClick={onClose} disabled={saving}>
                  Hủy
                </button>
              )}
              <button type="submit" className="ds-button ds-button-brand" disabled={!confirmed}>
                {saving ? 'Đang lưu…' : 'Lưu sự kiện'}
              </button>
            </div>
          </fieldset>
        </form>
      )}
    </section>
  )
}
