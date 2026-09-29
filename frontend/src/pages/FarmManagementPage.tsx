import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, createFarm, getFarms, updateFarm, type Farm, type FarmInput, type SessionUser } from '../services/api'

const EMPTY_FORM: FarmInput = {
  name: '',
  area_ha: '',
  latitude: '',
  longitude: '',
}

type FarmField = keyof FarmInput
type FieldErrors = Partial<Record<FarmField, string>>

function fieldError(field: string, message: string): string {
  if (field === 'name') return 'Tên thửa đất không được để trống.'
  if (field === 'area_ha') {
    return message.includes('Diện tích')
      ? message.replace(/^Value error,\s*/i, '')
      : 'Diện tích phải lớn hơn 0 ha và có tối đa 4 chữ số thập phân.'
  }
  if (field === 'latitude') return 'Vĩ độ phải nằm trong khoảng từ -90 đến 90.'
  if (field === 'longitude') return 'Kinh độ phải nằm trong khoảng từ -180 đến 180.'
  return message
}

function readValidationErrors(error: unknown): { fields: FieldErrors; general: string } {
  if (!(error instanceof ApiError) || !Array.isArray(error.detail)) {
    return { fields: {}, general: 'Không lưu được thửa đất. Vui lòng thử lại.' }
  }

  const fields: FieldErrors = {}
  for (const issue of error.detail as Array<{ loc?: unknown[]; msg?: string }>) {
    const field = issue.loc?.at(-1)
    if (typeof field === 'string' && field in EMPTY_FORM) {
      fields[field as FarmField] = fieldError(field, issue.msg ?? '')
    }
  }
  return {
    fields,
    general: Object.keys(fields).length ? '' : 'Dữ liệu gửi lên chưa hợp lệ.',
  }
}

function formatNumber(value: string | number, digits: number): string {
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: digits }).format(Number(value))
}

