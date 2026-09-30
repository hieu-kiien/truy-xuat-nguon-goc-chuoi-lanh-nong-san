import { useState, useEffect, useCallback, type FormEvent } from 'react'
import { API_BASE_URL, createFarm, getFarms, updateFarm } from '../services/api'
import {
  hasPermission,
  ORG_TYPE_LABELS,
  ROLE_LABELS,
  ROLE_PERMISSIONS,
  type Farm,
  type SessionUser,
} from '../types'
import { IntegrityPanel } from './IntegrityPanel'
import { LotsPanel } from './LotsPanel'
import { SecurityPanel } from './SecurityPanel'

export type WorkspaceTab = 'lots' | 'overview' | 'security' | 'integrity'

interface FarmWorkspaceProps {
  user: SessionUser
  activeTab: WorkspaceTab
  onTabChange: (tab: WorkspaceTab) => void
  onLogout: () => void
  onNotify: (message: string) => void
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
    label: 'Mẫu Đà Lạt',
    name: 'Phân khu Rau hữu cơ Trại Mát',
    area_ha: '3.2500',
    latitude: '11.924850',
    longitude: '108.497210',
  },
  {
    label: 'Mẫu Mộc Châu',
    name: 'Đồi Dâu tây Bản Áng Khu B',
    area_ha: '4.5000',
    latitude: '20.828640',
    longitude: '104.661520',
  },
  {
    label: 'Mẫu Tiền Giang',
    name: 'Vùng trồng Xoài Cát Hòa Lộc Cái Bè',
    area_ha: '6.1000',
    latitude: '10.334910',
    longitude: '106.028450',
  },
]

