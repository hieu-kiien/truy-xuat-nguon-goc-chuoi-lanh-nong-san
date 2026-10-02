import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import type { Farm, FarmPayload } from '../types'
import { Icon } from './Icons'

type AtlasMode = 'map' | 'list' | 'compare'
type FormState = 'closed' | 'create' | 'edit'

interface FarmAtlasProps {
  farms: Farm[]
  loading: boolean
  error: string | null
  canRead: boolean
  canWrite: boolean
  searchQuery: string
  onSearchChange: (query: string) => void
  onRefresh: () => void
  onSave: (id: string | null, payload: FarmPayload) => Promise<Farm>
}

const PRESETS = [
  { label: 'Mẫu Đà Lạt', name: 'Phân khu Rau hữu cơ Trại Mát', area_ha: '3.2500', latitude: '11.924850', longitude: '108.497210' },
  { label: 'Mẫu Mộc Châu', name: 'Đồi Dâu tây Bản Áng Khu B', area_ha: '4.5000', latitude: '20.828640', longitude: '104.661520' },
  { label: 'Mẫu Tiền Giang', name: 'Vùng trồng Xoài Cát Hòa Lộc Cái Bè', area_ha: '6.1000', latitude: '10.334910', longitude: '106.028450' },
]

const formatArea = (value: string) => `${Number(value).toFixed(2)} ha`