export default function FarmManagementPage({
  user,
  onLogout,
}: {
  user: SessionUser
  onLogout: () => void
}) {
  const [farms, setFarms] = useState<Farm[]>([])
  const [form, setForm] = useState<FarmInput>(EMPTY_FORM)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [generalError, setGeneralError] = useState('')
  const [listError, setListError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const canManageFarms = user.role === 'grower'

  useEffect(() => {
    let active = true
    getFarms()
      .then((records) => {
        if (active) setFarms(records)
      })
      .catch((error: unknown) => {
        if (!active) return
        setListError(
          error instanceof ApiError && error.status === 403
            ? 'Vai trò hiện tại không có quyền xem thửa đất.'
            : 'Không tải được danh sách thửa đất.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  function updateField(field: FarmField, value: string) {
    setForm((previous) => ({ ...previous, [field]: value }))
    setFieldErrors((previous) => ({ ...previous, [field]: undefined }))
    setGeneralError('')
  }

  function startEditing(farm: Farm) {
    setEditingId(farm.id)
    setForm({
      name: farm.name,
      area_ha: String(farm.area_ha),
      latitude: String(farm.latitude),
      longitude: String(farm.longitude),
    })
    setFieldErrors({})
    setGeneralError('')
    document.getElementById('farm-name')?.focus()
  }

  function cancelEditing() {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setFieldErrors({})
    setGeneralError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (savingRef.current) return
    savingRef.current = true
    setSaving(true)
    setFieldErrors({})
    setGeneralError('')

    const payload: FarmInput = {
      name: form.name.trim(),
      area_ha: Number(form.area_ha),
      latitude: Number(form.latitude),
      longitude: Number(form.longitude),
    }

    try {
      const saved = editingId
        ? await updateFarm(editingId, payload)
        : await createFarm(payload)
      setFarms((current) => {
        if (!editingId) return [...current, saved]
        return current.map((farm) => (farm.id === saved.id ? saved : farm))
      })
      cancelEditing()
    } catch (error) {
      const validation = readValidationErrors(error)
      setFieldErrors(validation.fields)
      setGeneralError(validation.general)
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/lots"><span aria-hidden="true">🌾</span> Nông sản chuỗi lạnh</a>
        <nav className="main-nav" aria-label="Điều hướng chính">
          <a href="/lots">Lô hàng</a>
          {canManageFarms && <a className="active" href="/farms" aria-current="page">Thửa đất</a>}
        </nav>
        <div className="user-menu">
          <span>{user.full_name}</span>
          <button className="quiet-button" onClick={onLogout} type="button">Đăng xuất</button>
        </div>
      </header>

      <div className="workspace-grid">
        <section className="farm-list-panel" aria-labelledby="farms-title">
          <p className="eyebrow">{user.organization_name}</p>
          <div className="section-heading">
            <div>
              <h1 id="farms-title">Thửa đất</h1>
              <p className="muted">Danh sách thửa đất thuộc tổ chức của bạn.</p>
            </div>
            <span className="count-pill">{farms.length} thửa</span>
          </div>

          {loading ? (
            <div className="list-message" role="status">Đang tải danh sách…</div>
          ) : listError ? (
            <div className="list-message" role="alert">{listError}</div>
          ) : farms.length === 0 ? (
            <div className="farm-empty-state">
              <span aria-hidden="true">🌱</span>
              <h2>Chưa có thửa đất</h2>
              <p>Khai báo thửa đầu tiên để gắn thông tin vùng trồng của tổ chức.</p>
            </div>
          ) : (
            <div className="farm-list">
              {farms.map((farm) => (
                <article className="farm-card" key={farm.id}>
                  <div className="farm-card-top">
                    <div className="farm-avatar" aria-hidden="true">🌿</div>
                    <button className="edit-button" onClick={() => startEditing(farm)} type="button">
                      Sửa thông tin
                    </button>
                  </div>
                  <h2>{farm.name}</h2>
                  <p className="farm-area">{formatNumber(farm.area_ha, 4)} <span>ha</span></p>
                  <div className="coordinates">
                    <span aria-hidden="true">⌖</span>
                    {formatNumber(farm.latitude, 6)}, {formatNumber(farm.longitude, 6)}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {canManageFarms ? <aside className="farm-form-card" aria-labelledby="farm-form-title">
          <div className="form-card-heading">
            <span className="form-icon" aria-hidden="true">{editingId ? '✎' : '＋'}</span>
            <div>
              <p className="eyebrow">THÔNG TIN VÙNG TRỒNG</p>
              <h2 id="farm-form-title">{editingId ? 'Cập nhật thửa đất' : 'Khai báo thửa đất'}</h2>
            </div>
          </div>
          <form className="farm-form" onSubmit={handleSubmit}>
            <div className="field-group">
              <label htmlFor="farm-name">Tên thửa đất</label>
              <input
                id="farm-name"
                className={fieldErrors.name ? 'invalid' : ''}
                value={form.name}
                onChange={(event) => updateField('name', event.target.value)}
                maxLength={200}
                required
                aria-invalid={Boolean(fieldErrors.name)}
                aria-describedby={fieldErrors.name ? 'farm-name-error' : undefined}
              />
              {fieldErrors.name && <small id="farm-name-error" className="field-error" role="alert">{fieldErrors.name}</small>}
            </div>
            <div className="field-group">
              <label htmlFor="farm-area">Diện tích (ha)</label>
              <input
                id="farm-area"
                className={fieldErrors.area_ha ? 'invalid' : ''}
                type="number"
                inputMode="decimal"
                value={form.area_ha}
                onChange={(event) => updateField('area_ha', event.target.value)}
                min="0.0001"
                step="0.0001"
                required
                aria-invalid={Boolean(fieldErrors.area_ha)}
                aria-describedby={fieldErrors.area_ha ? 'farm-area-error' : undefined}
              />
              {fieldErrors.area_ha && <small id="farm-area-error" className="field-error" role="alert">{fieldErrors.area_ha}</small>}
            </div>
            <div className="coordinate-fields">
              <div className="field-group">
                <label htmlFor="farm-latitude">Vĩ độ</label>
                <input
                  id="farm-latitude"
                  className={fieldErrors.latitude ? 'invalid' : ''}
                  type="number"
                  inputMode="decimal"
                  value={form.latitude}
                  onChange={(event) => updateField('latitude', event.target.value)}
                  min="-90"
                  max="90"
                  step="0.000001"
                  required
                  aria-invalid={Boolean(fieldErrors.latitude)}
                  aria-describedby={fieldErrors.latitude ? 'farm-latitude-error' : undefined}
                />
                {fieldErrors.latitude && <small id="farm-latitude-error" className="field-error" role="alert">{fieldErrors.latitude}</small>}
              </div>
              <div className="field-group">
                <label htmlFor="farm-longitude">Kinh độ</label>
                <input
                  id="farm-longitude"
                  className={fieldErrors.longitude ? 'invalid' : ''}
                  type="number"
                  inputMode="decimal"
                  value={form.longitude}
                  onChange={(event) => updateField('longitude', event.target.value)}
                  min="-180"
                  max="180"
                  step="0.000001"
                  required
                  aria-invalid={Boolean(fieldErrors.longitude)}
                  aria-describedby={fieldErrors.longitude ? 'farm-longitude-error' : undefined}
                />
                {fieldErrors.longitude && <small id="farm-longitude-error" className="field-error" role="alert">{fieldErrors.longitude}</small>}
              </div>
            </div>
            <p className="coordinate-help">Tọa độ dạng WGS84: vĩ độ và kinh độ dạng thập phân.</p>
            {generalError && <p className="form-error" role="alert">{generalError}</p>}
            <div className="form-actions">
              {editingId && <button className="secondary-button" onClick={cancelEditing} type="button">Hủy</button>}
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? 'Đang lưu…' : editingId ? 'Lưu thay đổi' : 'Lưu thửa đất'}
              </button>
            </div>
          </form>
        </aside> : <aside className="farm-form-card permission-message">
          <span aria-hidden="true">🔒</span>
          <h2>Không có quyền khai báo thửa đất</h2>
          <p>Chức năng này chỉ dành cho người dùng có vai trò nông hộ.</p>
        </aside>}
      </div>
    </main>
  )
}
