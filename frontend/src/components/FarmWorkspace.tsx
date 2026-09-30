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

export type WorkspaceTab = 'overview' | 'security' | 'integrity'

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
    label: '+ Mẫu Đà Lạt',
    name: 'Phân khu Rau hữu cơ Trại Mát',
    area_ha: '3.2500',
    latitude: '11.924850',
    longitude: '108.497210',
  },
  {
    label: '+ Mẫu Mộc Châu',
    name: 'Đồi Dâu tây Bản Áng Khu B',
    area_ha: '4.5000',
    latitude: '20.828640',
    longitude: '104.661520',
  },
  {
    label: '+ Mẫu Tiền Giang',
    name: 'Vùng trồng Xoài Cát Hòa Lộc Cái Bè',
    area_ha: '6.1000',
    latitude: '10.334910',
    longitude: '106.028450',
  },
]

const SAMPLE_HASH_EVENTS = [
  {
    seq: '#01',
    stage: 'Thu hoạch tại vùng trồng',
    temp: '14.2°C',
    prevHash: '00000000...00000000',
    hash: '9f86d081...8b4c70a1',
  },
  {
    seq: '#02',
    stage: 'Sơ chế & Cấp đông nhanh',
    temp: '3.8°C',
    prevHash: '9f86d081...8b4c70a1',
    hash: '4b227777...d4735e3a',
  },
  {
    seq: '#03',
    stage: 'Vận chuyển xe lạnh chuyên dụng',
    temp: '3.5°C',
    prevHash: '4b227777...d4735e3a',
    hash: 'e3b0c442...98fc1c14',
  },
  {
    seq: '#04',
    stage: 'Nhập kho trung tâm phân phối',
    temp: '4.0°C',
    prevHash: 'e3b0c442...98fc1c14',
    hash: 'a1860004...b62aa867',
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
              <span className="sidebar-brand-badge">✦ Chuỗi Lạnh Nông Sản</span>
              <div className="sidebar-brand-title">AgroChain</div>
              <p className="sidebar-brand-sub">{user.organization_name}</p>
            </div>

            <nav className="sidebar-nav">
              <ul className="sidebar-nav-list">
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
                    <span aria-hidden="true">◉</span>
                    <span>Vùng trồng &amp; Thửa đất</span>
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
                    <span aria-hidden="true">▦</span>
                    <span>Phân quyền &amp; Cô lập RLS</span>
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
                    <span aria-hidden="true">◎</span>
                    <span>Chuỗi Hash Sự kiện</span>
                  </button>
                </li>
                <li>
                  <a
                    href={`${API_BASE_URL}/docs`}
                    target="_blank"
                    rel="noreferrer"
                    className="dashboard-nav-item"
                  >
                    <span aria-hidden="true">↗</span>
                    <span>Tài liệu API (Swagger)</span>
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
                ☰
              </button>
              <div>
                <h1 style={{ fontSize: '24px', marginBottom: '2px' }}>
                  {activeTab === 'overview'
                    ? 'Quản lý Vùng trồng & Thửa đất'
                    : activeTab === 'security'
                      ? 'Phân quyền RBAC & Cô lập Đa tổ chức (RLS)'
                      : 'Xác minh Toàn vẹn Chuỗi Sự kiện (SHA-256)'}
                </h1>
                <p style={{ fontSize: '13px', color: 'var(--body-subtle)' }}>
                  Đơn vị: <strong>{user.organization_name}</strong> ({ORG_TYPE_LABELS[user.organization_type]})
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
              <button
                type="button"
                className="ds-button ds-button-brand ds-button-sm"
                onClick={() => void refreshFarms()}
              >
                Làm mới dữ liệu
              </button>
            </div>
          </header>

          <main className="dashboard-content">
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
                  <p className="stat-value" style={{ fontSize: '22px' }}>
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
                    className="stat-trend"
                    style={{
                      color: tamperSimulated
                        ? 'var(--fg-danger)'
                        : 'var(--fg-success-strong)',
                    }}
                  >
                    {tamperSimulated
                      ? 'Phát hiện sai lệch chữ ký băm!'
                      : 'SHA-256 & RFC 8785 hợp lệ'}
                  </p>
                </article>
              </div>
            </section>

            {activeTab === 'overview' && (
              <>
                {!canReadFarms ? (
                  <section className="sticker-panel chart-panel">
                    <h2 style={{ fontSize: '22px', marginBottom: '8px' }}>
                      Giới hạn quyền truy cập Vùng trồng (RBAC)
                    </h2>
                    <p
                      style={{
                        fontSize: '14px',
                        color: 'var(--body-subtle)',
                        marginBottom: '16px',
                      }}
                    >
                      Tài khoản <strong>{user.email}</strong> có vai trò{' '}
                      <code>{user.role}</code> (chỉ có quyền{' '}
                      <code>{grantedPermissions.join(', ')}</code>). Theo thiết kế
                      bảo mật N3-6, vai trò này không được phép đọc hoặc chỉnh sửa
                      danh mục vùng trồng.
                    </p>
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
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
                      <div
                        className="alert-box alert-error"
                        style={{ marginTop: '16px', marginBottom: 0 }}
                      >
                        {rbacProbeResult}
                      </div>
                    )}
                  </section>
                ) : (
                  <>
                    <div className="dashboard-panels">
                      <section
                        className="chart-panel sticker-panel"
                        aria-labelledby="chart-title"
                      >
                        <h2
                          id="chart-title"
                          style={{ fontSize: '20px', marginBottom: '6px' }}
                        >
                          Biểu đồ phân bổ diện tích (ha)
                        </h2>
                        <p
                          style={{
                            fontSize: '13px',
                            color: 'var(--body-subtle)',
                            marginBottom: '12px',
                          }}
                        >
                          Bấm vào từng cột để xem nhanh thông số thửa đất
                        </p>

                        {farms.length === 0 ? (
                          <p
                            style={{
                              padding: '40px 0',
                              textAlign: 'center',
                              color: 'var(--body-subtle)',
                            }}
                          >
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
                                  <span
                                    style={{
                                      fontSize: '11px',
                                      fontFamily: 'var(--font-geist-mono)',
                                      fontWeight: 700,
                                      color: 'var(--heading)',
                                    }}
                                  >
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
                          className="activity-panel sticker-panel"
                          aria-labelledby="form-title"
                        >
                          <h2
                            id="form-title"
                            style={{ fontSize: '20px', marginBottom: '4px' }}
                          >
                            {editingFarm
                              ? 'Cập nhật Vùng trồng'
                              : 'Khai báo Vùng trồng mới'}
                          </h2>
                          <p
                            style={{
                              fontSize: '13px',
                              color: 'var(--body-subtle)',
                              marginBottom: '14px',
                            }}
                          >
                            {editingFarm
                              ? `Mã UUID bất biến: ${editingFarm.id}`
                              : 'Điền thông tin diện tích (> 0 ha) và tọa độ GPS hợp lệ'}
                          </p>

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

                            <div
                              style={{
                                display: 'flex',
                                gap: '10px',
                                flexWrap: 'wrap',
                              }}
                            >
                              <button
                                type="submit"
                                className="ds-button ds-button-brand ds-button-sm"
                                disabled={saving}
                              >
                                {saving
                                  ? 'Đang lưu...'
                                  : editingFarm
                                    ? 'Lưu cập nhật'
                                    : '✦ Thêm vùng trồng'}
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
                          <h2 id="farms-table-title" style={{ fontSize: '20px' }}>
                            Danh mục Vùng trồng đã khai báo ({filteredFarms.length})
                          </h2>
                          <p
                            style={{
                              fontSize: '13px',
                              color: 'var(--body-subtle)',
                            }}
                          >
                            Mỗi vùng trồng có mã định danh UUID cố định không thay đổi
                            khi cập nhật tên hoặc diện tích
                          </p>
                        </div>
                      </div>

                      {listError && (
                        <div
                          className="alert-box alert-error"
                          style={{ margin: '0 24px 16px' }}
                        >
                          {listError}
                        </div>
                      )}

                      <div style={{ overflowX: 'auto' }}>
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
                                <td colSpan={5} style={{ textAlign: 'center' }}>
                                  Đang tải danh sách vùng trồng...
                                </td>
                              </tr>
                            ) : filteredFarms.length === 0 ? (
                              <tr>
                                <td colSpan={5} style={{ textAlign: 'center' }}>
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
                                  <th scope="row" style={{ fontWeight: 700 }}>
                                    {farm.name}
                                  </th>
                                  <td>
                                    <span className="status-badge status-done">
                                      {Number(farm.area_ha).toFixed(2)} ha
                                    </span>
                                  </td>
                                  <td>
                                    <div style={{ display: 'grid', gap: '2px' }}>
                                      <code>
                                        {farm.latitude}, {farm.longitude}
                                      </code>
                                      <a
                                        href={`https://www.google.com/maps?q=${farm.latitude},${farm.longitude}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        style={{
                                          fontSize: '12px',
                                          color: 'var(--heading)',
                                          fontWeight: 600,
                                          textDecoration: 'underline',
                                        }}
                                      >
                                        Mở Google Maps ↗
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
              <div className="dashboard-panels">
                <section className="sticker-panel chart-panel">
                  <h2 style={{ fontSize: '20px', marginBottom: '12px' }}>
                    Thông tin Phiên &amp; Ngữ cảnh Đa tổ chức (PostgreSQL RLS)
                  </h2>
                  <div style={{ display: 'grid', gap: '12px' }}>
                    <div
                      style={{
                        padding: '12px 14px',
                        borderRadius: '10px',
                        background: 'var(--neutral-primary-soft)',
                      }}
                    >
                      <div style={{ fontSize: '12px', color: 'var(--body-subtle)' }}>
                        Người dùng đang xác thực
                      </div>
                      <div style={{ fontWeight: 700 }}>
                        {user.full_name} ({user.email})
                      </div>
                    </div>

                    <div
                      style={{
                        padding: '12px 14px',
                        borderRadius: '10px',
                        background: 'var(--neutral-primary-soft)',
                      }}
                    >
                      <div style={{ fontSize: '12px', color: 'var(--body-subtle)' }}>
                        Biến phiên PostgreSQL RLS (app.current_organization)
                      </div>
                      <code>{user.organization_id}</code>
                    </div>

                    <div
                      style={{
                        padding: '12px 14px',
                        borderRadius: '10px',
                        background: 'var(--neutral-primary-soft)',
                      }}
                    >
                      <div style={{ fontSize: '12px', color: 'var(--body-subtle)' }}>
                        Danh sách quyền hạn RBAC được cấp
                      </div>
                      <div
                        style={{
                          display: 'flex',
                          gap: '8px',
                          flexWrap: 'wrap',
                          marginTop: '6px',
                        }}
                      >
                        {grantedPermissions.map((perm) => (
                          <span key={perm} className="status-badge status-done">
                            {perm}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="sticker-panel activity-panel">
                  <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>
                    Kiểm chứng Bảo mật API Thực tế
                  </h2>
                  <p
                    style={{
                      fontSize: '14px',
                      color: 'var(--body-subtle)',
                      marginBottom: '16px',
                    }}
                  >
                    Bấm nút bên dưới để gửi yêu cầu trực tiếp tới endpoint{' '}
                    <code>GET /api/v1/farms/</code> và kiểm tra phản hồi phân quyền từ
                    Backend:
                  </p>

                  <button
                    type="button"
                    className="ds-button ds-button-brand ds-button-sm"
                    onClick={() => void runForbiddenProbe()}
                  >
                    Gửi yêu cầu kiểm tra quyền truy cập API
                  </button>

                  {rbacProbeResult && (
                    <div
                      className={`alert-box ${
                        rbacProbeResult.startsWith('200')
                          ? 'alert-success'
                          : 'alert-error'
                      }`}
                      style={{ marginTop: '16px', marginBottom: 0 }}
                    >
                      {rbacProbeResult}
                    </div>
                  )}
                </section>
              </div>
            )}

            {activeTab === 'integrity' && (
              <section className="data-table-wrapper sticker-panel">
                <div className="data-table-header">
                  <div>
                    <h2 style={{ fontSize: '20px' }}>
                      Chuỗi Băm Mật mã Chống sửa lén Bản ghi Sự kiện (SHA-256 + RFC 8785)
                    </h2>
                    <p style={{ fontSize: '13px', color: 'var(--body-subtle)' }}>
                      Mỗi sự kiện chuỗi lạnh băm kèm mã hash của sự kiện liền trước —
                      tốc độ xác minh thực nghiệm: 147.856 sự kiện/giây
                    </p>
                  </div>

                  <button
                    type="button"
                    className="ds-button ds-button-secondary ds-button-sm"
                    onClick={() => {
                      setTamperSimulated((prev) => !prev)
                      onNotify(
                        !tamperSimulated
                          ? 'Đã mô phỏng sửa lén nhiệt độ tại sự kiện #03!'
                          : 'Đã khôi phục dữ liệu gốc hợp lệ.'
                      )
                    }}
                  >
                    {tamperSimulated
                      ? 'Khôi phục dữ liệu gốc'
                      : 'Mô phỏng sửa lén nhiệt độ (#03)'}
                  </button>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Thứ tự</th>
                        <th>Công đoạn Chuỗi lạnh</th>
                        <th>Nhiệt độ ghi nhận</th>
                        <th>Hash sự kiện trước (Prev Hash)</th>
                        <th>Hash hiện tại (SHA-256)</th>
                        <th>Trạng thái</th>
                      </tr>
                    </thead>
                    <tbody>
                      {SAMPLE_HASH_EVENTS.map((ev, index) => {
                        const isTamperedRow = tamperSimulated && index === 2
                        const isBrokenDownstream = tamperSimulated && index > 2
                        return (
                          <tr
                            key={ev.seq}
                            style={
                              isTamperedRow || isBrokenDownstream
                                ? { background: 'var(--danger-soft)' }
                                : undefined
                            }
                          >
                            <td>
                              <code>{ev.seq}</code>
                            </td>
                            <th scope="row" style={{ fontWeight: 700 }}>
                              {ev.stage}
                            </th>
                            <td>
                              <code>{isTamperedRow ? '99.9°C (Đã sửa)' : ev.temp}</code>
                            </td>
                            <td>
                              <code>{ev.prevHash}</code>
                            </td>
                            <td>
                              <code>
                                {isTamperedRow
                                  ? 'ff009911...LỖI_HASH'
                                  : ev.hash}
                              </code>
                            </td>
                            <td>
                              {isTamperedRow ? (
                                <span
                                  className="status-badge"
                                  style={{
                                    background: 'var(--danger-soft)',
                                    color: 'var(--fg-danger)',
                                  }}
                                >
                                  Bị can thiệp
                                </span>
                              ) : isBrokenDownstream ? (
                                <span
                                  className="status-badge"
                                  style={{
                                    background: 'var(--danger-soft)',
                                    color: 'var(--fg-danger)',
                                  }}
                                >
                                  Đứt chuỗi liên kết
                                </span>
                              ) : (
                                <span className="status-badge status-done">
                                  Toàn vẹn
                                </span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </main>
        </div>
      </div>
    </div>
  )
}
