import { useEffect, useRef, useState, type FormEvent } from 'react'
import { consumeLot, getLocations, moveLot } from '../services/api'
import type { DistributionLocation, Lot } from '../types'

interface Props { lot: Lot; operation?: 'move' | 'consume'; onCompleted: () => Promise<void> }

export function LotLifecyclePanel({ lot, operation, onCompleted }: Props) {
  const [locations, setLocations] = useState<DistributionLocation[]>([])
  const [loading, setLoading] = useState(true)
  const [locationId, setLocationId] = useState('')
  const [note, setNote] = useState('')
  const [confirmConsume, setConfirmConsume] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const busy = useRef(false)
  useEffect(() => {
    let active = true
    getLocations().then(result => { if (active) setLocations(result) })
      .catch((err: unknown) => { if (active) setError(err instanceof Error ? err.message : 'Không thể tải địa điểm.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  const perform = async (operation: 'move' | 'consume') => {
    if (busy.current) return
    busy.current = true; setSaving(true); setError(null)
    try {
      if (operation === 'move') await moveLot(lot.id, locationId)
      else await consumeLot(lot.id, note.trim() || undefined)
      await onCompleted()
    } catch (err) { setError(err instanceof Error ? err.message : 'Không thể cập nhật lô.') }
    finally { busy.current = false; setSaving(false) }
  }
  const move = (event: FormEvent) => { event.preventDefault(); void perform('move') }
  return <section className="panel-card panel-box" aria-labelledby="lot-lifecycle-title">
    <h2 id="lot-lifecycle-title">{operation === 'consume' ? 'Ghi nhận tiêu thụ' : 'Di chuyển lô'}</h2>
    {error && <p className="alert-box alert-error" role="alert">{error}</p>}
    {operation !== 'consume' && <form onSubmit={move}>
      <fieldset className="transform-fields" disabled={saving || loading}>
        <legend>Di chuyển trong tổ chức</legend>
        <label className="form-field">Địa điểm nhận<select required value={locationId} onChange={event => setLocationId(event.target.value)}>
          <option value="">{loading ? 'Đang tải…' : 'Chọn cửa hàng / kho'}</option>
          {locations.filter(location => location.id !== lot.current_location_id).map(location => <option key={location.id} value={location.id}>{location.name} · {location.address}</option>)}
        </select></label>
        <button type="submit" className="ds-button ds-button-brand" disabled={!locationId}>{saving ? 'Đang xử lý…' : 'Di chuyển lô'}</button>
        {!loading && locations.length === 0 && <p>Thêm địa điểm trên trang danh sách lô trước khi di chuyển.</p>}
      </fieldset>
    </form>}
    {operation !== 'move' && <div className="transform-fields">
      <p>Đánh dấu đã tiêu thụ sẽ đưa khối lượng còn lại ({lot.remaining_quantity} {lot.product?.unit}) về 0 và kết thúc lô. Sau thao tác này, lô không thể di chuyển, bàn giao, tách, gộp hoặc ghi thêm sự kiện.</p>
      <label>Ghi chú tiêu thụ (không bắt buộc)<input maxLength={500} disabled={saving} value={note} onChange={event => setNote(event.target.value)} /></label>
      <label><span><input type="checkbox" checked={confirmConsume} disabled={saving} onChange={event => setConfirmConsume(event.target.checked)} /> Tôi xác nhận toàn bộ phần còn lại đã tiêu thụ và thao tác không thể hoàn tác.</span></label>
      <button type="button" className="ds-button ds-button-secondary" disabled={saving || !confirmConsume} onClick={() => void perform('consume')}>{saving ? 'Đang xử lý…' : 'Đánh dấu đã tiêu thụ'}</button>
    </div>}
  </section>
}
