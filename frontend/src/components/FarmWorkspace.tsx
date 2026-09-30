import { useState, useEffect, useCallback, type FormEvent } from 'react'
import { createFarm, getFarms, updateFarm } from '../services/api'
import {
  hasPermission,
  ORG_TYPE_LABELS,
  ROLE_LABELS,
  ROLE_PERMISSIONS,
  type Farm,
  type SessionUser,
} from '../types'

interface FarmWorkspaceProps {
  user: SessionUser
}

interface PresetLocation {
  label: string
  name: string
  area_ha: string
  latitude: string
  longitude: string
}

const PRESET_LOCATIONS: PresetLocation[] = [
  {
    label: 'Mẫu Đà Lạt (Lâm Đồng)',
    name: 'Phân khu Rau hữu cơ Trại Mát',
    area_ha: '3.2500',
    latitude: '11.924850',
    longitude: '108.497210',
  },
  {
    label: 'Mẫu Mộc Châu (Sơn La)',
    name: 'Đồi Dâu tây Bản Áng Khu B',
    area_ha: '4.5000',
    latitude: '20.828640',
    longitude: '104.661520',
  },
  {
    label: 'Mẫu Tiền Giang (ĐBSCL)',
    name: 'Vùng trồng Xoài Cát Hòa Lộc Cái Bè',
    area_ha: '6.1000',
    latitude: '10.334910',
    longitude: '106.028450',
  },
]

