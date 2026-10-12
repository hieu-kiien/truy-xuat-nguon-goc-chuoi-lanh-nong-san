import { useEffect, useRef, useState, type FormEvent } from 'react'
import { createLocation, getLocations } from '../services/api'
import type { DistributionLocation } from '../types'
import { TaskLink } from './TaskLink'

export function LocationsPanel() {
  const task = new URLSearchParams(window.location.search).get('task') === 'locations'
  const [locations, setLocations] = useState<DistributionLocation[]>([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
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
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy.current) return
    busy.current = true; setSaving(true); setError(null)
    try {
      const location = await createLocation(name.trim(), address.trim())
      setLocations(current => [...current, location]); setName(''); setAddress('')
    } catch (err) { setError(err instanceof Error ? err.message : 'Không thể tạo địa điểm.') }
    finally { busy.current = false; setSaving(false) }
  }
  if (!task) return <section className="panel-card panel-box"><div className="panel-head"><div><h2>Địa điểm phân phối</h2><p className="panel-sub">Quản lý cửa hàng và kho của đơn vị trong trang riêng.</p></div><TaskLink href="/lots?task=locations" secondary>Quản lý địa điểm</TaskLink></div></section>
  return <section className="panel-card panel-box" aria-labelledby="locations-title">
    <a className="ds-button ds-button-secondary" href="/lots">← Danh sách lô</a>
    <h2 id="locations-title">Địa điểm phân phối</h2>
    <p className="panel-sub">Cửa hàng và kho thuộc tổ chức của bạn; chọn địa điểm khi di chuyển hoặc tách lô.</p>
    {error && <p className="alert-box alert-error" role="alert">{error}</p>}
    {loading ? <p aria-busy="true">Đang tải địa điểm…</p> : locations.length === 0 ? <p>Chưa có địa điểm phân phối.</p> :
      <ul>{locations.map(location => <li key={location.id}><strong>{location.name}</strong> · {location.address}</li>)}</ul>}
    <form onSubmit={event => void submit(event)}>
      <fieldset className="transform-fields" disabled={saving}>
        <legend>Thêm địa điểm</legend>
        <label>Tên cửa hàng / kho<input required maxLength={200} placeholder="Ví dụ: Kho rau Đà Lạt" value={name} onChange={event => setName(event.target.value)} /></label>
        <label>Địa chỉ<input required maxLength={500} placeholder="Số nhà, đường, phường/xã, tỉnh/thành phố" value={address} onChange={event => setAddress(event.target.value)} /></label>
        <button className="ds-button ds-button-brand" type="submit" disabled={!name.trim() || !address.trim()}>{saving ? 'Đang lưu…' : 'Thêm địa điểm'}</button>
      </fieldset>
    </form>
  </section>
}
