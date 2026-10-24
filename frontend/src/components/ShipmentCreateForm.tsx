import { useCallback, useEffect, useState } from 'react'
import { createShipment, getLots } from '../services/api'
import type { Lot } from '../types'

export function ShipmentCreateForm({
  onCreated,
}: {
  onCreated?: (shipmentCode: string) => void
}) {
  const [lots, setLots] = useState<Lot[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [containerCode, setContainerCode] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const page = await getLots({ page_size: 50 })
      setLots(page.items.filter((lot) => lot.status === 'active'))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải danh sách lô.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load()
    }, 20)
    return () => {
      window.clearTimeout(timer)
    }
  }, [load])

  const toggleLot = (lotId: string) => {
    setSelected((current) =>
      current.includes(lotId)
        ? current.filter((id) => id !== lotId)
        : [...current, lotId],
    )
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (saving) return
    if (selected.length === 0) {
      setError('Chọn ít nhất một lô hàng cho chuyến vận chuyển.')
      return
    }
    if (containerCode.trim().length < 2) {
      setError('Mã thùng lạnh phải có ít nhất hai ký tự.')
      return
    }
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const shipment = await createShipment({
        container_code: containerCode.trim(),
        lot_ids: selected,
        notes: notes.trim() ? notes.trim() : null,
      })
      setNotice(`Đã mở chuyến vận chuyển ${shipment.shipment_code}.`)
      setSelected([])
      setContainerCode('')
      setNotes('')
      onCreated?.(shipment.shipment_code)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể mở chuyến vận chuyển.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section
      className="panel-card panel-box"
      aria-label="Khai báo chuyến vận chuyển lạnh"
    >
      <header className="panel-head">
        <div>
          <h2>Khai báo chuyến vận chuyển</h2>
          <p className="panel-sub">
            Một chuyến gắn nhiều lô hàng với một thùng lạnh. Ngưỡng chuỗi lạnh
            được chốt theo loại hàng ngay khi mở chuyến.
          </p>
        </div>
      </header>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert-box alert-success" role="status">
          {notice}
        </div>
      )}

      <form onSubmit={submit} className="integrity-check-controls">
        <div className="form-field">
          <label htmlFor="shipment-container-code">Mã thùng lạnh</label>
          <input
            id="shipment-container-code"
            type="text"
            required
            value={containerCode}
            onChange={(event) => setContainerCode(event.target.value)}
            placeholder="RF-2026-001"
          />
        </div>
        <div className="form-field">
          <label htmlFor="shipment-notes">Ghi chú</label>
          <input
            id="shipment-notes"
            type="text"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Tuyến đi, giờ giao dự kiến"
          />
        </div>
        <button
          type="submit"
          className="ds-button ds-button-brand"
          disabled={saving || loading}
        >
          {saving ? 'Đang mở…' : 'Mở chuyến vận chuyển'}
        </button>
      </form>

      <h3>Lô hàng ({selected.length} lô đã chọn)</h3>
      {loading && lots.length === 0 && <p role="status">Đang tải danh sách lô…</p>}
      {!loading && lots.length === 0 && (
        <p>Tổ chức của bạn chưa có lô đang hoạt động để đưa vào chuyến.</p>
      )}
      {lots.length > 0 && (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Chọn</th>
                <th scope="col">Mã lô</th>
                <th scope="col">Tên lô</th>
                <th scope="col">Nông sản</th>
                <th scope="col">Còn lại</th>
              </tr>
            </thead>
            <tbody>
              {lots.map((lot) => (
                <tr key={lot.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.includes(lot.id)}
                      onChange={() => toggleLot(lot.id)}
                      aria-label={`Chọn lô ${lot.lot_code ?? lot.name}`}
                    />
                  </td>
                  <td>{lot.lot_code ?? '—'}</td>
                  <td>{lot.name}</td>
                  <td>{lot.product?.name ?? '—'}</td>
                  <td>{lot.remaining_quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