export function FarmWorkspace({ user }: FarmWorkspaceProps) {
  const canReadFarms = hasPermission(user.role, 'farms:read')
  const canWriteFarms = hasPermission(user.role, 'farms:write')
  const grantedPermissions = ROLE_PERMISSIONS[user.role] ?? []

  const [farms, setFarms] = useState<Farm[]>([])
  const [loadingFarms, setLoadingFarms] = useState<boolean>(canReadFarms)
  const [listError, setListError] = useState<string | null>(null)

  const [editingFarm, setEditingFarm] = useState<Farm | null>(null)
  const [name, setName] = useState('')
  const [areaHa, setAreaHa] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [saving, setSaving] = useState(false)
  const [formFeedback, setFormFeedback] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  const [rbacProbeResult, setRbacProbeResult] = useState<string | null>(null)

  const refreshFarms = useCallback(async () => {
    if (!canReadFarms) return
    setLoadingFarms(true)
    setListError(null)
    try {
      const data = await getFarms()
      setFarms(data)
    } catch (err) {
      setListError(
        err instanceof Error ? err.message : 'Không thể tải danh sách vùng trồng'
      )
    } finally {
      setLoadingFarms(false)
    }
  }, [canReadFarms])

  useEffect(() => {
    if (!canReadFarms) return
    let cancelled = false

    getFarms()
      .then((data) => {
        if (!cancelled) {
          setFarms(data)
          setLoadingFarms(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setListError(
            err instanceof Error
              ? err.message
              : 'Không thể tải danh sách vùng trồng'
          )
          setLoadingFarms(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [canReadFarms])

  const resetForm = () => {
    setEditingFarm(null)
    setName('')
    setAreaHa('')
    setLatitude('')
    setLongitude('')
  }

  const startEdit = (farm: Farm) => {
    setEditingFarm(farm)
    setName(farm.name)
    setAreaHa(String(farm.area_ha))
    setLatitude(String(farm.latitude))
    setLongitude(String(farm.longitude))
    setFormFeedback(null)
  }

  const applyPreset = (preset: PresetLocation) => {
    setName(preset.name)
    setAreaHa(preset.area_ha)
    setLatitude(preset.latitude)
    setLongitude(preset.longitude)
    setFormFeedback(null)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setFormFeedback(null)

    try {
      const payload = {
        name: name.trim(),
        area_ha: areaHa.trim(),
        latitude: latitude.trim(),
        longitude: longitude.trim(),
      }

      if (editingFarm) {
        const updated = await updateFarm(editingFarm.id, payload)
        setFarms((prev) =>
          prev.map((item) => (item.id === updated.id ? updated : item))
        )
        setFormFeedback({
          type: 'success',
          message: `Đã cập nhật vùng trồng "${updated.name}" (Mã định danh giữ nguyên: ${updated.id}).`,
        })
      } else {
        const created = await createFarm(payload)
        setFarms((prev) => [...prev, created])
        setFormFeedback({
          type: 'success',
          message: `Đã khai báo vùng trồng mới "${created.name}".`,
        })
      }
      resetForm()
    } catch (err) {
      setFormFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Không thể lưu vùng trồng',
      })
    } finally {
      setSaving(false)
    }
  }

  const runForbiddenProbe = async () => {
    setRbacProbeResult('Đang gửi yêu cầu GET /api/v1/farms/ tới Backend...')
    try {
      await getFarms()
      setRbacProbeResult('Yêu cầu thành công.')
    } catch (err) {
      if (err instanceof Error) {
        setRbacProbeResult(
          `Backend đã chặn theo đúng thiết kế RBAC: ${err.message}`
        )
      }
    }
  }

  return (
    <div className="workspace-stack">
      <section className="card tenant-banner">
        <div className="tenant-grid">
          <div>
            <span className="meta-label">Tổ chức chủ quản (Tenant RLS)</span>
            <div className="meta-value">{user.organization_name}</div>
            <div className="meta-sub">
              Loại hình: {ORG_TYPE_LABELS[user.organization_type]} &bull; Mã tổ chức:{' '}
              <code>{user.organization_id}</code>
            </div>
          </div>

          <div>
            <span className="meta-label">Vai trò &amp; Quyền hạn được cấp (RBAC)</span>
            <div className="meta-value">
              {ROLE_LABELS[user.role]} (<code>{user.role}</code>)
            </div>
            <div className="permission-badges">
              {grantedPermissions.map((perm) => (
                <span key={perm} className="badge badge-permission">
                  {perm}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {!canReadFarms ? (
        <section className="card">
          <div className="card-header">
            <h2>Kiểm soát truy cập theo vai trò (RBAC)</h2>
            <p className="text-muted">
              Tài khoản hiện tại có vai trò <strong>{ROLE_LABELS[user.role]}</strong> (
              <code>{user.role}</code>), chỉ được cấp quyền{' '}
              <code>{grantedPermissions.join(', ')}</code> và không có quyền{' '}
              <code>farms:read</code> hoặc <code>farms:write</code>.
            </p>
          </div>

          <div className="rbac-demo-box">
            <p>
              Bạn có thể bấm nút bên dưới để gửi trực tiếp một yêu cầu{' '}
              <code>GET /api/v1/farms/</code> lên máy chủ Backend và kiểm chứng cơ chế chặn{' '}
              <code>403 Forbidden</code> của tầng bảo mật:
            </p>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={runForbiddenProbe}
            >
              Thử gọi API /api/v1/farms/ (Kiểm chứng chặn 403)
            </button>

            {rbacProbeResult && (
              <div className="alert alert-error rbac-probe-output" role="status">
                {rbacProbeResult}
              </div>
            )}
          </div>
        </section>
      ) : (
        <div className="workspace-columns">
          <section className="card">
            <div className="card-header-row">
              <div>
                <h2>Danh sách Vùng trồng &amp; Thửa đất</h2>
                <p className="text-muted">
                  Dữ liệu được cô lập tự động theo tổ chức{' '}
                  <strong>{user.organization_name}</strong> bằng PostgreSQL Row-Level Security
                </p>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void refreshFarms()}
                disabled={loadingFarms}
              >
                {loadingFarms ? 'Đang tải...' : 'Làm mới'}
              </button>
            </div>

            {listError && (
              <div className="alert alert-error" role="alert">
                {listError}
              </div>
            )}

            {loadingFarms ? (
              <p className="empty-state">Đang tải dữ liệu vùng trồng...</p>
            ) : farms.length === 0 ? (
              <p className="empty-state">
                Chưa có vùng trồng nào được khai báo cho tổ chức này.
              </p>
            ) : (
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Tên vùng trồng / Thửa đất</th>
                      <th>Diện tích (ha)</th>
                      <th>Tọa độ GPS (Vĩ độ, Kinh độ)</th>
                      <th>Thao tác</th>
                    </tr>
                  </thead>
                  <tbody>
                    {farms.map((farm) => (
                      <tr
                        key={farm.id}
                        className={
                          editingFarm?.id === farm.id ? 'row-editing' : undefined
                        }
                      >
                        <td>
                          <div className="farm-name">{farm.name}</div>
                          <div className="farm-id">
                            ID: <code>{farm.id}</code>
                          </div>
                        </td>
                        <td className="num-cell">{Number(farm.area_ha).toFixed(2)} ha</td>
                        <td>
                          <div>
                            <code>
                              {farm.latitude}, {farm.longitude}
                            </code>
                          </div>
                          <a
                            href={`https://www.google.com/maps?q=${farm.latitude},${farm.longitude}`}
                            target="_blank"
                            rel="noreferrer"
                            className="map-link"
                          >
                            Xem trên bản đồ
                          </a>
                        </td>
                        <td>
                          {canWriteFarms && (
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => startEdit(farm)}
                            >
                              Chỉnh sửa
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {canWriteFarms && (
            <section className="card">
              <div className="card-header">
                <h2>
                  {editingFarm
                    ? 'Cập nhật thông tin Vùng trồng'
                    : 'Khai báo Vùng trồng mới'}
                </h2>
                <p className="text-muted">
                  {editingFarm
                    ? `Đang chỉnh sửa mã định danh cố định: ${editingFarm.id}`
                    : 'Điền thông tin diện tích (> 0 ha) và tọa độ GPS hợp lệ'}
                </p>
              </div>

              {!editingFarm && (
                <div className="preset-bar">
                  <span className="preset-label">Điền nhanh dữ liệu mẫu:</span>
                  <div className="preset-buttons">
                    {PRESET_LOCATIONS.map((preset) => (
                      <button
                        key={preset.label}
                        type="button"
                        className="btn-chip"
                        onClick={() => applyPreset(preset)}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {formFeedback && (
                <div
                  className={`alert ${
                    formFeedback.type === 'success'
                      ? 'alert-success'
                      : 'alert-error'
                  }`}
                  role="status"
                >
                  {formFeedback.message}
                </div>
              )}

              <form onSubmit={handleSubmit} className="form-stack">
                <div className="form-field">
                  <label htmlFor="farm-name">
                    Tên vùng trồng / thửa đất <span className="required-mark">*</span>
                  </label>
                  <input
                    id="farm-name"
                    type="text"
                    required
                    maxLength={200}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="VD: Khu nhà kính Dâu tây A1"
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="farm-area">
                    Diện tích canh tác (ha) <span className="required-mark">*</span>
                  </label>
                  <input
                    id="farm-area"
                    type="number"
                    step="0.0001"
                    min="0.0001"
                    required
                    value={areaHa}
                    onChange={(e) => setAreaHa(e.target.value)}
                    placeholder="VD: 2.5000"
                  />
                </div>

                <div className="form-row-2">
                  <div className="form-field">
                    <label htmlFor="farm-lat">
                      Vĩ độ (Latitude: -90 đến 90) <span className="required-mark">*</span>
                    </label>
                    <input
                      id="farm-lat"
                      type="number"
                      step="0.000001"
                      min="-90"
                      max="90"
                      required
                      value={latitude}
                      onChange={(e) => setLatitude(e.target.value)}
                      placeholder="VD: 11.862450"
                    />
                  </div>

                  <div className="form-field">
                    <label htmlFor="farm-lng">
                      Kinh độ (Longitude: -180 đến 180){' '}
                      <span className="required-mark">*</span>
                    </label>
                    <input
                      id="farm-lng"
                      type="number"
                      step="0.000001"
                      min="-180"
                      max="180"
                      required
                      value={longitude}
                      onChange={(e) => setLongitude(e.target.value)}
                      placeholder="VD: 108.538120"
                    />
                  </div>
                </div>

                <div className="form-actions">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={saving}
                  >
                    {saving
                      ? 'Đang lưu...'
                      : editingFarm
                        ? 'Lưu cập nhật'
                        : 'Thêm vùng trồng'}
                  </button>

                  {editingFarm && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={resetForm}
                    >
                      Hủy chỉnh sửa
                    </button>
                  )}
                </div>
              </form>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