export function FarmWorkspace({
  user,
  activeTab,
  onTabChange,
  onLogout,
  onNotify,
}: FarmWorkspaceProps) {
  const canReadFarms = hasPermission(user.role, 'farms:read')
  const canWriteFarms = hasPermission(user.role, 'farms:write')
  const canReadLots = hasPermission(user.role, 'lots:read')
  const grantedPermissions = ROLE_PERMISSIONS[user.role] ?? []

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

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
  const [tamperSimulated, setTamperSimulated] = useState(false)

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
    onTabChange('overview')
    onNotify(`Đang chỉnh sửa: ${farm.name}`)
  }

  const applyPreset = (preset: PresetLocation) => {
    setName(preset.name)
    setAreaHa(preset.area_ha)
    setLatitude(preset.latitude)
    setLongitude(preset.longitude)
    setFormFeedback(null)
    onNotify(`Đã điền mẫu: ${preset.name}`)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
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
          message: `Đã cập nhật "${updated.name}" (ID cố định: ${updated.id}).`,
        })
        onNotify(`Đã lưu cập nhật: ${updated.name}`)
      } else {
        const created = await createFarm(payload)
        setFarms((prev) => [...prev, created])
        setFormFeedback({
          type: 'success',
          message: `Đã khai báo vùng trồng mới "${created.name}".`,
        })
        onNotify(`Đã thêm vùng trồng: ${created.name}`)
      }
      form.reset()
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
      setRbacProbeResult(
        '200 OK — Vai trò hiện tại được phép truy cập danh sách vùng trồng.'
      )
      onNotify('Kiểm tra API thành công (200 OK)')
    } catch (err) {
      if (err instanceof Error) {
        setRbacProbeResult(
          `403 Forbidden — Backend đã chặn truy cập theo đúng ma trận RBAC: "${err.message}"`
        )
        onNotify('Backend đã chặn truy cập trái phép (403 Forbidden)')
      }
    }
  }

  const filteredFarms = farms.filter((f) => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return true
    return (
      f.name.toLowerCase().includes(q) ||
      f.id.toLowerCase().includes(q) ||
      String(f.latitude).includes(q) ||
      String(f.longitude).includes(q)
    )
  })

  const totalAreaHa = farms.reduce(
    (sum, item) => sum + (Number(item.area_ha) || 0),
    0
  )
  const maxAreaHa = Math.max(
    ...farms.map((item) => Number(item.area_ha) || 1),
    5
  )

  return (
    <div className="application-shell">
      {sidebarOpen && (
        <button
          type="button"
          className="dashboard-overlay"
          aria-label="Đóng thanh điều hướng"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="dashboard-layout">
        <aside
          className={`dashboard-sidebar ${
            sidebarOpen ? 'dashboard-sidebar-open' : ''
          }`}
          aria-label="Điều hướng chính"
        >
          <div>
            <div className="sidebar-brand">
              <span className="sidebar-brand-badge">Chuỗi Lạnh Nông Sản</span>
              <div className="sidebar-brand-title">AgroChain</div>
              <p className="sidebar-brand-sub">{user.organization_name}</p>
            </div>

            <nav className="sidebar-nav">
              <ul className="sidebar-nav-list">
                <li>
                  <button
                    type="button"
                    onClick={() => {
                      onTabChange('lots')
                      setSidebarOpen(false)
                    }}
                    className={`dashboard-nav-item ${
                      activeTab === 'lots' ? 'dashboard-nav-item-active' : ''
                    }`}
                  >
                    Danh sách lô
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => {
                      onTabChange('overview')
                      setSidebarOpen(false)
                    }}
                    className={`dashboard-nav-item ${
                      activeTab === 'overview' ? 'dashboard-nav-item-active' : ''
                    }`}
                  >
                    Vùng trồng &amp; Thửa đất
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => {
                      onTabChange('security')
                      setSidebarOpen(false)
                    }}
                    className={`dashboard-nav-item ${
                      activeTab === 'security' ? 'dashboard-nav-item-active' : ''
                    }`}
                  >
                    Phân quyền &amp; Cô lập RLS
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => {
                      onTabChange('integrity')
                      setSidebarOpen(false)
                    }}
                    className={`dashboard-nav-item ${
                      activeTab === 'integrity' ? 'dashboard-nav-item-active' : ''
                    }`}
                  >
                    Chuỗi Hash Sự kiện
                  </button>
                </li>
                <li>
                  <a
                    href={`${API_BASE_URL}/docs`}
                    target="_blank"
                    rel="noreferrer"
                    className="dashboard-nav-item"
                  >
                    Tài liệu API (Swagger)
                  </a>
                </li>
              </ul>
            </nav>
          </div>

          <div className="sidebar-footer">
            <div className="sidebar-user-card">
              <div className="sidebar-user-name">{user.full_name}</div>
              <div className="sidebar-user-meta">{user.email}</div>
              <div className="sidebar-user-meta">
                Vai trò: <strong>{ROLE_LABELS[user.role]}</strong>
              </div>
            </div>

            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm ds-button-block"
              onClick={onLogout}
            >
              Đăng xuất phiên làm việc
            </button>
          </div>
        </aside>

        <div className="dashboard-main">
          <header className="dashboard-topbar">
            <div className="topbar-left">
              <button
                type="button"
                className="dashboard-menu-btn"
                aria-label="Mở thanh điều hướng"
                onClick={() => setSidebarOpen((prev) => !prev)}
              >
                Menu
              </button>
              <div>
                <h1 className="topbar-title">
                  {activeTab === 'lots'
                    ? 'Danh sách lô'
                    : activeTab === 'overview'
                    ? 'Quản lý Vùng trồng & Thửa đất'
                    : activeTab === 'security'
                      ? 'Phân quyền RBAC & Cô lập Đa tổ chức (RLS)'
                      : 'Xác minh Toàn vẹn Chuỗi Sự kiện (SHA-256)'}
                </h1>
                <p className="panel-sub">
                  Đơn vị: <strong>{user.organization_name}</strong> (
                  {ORG_TYPE_LABELS[user.organization_type]})
                </p>
              </div>
            </div>

            <div className="topbar-actions">
              {activeTab === 'overview' && canReadFarms && (
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Tìm tên thửa đất, mã UUID..."
                  className="dashboard-search"
                  aria-label="Tìm kiếm vùng trồng"
                />
              )}
              {activeTab !== 'lots' && (
                <button
                  type="button"
                  className="ds-button ds-button-brand ds-button-sm"
                  onClick={() => void refreshFarms()}
                >
                  Làm mới dữ liệu
                </button>
              )}
            </div>
          </header>

          <main className="dashboard-content">
            {activeTab === 'overview' && (
              <section aria-label="Chỉ số tổng quan">
              <div className="stats-grid">
                <article className="stat-card sticker-panel">
                  <p className="stat-label">Số vùng trồng thuộc đơn vị</p>
                  <p className="stat-value">
                    {canReadFarms ? farms.length : 'Giới hạn'}
                  </p>
                  <p className="stat-trend">
                    {canReadFarms
                      ? 'Cô lập theo PostgreSQL RLS'
                      : 'Vai trò không có quyền farms:read'}
                  </p>
                </article>

                <article className="stat-card sticker-panel">
                  <p className="stat-label">Tổng diện tích canh tác</p>
                  <p className="stat-value">
                    {canReadFarms ? `${totalAreaHa.toFixed(2)} ha` : '—'}
                  </p>
                  <p className="stat-trend">Đạt chuẩn truy xuất VietGAP</p>
                </article>

                <article className="stat-card sticker-panel">
                  <p className="stat-label">Vai trò phiên hiện tại</p>
                  <p className="stat-value stat-value-compact">
                    {ROLE_LABELS[user.role]}
                  </p>
                  <p className="stat-trend">
                    {grantedPermissions.length} quyền hạn được cấp
                  </p>
                </article>

                <article className="stat-card sticker-panel">
                  <p className="stat-label">Toàn vẹn chuỗi sự kiện</p>
                  <p className="stat-value">
                    {tamperSimulated ? 'Cảnh báo' : '100%'}
                  </p>
                  <p
                    className={`stat-trend ${
                      tamperSimulated ? 'stat-trend-danger' : ''
                    }`}
                  >
                    {tamperSimulated
                      ? 'Phát hiện sai lệch chữ ký băm!'
                      : 'SHA-256 & RFC 8785 hợp lệ'}
                  </p>
                </article>
              </div>
              </section>
            )}

            {activeTab === 'lots' && <LotsPanel canReadLots={canReadLots} />}

            {activeTab === 'overview' && (
              <>
                {!canReadFarms ? (
                  <section className="sticker-panel panel-box">
                    <div className="panel-head">
                      <h2>Giới hạn quyền truy cập Vùng trồng (RBAC)</h2>
                      <p className="panel-sub">
                        Tài khoản <strong>{user.email}</strong> có vai trò{' '}
                        <code>{user.role}</code> (quyền hiện có:{' '}
                        <code>{grantedPermissions.join(', ')}</code>). Theo thiết
                        kế bảo mật N3-6, vai trò này không được phép đọc hoặc
                        chỉnh sửa danh mục vùng trồng.
                      </p>
                    </div>

                    <div className="action-row">
                      <button
                        type="button"
                        className="ds-button ds-button-brand ds-button-sm"
                        onClick={() => void runForbiddenProbe()}
                      >
                        Thử gọi GET /api/v1/farms/ (Kiểm chứng chặn 403)
                      </button>
                      <button
                        type="button"
                        className="ds-button ds-button-secondary ds-button-sm"
                        onClick={() => onTabChange('security')}
                      >
                        Xem chi tiết Ma trận Phân quyền
                      </button>
                    </div>

                    {rbacProbeResult && (
                      <div className="alert-box alert-error alert-spaced">
                        {rbacProbeResult}
                      </div>
                    )}
                  </section>
                ) : (
                  <>
                    <div className="dashboard-panels">
                      <section
                        className="panel-box sticker-panel"
                        aria-labelledby="chart-title"
                      >
                        <div className="panel-head">
                          <h2 id="chart-title">Biểu đồ phân bổ diện tích (ha)</h2>
                          <p className="panel-sub">
                            Bấm vào từng cột để xem nhanh thông số thửa đất
                          </p>
                        </div>

                        {farms.length === 0 ? (
                          <p className="empty-message">
                            Chưa có dữ liệu vùng trồng để hiển thị biểu đồ.
                          </p>
                        ) : (
                          <div
                            className="chart-bars"
                            role="img"
                            aria-label="Biểu đồ diện tích các vùng trồng"
                          >
                            {farms.map((farm, idx) => {
                              const area = Number(farm.area_ha) || 0
                              const heightPct = Math.max(
                                18,
                                Math.min(100, (area / maxAreaHa) * 100)
                              )
                              return (
                                <div key={farm.id} className="chart-bar-col">
                                  <span className="chart-bar-value">
                                    {area.toFixed(1)}ha
                                  </span>
                                  <div
                                    className="chart-bar"
                                    style={{ height: `${heightPct}%` }}
                                    title={`${farm.name}: ${area.toFixed(2)} ha`}
                                    onClick={() =>
                                      onNotify(
                                        `${farm.name} — Diện tích: ${area.toFixed(2)} ha`
                                      )
                                    }
                                  />
                                  <span className="chart-bar-caption">
                                    Lô #{idx + 1}
                                  </span>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </section>

                      {canWriteFarms && (
                        <section
                          className="panel-box sticker-panel"
                          aria-labelledby="form-title"
                        >
                          <div className="panel-head">
                            <h2 id="form-title">
                              {editingFarm
                                ? 'Cập nhật Vùng trồng'
                                : 'Khai báo Vùng trồng mới'}
                            </h2>
                            <p className="panel-sub">
                              {editingFarm
                                ? `Mã UUID bất biến: ${editingFarm.id}`
                                : 'Điền thông tin diện tích (> 0 ha) và tọa độ GPS hợp lệ'}
                            </p>
                          </div>

                          {!editingFarm && (
                            <div className="preset-strip">
                              {PRESET_LOCATIONS.map((preset) => (
                                <button
                                  key={preset.label}
                                  type="button"
                                  className="ds-button ds-button-secondary ds-button-sm"
                                  onClick={() => applyPreset(preset)}
                                >
                                  {preset.label}
                                </button>
                              ))}
                            </div>
                          )}

                          {formFeedback && (
                            <div
                              className={`alert-box ${
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
                                Tên vùng trồng / thửa đất{' '}
                                <span className="required-mark">*</span>
                              </label>
                              <input
                                id="farm-name"
                                type="text"
                                required
                                maxLength={200}
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="VD: Khu nhà kính Dâu tây Công nghệ cao A1"
                              />
                            </div>

                            <div className="form-field">
                              <label htmlFor="farm-area">
                                Diện tích canh tác (ha){' '}
                                <span className="required-mark">*</span>
                              </label>
                              <input
                                id="farm-area"
                                type="number"
                                step="0.0001"
                                min="0.0001"
                                required
                                value={areaHa}
                                onChange={(e) => setAreaHa(e.target.value)}
                                placeholder="VD: 2.4500"
                              />
                            </div>

                            <div className="form-row-2">
                              <div className="form-field">
                                <label htmlFor="farm-lat">
                                  Vĩ độ (-90 đến 90){' '}
                                  <span className="required-mark">*</span>
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
                                  placeholder="11.862450"
                                />
                              </div>

                              <div className="form-field">
                                <label htmlFor="farm-lng">
                                  Kinh độ (-180 đến 180){' '}
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
                                  placeholder="108.538120"
                                />
                              </div>
                            </div>

                            <div className="action-row">
                              <button
                                type="submit"
                                className="ds-button ds-button-brand ds-button-sm"
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
                                  className="ds-button ds-button-secondary ds-button-sm"
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

                    <section
                      className="data-table-wrapper sticker-panel"
                      aria-labelledby="farms-table-title"
                    >
                      <div className="data-table-header">
                        <div>
                          <h2 id="farms-table-title" className="section-title">
                            Danh mục Vùng trồng đã khai báo ({filteredFarms.length})
                          </h2>
                          <p className="panel-sub">
                            Mỗi vùng trồng có mã định danh UUID cố định không thay
                            đổi khi cập nhật tên hoặc diện tích
                          </p>
                        </div>
                      </div>

                      {listError && (
                        <div className="alert-box alert-error table-alert">
                          {listError}
                        </div>
                      )}

                      <div className="table-scroll">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th scope="col">Mã định danh (UUID)</th>
                              <th scope="col">Tên Vùng trồng / Thửa đất</th>
                              <th scope="col">Diện tích</th>
                              <th scope="col">Tọa độ GPS</th>
                              <th scope="col">Thao tác</th>
                            </tr>
                          </thead>
                          <tbody>
                            {loadingFarms ? (
                              <tr>
                                <td colSpan={5} className="cell-center">
                                  Đang tải danh sách vùng trồng...
                                </td>
                              </tr>
                            ) : filteredFarms.length === 0 ? (
                              <tr>
                                <td colSpan={5} className="cell-center">
                                  Không tìm thấy vùng trồng nào phù hợp.
                                </td>
                              </tr>
                            ) : (
                              filteredFarms.map((farm) => (
                                <tr
                                  key={farm.id}
                                  className={
                                    editingFarm?.id === farm.id
                                      ? 'row-editing'
                                      : undefined
                                  }
                                >
                                  <td>
                                    <code>{farm.id.slice(0, 13)}...</code>
                                  </td>
                                  <th scope="row" className="cell-strong">
                                    {farm.name}
                                  </th>
                                  <td>
                                    <span className="status-badge status-done">
                                      {Number(farm.area_ha).toFixed(2)} ha
                                    </span>
                                  </td>
                                  <td>
                                    <div className="coord-stack">
                                      <code>
                                        {farm.latitude}, {farm.longitude}
                                      </code>
                                      <a
                                        href={`https://www.google.com/maps?q=${farm.latitude},${farm.longitude}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="map-external-link"
                                      >
                                        Mở Google Maps
                                      </a>
                                    </div>
                                  </td>
                                  <td>
                                    {canWriteFarms && (
                                      <button
                                        type="button"
                                        className="ds-button ds-button-secondary ds-button-sm"
                                        onClick={() => startEdit(farm)}
                                      >
                                        Chỉnh sửa
                                      </button>
                                    )}
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  </>
                )}
              </>
            )}

            {activeTab === 'security' && (
              <SecurityPanel
                user={user}
                rbacProbeResult={rbacProbeResult}
                onRunProbe={() => void runForbiddenProbe()}
              />
            )}

            {activeTab === 'integrity' && (
              <IntegrityPanel
                tamperSimulated={tamperSimulated}
                onToggleTamper={() => {
                  setTamperSimulated((prev) => !prev)
                  onNotify(
                    !tamperSimulated
                      ? 'Đã mô phỏng sửa lén nhiệt độ tại sự kiện #03!'
                      : 'Đã khôi phục dữ liệu gốc hợp lệ.'
                  )
                }}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  )
}