export function FarmAtlas({
  farms,
  loading,
  error,
  canRead,
  canWrite,
  searchQuery,
  onSearchChange,
  onRefresh,
  onSave,
}: FarmAtlasProps) {
  const [mode, setMode] = useState<AtlasMode>('map')
  const [selectedId, setSelectedId] = useState<string | null>(farms[0]?.id ?? null)
  const [focusMap, setFocusMap] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const formOriginRef = useRef<HTMLElement | null>(null)
  const inspectorRef = useRef<HTMLElement>(null)
  const [copyStatus, setCopyStatus] = useState('')
  const [formState, setFormState] = useState<FormState>('closed')
  const [formError, setFormError] = useState<string | null>(null)
  const [formSuccess, setFormSuccess] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [compareIds, setCompareIds] = useState<string[]>([])
  const [draft, setDraft] = useState({ name: '', area_ha: '', latitude: '', longitude: '' })
  const firstFieldRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (formState !== 'closed') firstFieldRef.current?.focus()
  }, [formState])

  const filteredFarms = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase()
    if (!query) return farms
    return farms.filter((farm) =>
      [farm.name, farm.id, farm.latitude, farm.longitude]
        .some((value) => String(value).toLocaleLowerCase().includes(query))
    )
  }, [farms, searchQuery])

  const resolvedSelectedId = farms.some((farm) => farm.id === selectedId)
    ? selectedId
    : farms[0]?.id ?? null
  const selectedFarm = farms.find((farm) => farm.id === resolvedSelectedId) ?? null
  const editingFarm = formState === 'edit' ? farms.find((farm) => farm.id === editingId) ?? null : null
  const compareFarms = compareIds.map((id) => farms.find((farm) => farm.id === id)).filter((farm): farm is Farm => Boolean(farm))
  const totalArea = farms.reduce((sum, farm) => sum + (Number(farm.area_ha) || 0), 0)

  const bounds = useMemo(() => {
    if (!farms.length) return { minLat: 10, maxLat: 22, minLng: 103, maxLng: 110 }
    const latitudes = farms.map((farm) => Number(farm.latitude))
    const longitudes = farms.map((farm) => Number(farm.longitude))
    const latSpan = Math.max(...latitudes) - Math.min(...latitudes)
    const lngSpan = Math.max(...longitudes) - Math.min(...longitudes)
    const latPad = Math.max(latSpan * 0.18, 0.03)
    const lngPad = Math.max(lngSpan * 0.18, 0.03)
    return {
      minLat: Math.min(...latitudes) - latPad,
      maxLat: Math.max(...latitudes) + latPad,
      minLng: Math.min(...longitudes) - lngPad,
      maxLng: Math.max(...longitudes) + lngPad,
    }
  }, [farms])

  const closeForm = () => {
    setFormState('closed')
    if (formOriginRef.current?.isConnected) formOriginRef.current.focus()
    else inspectorRef.current?.focus()
  }

  const startCreate = () => {
    formOriginRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setMode('map')
    setEditingId(null)
    setDraft({ name: '', area_ha: '', latitude: '', longitude: '' })
    setFormError(null)
    setFormSuccess(null)
    setFormState('create')
  }

  const startEdit = (farm: Farm) => {
    formOriginRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setMode('map')
    setEditingId(farm.id)
    setSelectedId(farm.id)
    setDraft({ name: farm.name, area_ha: String(farm.area_ha), latitude: String(farm.latitude), longitude: String(farm.longitude) })
    setFormError(null)
    setFormSuccess(null)
    setFormState('edit')
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canWrite || saving) return
    if (formState === 'edit' && !editingId) { setFormError('Không xác định được bản ghi cần sửa.'); return }
    setSaving(true)
    setFormError(null)
    setFormSuccess(null)
    try {
      const saved = await onSave(formState === 'edit' ? editingId : null, {
        name: draft.name.trim(),
        area_ha: draft.area_ha.trim(),
        latitude: draft.latitude.trim(),
        longitude: draft.longitude.trim(),
      })
      setSelectedId(saved.id)
      closeForm()
      setFormSuccess(editingFarm ? `Đã cập nhật ${saved.name}. UUID được giữ nguyên.` : `Đã tạo ${saved.name}.`)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Không thể lưu bản ghi trang trại.')
    } finally {
      setSaving(false)
    }
  }

  const toggleCompare = (farm: Farm) => {
    setCompareIds((current) => {
      if (current.includes(farm.id)) return current.filter((id) => id !== farm.id)
      if (current.length >= 2) return [current[1], farm.id]
      return [...current, farm.id]
    })
  }

  if (!canRead) {
    return (
      <section className="view-stack" data-demo-target="atlas" aria-labelledby="atlas-title">
        <div className="view-heading"><p className="eyebrow">Mission 02 / Farm atlas</p><h1 id="atlas-title">Sổ địa lý vùng trồng.</h1></div>
        <div className="access-gate">
          <div className="gate-symbol"><Icon name="shield" size={26} /></div>
          <div><span className="micro-label">RBAC GATE / FARMS:READ</span><h2>Vai trò hiện tại không có quyền farms:read.</h2><p>Farm Atlas chỉ hiện dữ liệu sau khi request được cho phép bởi backend. Mở Security X-Ray để kiểm chứng GET thực tế.</p></div>
        </div>
      </section>
    )
  }

  return (
    <section className="view-stack" data-demo-target="atlas" aria-labelledby="atlas-title">
      <div className="view-heading view-heading-spread">
        <div><p className="eyebrow">Mission 02 / Farm atlas</p><h1 id="atlas-title">Sổ địa lý vùng trồng.</h1><p className="view-intro">Vị trí và diện tích đọc từ API, lọc theo tenant ở PostgreSQL RLS.</p></div>
        <div className="atlas-heading-actions">
          <span className="api-data-stamp"><i />DỮ LIỆU API · {farms.length} THỬA</span>
          <button type="button" className="icon-button" aria-label="Làm mới vùng trồng" onClick={onRefresh}><Icon name="refresh" size={17} /></button>
          {canWrite && <button type="button" className="button button-primary" onClick={startCreate}><Icon name="plus" size={16} />Thêm thửa</button>}
        </div>
      </div>

      <div className="atlas-toolbar">
        <div className="view-switch" role="group" aria-label="Chế độ Farm Atlas">
          {(['map', 'list', 'compare'] as const).map((nextMode) => (
            <button key={nextMode} type="button" aria-pressed={mode === nextMode} className={mode === nextMode ? 'view-switch-active' : ''} onClick={() => setMode(nextMode)}>
              <Icon name={nextMode === 'map' ? 'atlas' : nextMode === 'list' ? 'list' : 'compare'} size={16} />
              {nextMode === 'map' ? 'Bản đồ' : nextMode === 'list' ? 'Danh sách' : 'So sánh'}
            </button>
          ))}
        </div>
        <label className="search-field"><Icon name="search" size={16} /><span className="sr-only">Tìm theo tên, UUID hoặc tọa độ</span><input type="search" value={searchQuery} onChange={(event) => onSearchChange(event.target.value)} placeholder="Tên thửa, UUID, tọa độ…" /></label>
      </div>

      {error && <div className="notice notice-error" role="alert"><strong>Không thể tải vùng trồng.</strong><span>{error}</span><button type="button" className="text-action" onClick={onRefresh}>Thử lại</button></div>}
      {formSuccess && <div className="notice notice-success" role="status"><Icon name="check" size={16} /><span>{formSuccess}</span><button type="button" aria-label="Đóng thông báo" onClick={() => setFormSuccess(null)}><Icon name="close" size={15} /></button></div>}

      {mode === 'map' && (
        <div className="atlas-layout">
          <section className="spatial-panel atlas-map-panel" aria-label="Bản đồ tọa độ vùng trồng">
            <div className="canvas-heading"><div><span className="micro-label">COORDINATE FIELD / WGS84</span><h2>{filteredFarms.length} tọa độ đang hiển thị</h2></div><span className="map-scale-label">VỊ TRÍ TƯƠNG ĐỐI · KHÔNG CÓ BASEMAP</span></div>
            <div className={`atlas-map ${focusMap ? 'atlas-focus-map' : ''}`}>
              <div className="atlas-camera-controls"><button type="button" aria-pressed={focusMap} onClick={() => setFocusMap(!focusMap)}><Icon name="pin" size={16} />{focusMap ? 'Toàn vùng' : 'Theo tọa độ'}</button></div>
              <div className="atlas-camera" style={{ transform: focusMap && selectedFarm ? `translate(${(50 - (9 + (Number(selectedFarm.longitude) - bounds.minLng) / Math.max(bounds.maxLng - bounds.minLng, .01) * 82)) * 1.55}%, ${(50 - (10 + (1 - (Number(selectedFarm.latitude) - bounds.minLat) / Math.max(bounds.maxLat - bounds.minLat, .01)) * 77)) * 1.55}%) scale(1.55)` : 'translate(0,0) scale(1)' }}>
              <svg className="atlas-map-art" viewBox="0 0 760 500" role="img" aria-label="Lưới tọa độ, vị trí tương đối của các vùng trồng thuộc tenant hiện tại">
                <defs>
                  <pattern id="atlas-grid" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="currentColor" strokeOpacity=".11" strokeWidth="1" /></pattern>
                  <pattern id="field-hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(38)"><path d="M0 0v12" stroke="currentColor" strokeOpacity=".12" strokeWidth="1" /></pattern>
                </defs>
                <rect width="760" height="500" fill="url(#atlas-grid)" />
                <path d="M88 344c48-86 37-147 110-190 58-34 100-15 145-73 54-68 122-46 136 15 12 49 62 48 92 92 29 43 31 110 88 156-79 59-135 63-198 35-62-28-107 21-178 35-71 14-151-12-195-70z" fill="url(#field-hatch)" stroke="currentColor" strokeOpacity=".17" />
                <path d="M35 124h688M35 250h688M35 376h688M170 36v428M380 36v428M590 36v428" className="atlas-grid-major" />
                <text x="42" y="28" className="map-region">TENANT LAND REGISTER</text>
                <text x="42" y="485" className="map-coordinate">BOUNDS / {bounds.minLat.toFixed(2)}–{bounds.maxLat.toFixed(2)}°N · {bounds.minLng.toFixed(2)}–{bounds.maxLng.toFixed(2)}°E</text>
              </svg>
              {loading && <div className="map-loading" role="status">Đang đồng bộ vị trí từ API…</div>}
              {!loading && filteredFarms.map((farm) => {
                const latitude = Number(farm.latitude)
                const longitude = Number(farm.longitude)
                const x = 9 + ((longitude - bounds.minLng) / Math.max(bounds.maxLng - bounds.minLng, 0.01)) * 82
                const y = 10 + (1 - (latitude - bounds.minLat) / Math.max(bounds.maxLat - bounds.minLat, 0.01)) * 77
                const selected = resolvedSelectedId === farm.id
                return (
                  <button key={farm.id} type="button" className={`farm-marker ${selected ? 'farm-marker-selected' : ''}`} style={{ left: `${x}%`, top: `${y}%` }} aria-pressed={selected} aria-label={`Chọn ${farm.name}, ${farm.area_ha} hecta, tọa độ ${farm.latitude}, ${farm.longitude}`} disabled={saving} onClick={() => { setSelectedId(farm.id); if (formState === 'closed') setFocusMap(true) }} onFocus={() => { if (!saving) setSelectedId(farm.id) }}>
                    <span className="farm-marker-dot"><Icon name="pin" size={16} /></span><span className="farm-marker-label">{farm.name}</span>
                  </button>
                )
              })}
              </div>
              {!loading && filteredFarms.length === 0 && <div className="atlas-empty-map"><span className="crosshair-large"><Icon name="pin" size={23} /></span><strong>{farms.length ? 'Không tìm thấy thửa khớp.' : 'Chưa có thửa trong vùng tenant này.'}</strong><span>{canWrite ? 'Tạo thửa mới để đặt tọa độ đầu tiên.' : 'Danh sách được lọc bởi RLS cho organization hiện tại.'}</span></div>}
              {selectedFarm && formState === 'closed' && <div className="atlas-coord-readout"><span className="crosshair-mini" /><div><small>FOCUS / {selectedFarm.id.slice(0, 8).toUpperCase()}</small><strong>{Math.abs(Number(selectedFarm.latitude)).toFixed(6)}°{Number(selectedFarm.latitude) < 0 ? 'S' : 'N'} · {Math.abs(Number(selectedFarm.longitude)).toFixed(6)}°{Number(selectedFarm.longitude) < 0 ? 'W' : 'E'}</strong></div></div>}
            </div>
            <div className="atlas-map-footer"><span><i className="legend-point" /> {filteredFarms.length} vị trí · tenant hiện tại</span><span><i className="legend-area" /> {totalArea.toFixed(2)} ha trong {farms.length} thửa</span></div>
          </section>

          <aside ref={inspectorRef} tabIndex={-1} className="atlas-inspector" onKeyDown={(event) => { if (event.key === 'Escape' && formState !== 'closed' && !saving) { event.preventDefault(); closeForm() } }} aria-label="Thông tin vùng trồng đang chọn">
            {formState !== 'closed' ? (
              <div className="farm-form-panel">
                <div className="inspector-topline"><span className="micro-label">{formState === 'edit' ? 'UPDATE / FARM RECORD' : 'NEW / FARM RECORD'}</span><button type="button" className="icon-button icon-button-small" aria-label="Đóng biểu mẫu" disabled={saving} onClick={closeForm}><Icon name="close" size={15} /></button></div>
                <h2>{formState === 'edit' ? 'Sửa vùng trồng.' : 'Ghim vùng mới.'}</h2>
                {editingFarm && <div className="identity-seal"><Icon name="shield" size={16} /><span><small>STABLE UUID · KHÔNG THAY ĐỔI</small><code title={editingFarm.id}>{editingFarm.id}</code></span></div>}
                {formState === 'create' && <div className="preset-row"><span>Mẫu:</span>{PRESETS.map((preset) => <button type="button" key={preset.label} onClick={() => setDraft({ name: preset.name, area_ha: preset.area_ha, latitude: preset.latitude, longitude: preset.longitude })}>{preset.label}</button>)}</div>}
                {formError && <div className="notice notice-error" role="alert">{formError}</div>}
                <form onSubmit={(event) => void submit(event)} className="farm-form">
                  <label htmlFor="atlas-farm-name">Tên vùng trồng <span>*</span><input ref={firstFieldRef} id="atlas-farm-name" type="text" required maxLength={200} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} autoComplete="off" /></label>
                  <label htmlFor="atlas-farm-area">Diện tích / ha <span>*</span><input id="atlas-farm-area" type="number" min="0.0001" step="0.0001" required value={draft.area_ha} onChange={(event) => setDraft({ ...draft, area_ha: event.target.value })} /></label>
                  <div className="form-field-pair">
                    <label htmlFor="atlas-farm-lat">Vĩ độ <span>*</span><input id="atlas-farm-lat" type="number" min="-90" max="90" step="0.000001" required value={draft.latitude} onChange={(event) => setDraft({ ...draft, latitude: event.target.value })} /></label>
                    <label htmlFor="atlas-farm-lng">Kinh độ <span>*</span><input id="atlas-farm-lng" type="number" min="-180" max="180" step="0.000001" required value={draft.longitude} onChange={(event) => setDraft({ ...draft, longitude: event.target.value })} /></label>
                  </div>
                  <p className="form-caption">Tọa độ WGS84 · diện tích lớn hơn 0 ha · giá trị được xác minh bởi backend.</p>
                  <div className="form-actions"><button type="submit" className="button button-primary" disabled={saving}><Icon name="check" size={16} />{saving ? 'Đang lưu…' : formState === 'edit' ? 'Lưu thay đổi' : 'Tạo vùng trồng'}</button><button type="button" className="button button-quiet" disabled={saving} onClick={closeForm}>Hủy</button></div>
                </form>
              </div>
            ) : selectedFarm ? (
              <div className="farm-detail-panel">
                <div className="inspector-topline"><span className="micro-label">FARM / RECORD</span><span className="state-pill state-normal">Tenant-visible</span></div>
                <h2>{selectedFarm.name}</h2>
                <svg className="farm-area-glyph" viewBox="0 0 200 100" role="img" aria-label="Biểu diễn tỷ trọng diện tích của vùng trồng trong tenant"><path d="M0 50h200M100 0v100" /><circle cx="100" cy="50" r={Math.max(8, Math.min(45, Math.sqrt(Number(selectedFarm.area_ha) / Math.max(totalArea, 1)) * 45))} /></svg><p className="area-glyph-caption">Diện tích tương đối · không phải ranh thửa</p>
                <p className="farm-area-display">{Number(selectedFarm.area_ha).toFixed(2)}<small> ha</small></p>
                <div className="identity-seal"><Icon name="shield" size={16} /><span><small>STABLE UUID</small><code title={selectedFarm.id}>{selectedFarm.id}</code></span></div>
                <button type="button" className="text-action uuid-copy" onClick={() => { if (!navigator.clipboard) { setCopyStatus('Trình duyệt không hỗ trợ sao chép.'); return }; void navigator.clipboard.writeText(selectedFarm.id).then(() => setCopyStatus('Đã sao chép UUID.'), () => setCopyStatus('Không thể sao chép; UUID đầy đủ ở trên.')) }}>Sao chép UUID <Icon name="layers" size={15} /></button><p className="copy-status" role="status">{copyStatus}</p>
                <dl className="detail-list"><div><dt>Vĩ độ / latitude</dt><dd>{selectedFarm.latitude}</dd></div><div><dt>Kinh độ / longitude</dt><dd>{selectedFarm.longitude}</dd></div><div><dt>Organization</dt><dd>{selectedFarm.organization_id.slice(0, 12)}…</dd></div></dl>
                <a className="button button-quiet map-external" href={`https://www.google.com/maps?q=${selectedFarm.latitude},${selectedFarm.longitude}`} target="_blank" rel="noreferrer"><Icon name="pin" size={15} />Mở tọa độ trên bản đồ</a>
                {canWrite && <button type="button" className="button button-primary button-block" onClick={() => startEdit(selectedFarm)}>Sửa bản ghi vùng trồng <Icon name="arrow" size={15} /></button>}
              </div>
            ) : (
              <div className="atlas-inspector-empty"><span className="crosshair-large"><Icon name="atlas" size={23} /></span><h2>Chọn một vị trí.</h2><p>Thông tin GPS và UUID sẽ xuất hiện tại đây.</p>{canWrite && <button type="button" className="button button-primary" onClick={startCreate}><Icon name="plus" size={16} />Tạo vùng trồng</button>}</div>
            )}
          </aside>
        </div>
      )}

      {mode === 'list' && (
        <section className="surface atlas-list-surface" aria-label="Danh sách vùng trồng">
          <div className="section-heading"><div><span className="micro-label">FARM RECORDS / API</span><h2>Danh mục vùng trồng</h2></div><span className="list-count">{filteredFarms.length} / {farms.length} bản ghi</span></div>
          {loading ? <p className="empty-copy" role="status">Đang đồng bộ danh sách vùng trồng…</p> : filteredFarms.length ? <div className="atlas-table-wrap"><table className="atlas-table"><thead><tr><th scope="col">Identity</th><th scope="col">Vùng trồng</th><th scope="col">Diện tích</th><th scope="col">Tọa độ GPS</th><th scope="col">Tỷ trọng</th><th scope="col"><span className="sr-only">Thao tác</span></th></tr></thead><tbody>{filteredFarms.map((farm) => <tr key={farm.id} className={resolvedSelectedId === farm.id ? 'farm-row-selected' : ''}><td><button type="button" className="table-select-button" aria-label={`Chọn ${farm.name}`} onClick={() => setSelectedId(farm.id)}><code title={farm.id}>{farm.id.slice(0, 8)}…</code></button></td><th scope="row">{farm.name}</th><td>{formatArea(farm.area_ha)}</td><td><code>{farm.latitude}, {farm.longitude}</code></td><td><div className="area-share"><span style={{ width: `${totalArea ? (Number(farm.area_ha) / totalArea) * 100 : 0}%` }} /><small>{totalArea ? Math.round(Number(farm.area_ha) / totalArea * 100) : 0}%</small></div></td><td>{canWrite && <button type="button" className="button button-table" onClick={() => startEdit(farm)}>Sửa</button>}</td></tr>)}</tbody></table></div> : <p className="empty-copy">Không có vùng trồng phù hợp với bộ lọc.</p>}
          {formState !== 'closed' && <div className="inline-edit-note"><Icon name="layers" size={17} /><span>Form {formState === 'edit' ? 'sửa' : 'tạo'} đang mở trong inspector của tab Bản đồ.</span><button type="button" className="text-action" onClick={() => setMode('map')}>Mở inspector <Icon name="arrow" size={14} /></button></div>}
        </section>
      )}

      {mode === 'compare' && (
        <section className="compare-layout" aria-label="So sánh vùng trồng">
          <div className="surface compare-picker"><div className="section-heading"><div><span className="micro-label">COMPARE / UP TO 2</span><h2>Chọn hai vùng trồng.</h2></div><span className="list-count">{compareIds.length} / 2</span></div><div className="compare-pick-list">{filteredFarms.map((farm) => <button key={farm.id} type="button" aria-pressed={compareIds.includes(farm.id)} className={compareIds.includes(farm.id) ? 'compare-pick compare-pick-active' : 'compare-pick'} onClick={() => toggleCompare(farm)}><span className="compare-pick-mark">{compareIds.includes(farm.id) ? <Icon name="check" size={15} /> : null}</span><span><strong>{farm.name}</strong><small>{farm.id.slice(0, 8)}… · {farm.latitude}, {farm.longitude}</small></span><b>{formatArea(farm.area_ha)}</b></button>)}</div></div>
          <div className="compare-result">
            {compareFarms.length === 2 ? <><div className="compare-result-heading"><p className="eyebrow">FIELD NOTES / SIDE BY SIDE</p><h2>Hai tọa độ, cùng tenant.</h2></div><div className="compare-cards">{compareFarms.map((farm, index) => <article key={farm.id} className="surface compare-card"><span className="compare-index">0{index + 1}</span><h3>{farm.name}</h3><strong>{formatArea(farm.area_ha)}</strong><p><Icon name="pin" size={14} />{farm.latitude}, {farm.longitude}</p><code title={farm.id}>{farm.id}</code></article>)}</div><div className="compare-delta"><span>Chênh lệch diện tích</span><strong>{Math.abs(Number(compareFarms[0].area_ha) - Number(compareFarms[1].area_ha)).toFixed(2)} ha</strong></div></> : <div className="surface compare-placeholder"><Icon name="compare" size={23} /><h2>Chọn thêm {2 - compareFarms.length} vùng.</h2><p>So sánh chỉ đọc dữ liệu đang hiển thị; không ghi thay đổi về backend.</p></div>}
          </div>
        </section>
      )}
    </section>
  )
}
