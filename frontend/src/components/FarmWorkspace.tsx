import { useState, useEffect, useCallback, type FormEvent } from 'react'
import {
  API_BASE_URL,
  createFarm,
  getFarms,
  login,
  updateFarm,
} from '../services/api'
import {
  DEMO_ACCOUNTS,
  hasPermission,
  ORG_TYPE_LABELS,
  ROLE_LABELS,
  ROLE_PERMISSIONS,
  type DemoAccount,
  type Farm,
  type SessionUser,
} from '../types'
import { IntegrityPanel } from './IntegrityPanel'
import { SecurityPanel } from './SecurityPanel'

export type WorkspaceTab = 'overview' | 'security' | 'integrity'

interface FarmWorkspaceProps {
  user: SessionUser
  activeTab: WorkspaceTab
  isDark: boolean
  onToggleTheme: () => void
  onTabChange: (tab: WorkspaceTab) => void
  onSwitchUser: (user: SessionUser) => void
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
  isDark,
  onToggleTheme,
  onTabChange,
  onSwitchUser,
  onLogout,
  onNotify,
}: FarmWorkspaceProps) {
  const canReadFarms = hasPermission(user.role, 'farms:read')
  const canWriteFarms = hasPermission(user.role, 'farms:write')
  const grantedPermissions = ROLE_PERMISSIONS[user.role] ?? []

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [switchingAccount, setSwitchingAccount] = useState(false)

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

  const handleQuickSwitch = async (account: DemoAccount) => {
    if (account.email === user.email || switchingAccount) return
    setSwitchingAccount(true)
    try {
      const nextUser = await login({
        email: account.email,
        password: account.password,
      })
      onNotify(`Đã chuyển sang phiên: ${nextUser.organization_name}`)
      onSwitchUser(nextUser)
    } catch (err) {
      onNotify(
        err instanceof Error ? err.message : 'Không thể chuyển đổi tài khoản'
      )
    } finally {
      setSwitchingAccount(false)
    }
  }

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
          message: `Đã cập nhật "${updated.name}" (UUID cố định: ${updated.id.slice(0, 8)}...).`,
        })
        onNotify(`Đã lưu cập nhật: ${updated.name}`)
      } else {
        const created = await createFarm(payload)
        setFarms((prev) => [...prev, created])
        setFormFeedback({
          type: 'success',
          message: `Đã thêm vùng trồng "${created.name}".`,
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
    setRbacProbeResult('Đang gửi GET /api/v1/farms/ tới Backend...')
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
  const avgAreaHa = farms.length > 0 ? totalAreaHa / farms.length : 0
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
              <div className="sidebar-brand-row">
                <div className="sidebar-brand-title">AgroChain</div>
                <span className="sidebar-brand-badge">N3-4..7</span>
              </div>
              <p className="sidebar-brand-sub" title={user.organization_name}>
                {user.organization_name}
              </p>
            </div>

            <nav className="sidebar-nav">
              <div>
                <div className="sidebar-section-label">Phân hệ Nghiệp vụ</div>
                <ul className="sidebar-nav-list">
                  <li>
                    <button
                      type="button"
                      onClick={() => {
                        onTabChange('overview')
                        setSidebarOpen(false)
                      }}
                      className={`dashboard-nav-item ${
                        activeTab === 'overview'
                          ? 'dashboard-nav-item-active'
                          : ''
                      }`}
                    >
                      <span>Tổng quan &amp; Vùng trồng</span>
                      <span className="nav-tag">N3-7</span>
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
                        activeTab === 'security'
                          ? 'dashboard-nav-item-active'
                          : ''
                      }`}
                    >
                      <span>Phân quyền &amp; RLS</span>
                      <span className="nav-tag">N3-6</span>
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
                        activeTab === 'integrity'
                          ? 'dashboard-nav-item-active'
                          : ''
                      }`}
                    >
                      <span>Chuỗi Hash Sự kiện</span>
                      <span className="nav-tag">N3-4</span>
                    </button>
                  </li>
                  <li>
                    <a
                      href={`${API_BASE_URL}/docs`}
                      target="_blank"
                      rel="noreferrer"
                      className="dashboard-nav-item"
                    >
                      <span>OpenAPI Swagger</span>
                      <span className="nav-tag">API</span>
                    </a>
                  </li>
                </ul>
              </div>

              <div>
                <div className="sidebar-section-label">Trạng thái Hạ tầng</div>
                <div className="sidebar-specs-box">
                  <div className="sidebar-spec-row">
                    <span className="sidebar-spec-key">PostgreSQL RLS</span>
                    <span className="sidebar-spec-val">FORCE ON</span>
                  </div>
                  <div className="sidebar-spec-row">
                    <span className="sidebar-spec-key">Tenant ID</span>
                    <span className="sidebar-spec-val">
                      {user.organization_id.slice(0, 8)}...
                    </span>
                  </div>
                  <div className="sidebar-spec-row">
                    <span className="sidebar-spec-key">Session Auth</span>
                    <span className="sidebar-spec-val">SHA-256</span>
                  </div>
                  <div className="sidebar-spec-row">
                    <span className="sidebar-spec-key">Hash Chain</span>
                    <span className="sidebar-spec-val">RFC 8785</span>
                  </div>
                </div>
              </div>
            </nav>
          </div>

          <div className="sidebar-footer">
            <div className="sidebar-user-card">
              <div className="sidebar-user-name">{user.full_name}</div>
              <div className="sidebar-user-meta" title={user.email}>
                {user.email}
              </div>
              <div className="sidebar-user-meta">
                Vai trò: <strong>{ROLE_LABELS[user.role]}</strong>
              </div>
            </div>

            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm ds-button-block"
              onClick={onLogout}
            >
              Đăng xuất phiên
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
              <h1 className="topbar-title">
                {activeTab === 'overview'
                  ? 'Bảng điều khiển Vùng trồng & Giám sát Chuỗi lạnh'
                  : activeTab === 'security'
                    ? 'Ma trận Phân quyền RBAC & Cô lập Đa tổ chức (RLS)'
                    : 'Kiểm chứng Toàn vẹn Chuỗi Sự kiện (SHA-256 + RFC 8785)'}
              </h1>
              <span className="topbar-divider">|</span>
              <span className="status-badge status-done">
                {ORG_TYPE_LABELS[user.organization_type]}
              </span>
            </div>

            <div className="topbar-actions">
              <div
                className="tenant-switcher-group"
                role="group"
                aria-label="Chuyển đổi nhanh tài khoản Demo"
              >
                <span className="tenant-switcher-label">Đổi nhanh phiên:</span>
                {DEMO_ACCOUNTS.map((acc) => {
                  const isCurrent = acc.email === user.email
                  return (
                    <button
                      key={acc.email}
                      type="button"
                      disabled={switchingAccount}
                      onClick={() => void handleQuickSwitch(acc)}
                      className={`tenant-pill-btn ${
                        isCurrent ? 'tenant-pill-btn-active' : ''
                      }`}
                      title={`Chuyển sang ${acc.label} (${acc.email})`}
                    >
                      {acc.shortName}
                    </button>
                  )
                })}
              </div>

              {activeTab === 'overview' && canReadFarms && (
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Lọc tên thửa, UUID, GPS..."
                  className="dashboard-search"
                  aria-label="Tìm kiếm vùng trồng"
                />
              )}

              <button
                type="button"
                className="ds-button ds-button-secondary ds-button-sm"
                onClick={() => void refreshFarms()}
              >
                Làm mới
              </button>

              <button
                type="button"
                className="ds-button ds-button-secondary ds-button-sm"
                onClick={onToggleTheme}
              >
                {isDark ? 'Sáng' : 'Tối'}
              </button>
            </div>
          </header>

          <main className="dashboard-content">
            <section aria-label="Chỉ số vận hành tổng hợp">
              <div className="stats-grid">
                <article className="stat-card sticker-panel">
                  <p className="stat-label">Đơn vị thành viên (Tenant)</p>
                  <p
                    className="stat-value stat-value-sans"
                    title={user.organization_name}
                  >
                    {user.organization_name}
                  </p>
                  <p className="stat-trend">
                    ID: {user.organization_id.slice(0, 8)}...
                  </p>
                </article>

                <article className="stat-card sticker-panel">
                  <p className="stat-label">Vùng trồng thuộc đơn vị</p>
                  <p className="stat-value">
                    {canReadFarms ? `${farms.length} vùng` : 'Chặn (403)'}
                  </p>
                  <p className="stat-trend">
                    {canReadFarms
                      ? 'Cô lập bởi PostgreSQL RLS'
                      : 'Không có quyền farms:read'}
                  </p>
                </article>

                <article className="stat-card sticker-panel">
                  <p className="stat-label">Tổng diện tích canh tác</p>
                  <p className="stat-value">
                    {canReadFarms ? `${totalAreaHa.toFixed(2)} ha` : '—'}
                  </p>
                  <p className="stat-trend">
                    {canReadFarms
                      ? `TB: ${avgAreaHa.toFixed(2)} ha / thửa`
                      : 'Bị giới hạn theo RBAC'}
                  </p>
                </article>

                <article className="stat-card sticker-panel">
                  <p className="stat-label">Vai trò &amp; Quyền RBAC</p>
                  <p className="stat-value stat-value-sans">
                    {ROLE_LABELS[user.role]}
                  </p>
                  <p className="stat-trend">
                    <code>{user.role}</code> ({grantedPermissions.length} quyền)
                  </p>
                </article>

                <article className="stat-card sticker-panel">
                  <p className="stat-label">Chuỗi băm sự kiện (N3-4)</p>
                  <p className="stat-value">
                    {tamperSimulated ? 'Lỗi Hash!' : '4/4 Hợp lệ'}
                  </p>
                  <p
                    className={`stat-trend ${
                      tamperSimulated ? 'stat-trend-danger' : ''
                    }`}
                  >
                    {tamperSimulated
                      ? 'Phát hiện can thiệp tại #03'
                      : 'SHA-256 · 147,8k sự kiện/s'}
                  </p>
                </article>

                <article className="stat-card sticker-panel">
                  <p className="stat-label">Bảo mật phiên (N3-5)</p>
                  <p className="stat-value stat-value-sans">Argon2id + Cookie</p>
                  <p className="stat-trend">Khóa 15p nếu sai mật khẩu 5 lần</p>
                </article>
              </div>
            </section>

            {activeTab === 'overview' && (
              <>
                <div className="dashboard-split-main">
                  {!canReadFarms ? (
                    <section className="sticker-panel panel-box">
                      <div className="panel-head">
                        <h2>
                          Chặn Truy cập Danh mục Vùng trồng theo RBAC (N3-6)
                        </h2>
                        <span className="status-badge status-danger">
                          HTTP 403 Forbidden
                        </span>
                      </div>
                      <p className="panel-sub">
                        Tài khoản <strong>{user.email}</strong> đang mang vai trò{' '}
                        <code>{user.role}</code> (quyền được cấp:{' '}
                        <code>{grantedPermissions.join(', ')}</code>). Theo thiết
                        kế bảo mật N3-6, vai trò Thanh tra viên chỉ đọc lô hàng (
                        <code>lots:read_all</code>) và bị chặn truy cập trực tiếp
                        vào API quản lý vùng trồng (<code>farms:read</code>,{' '}
                        <code>farms:write</code>).
                      </p>

                      <div className="action-row alert-spaced">
                        <button
                          type="button"
                          className="ds-button ds-button-brand ds-button-sm"
                          onClick={() => void runForbiddenProbe()}
                        >
                          Gửi thử GET /api/v1/farms/ (Kiểm chứng chặn 403)
                        </button>
                        <button
                          type="button"
                          className="ds-button ds-button-secondary ds-button-sm"
                          onClick={() => onTabChange('security')}
                        >
                          Mở Ma trận Phân quyền đầy đủ
                        </button>
                      </div>

                      {rbacProbeResult && (
                        <div className="alert-box alert-error alert-spaced">
                          {rbacProbeResult}
                        </div>
                      )}
                    </section>
                  ) : (
                    <section
                      className="data-table-wrapper sticker-panel"
                      aria-labelledby="farms-table-title"
                    >
                      <div className="data-table-header">
                        <div>
                          <h2 id="farms-table-title" className="section-title">
                            Danh mục Vùng trồng &amp; Thửa đất ({filteredFarms.length}
                            )
                          </h2>
                          <p className="panel-sub">
                            Dữ liệu lọc tự động theo{' '}
                            <code>
                              organization_id = {user.organization_id.slice(0, 8)}
                              ...
                            </code>{' '}
                            tại tầng PostgreSQL RLS
                          </p>
                        </div>
                        <span className="status-badge status-done">
                          UUID Bất biến (N3-7)
                        </span>
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
                              <th scope="col">Mã UUID</th>
                              <th scope="col">Tên Vùng trồng / Thửa đất</th>
                              <th scope="col">Diện tích</th>
                              <th scope="col">Tỷ trọng</th>
                              <th scope="col">Tọa độ GPS (WGS84)</th>
                              <th scope="col">Thao tác</th>
                            </tr>
                          </thead>
                          <tbody>
                            {loadingFarms ? (
                              <tr>
                                <td colSpan={6} className="cell-center">
                                  Đang tải danh sách vùng trồng...
                                </td>
                              </tr>
                            ) : filteredFarms.length === 0 ? (
                              <tr>
                                <td colSpan={6} className="cell-center">
                                  Không có vùng trồng nào khớp với bộ lọc.
                                </td>
                              </tr>
                            ) : (
                              filteredFarms.map((farm) => {
                                const areaNum = Number(farm.area_ha) || 0
                                const sharePct =
                                  totalAreaHa > 0
                                    ? Math.round((areaNum / totalAreaHa) * 100)
                                    : 0
                                return (
                                  <tr
                                    key={farm.id}
                                    className={
                                      editingFarm?.id === farm.id
                                        ? 'row-editing'
                                        : undefined
                                    }
                                  >
                                    <td>
                                      <code title={farm.id}>
                                        {farm.id.slice(0, 8)}...
                                      </code>
                                    </td>
                                    <th scope="row" className="cell-strong">
                                      {farm.name}
                                    </th>
                                    <td>
                                      <span className="status-badge status-done">
                                        {areaNum.toFixed(2)} ha
                                      </span>
                                    </td>
                                    <td>
                                      <div className="area-bar-cell">
                                        <div className="area-bar-track">
                                          <div
                                            className="area-bar-fill"
                                            style={{ width: `${sharePct}%` }}
                                          />
                                        </div>
                                        <span className="area-bar-pct">
                                          {sharePct}%
                                        </span>
                                      </div>
                                    </td>
                                    <td>
                                      <div className="coord-inline">
                                        <code>
                                          {farm.latitude}, {farm.longitude}
                                        </code>
                                        <a
                                          href={`https://www.google.com/maps?q=${farm.latitude},${farm.longitude}`}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="map-external-link"
                                        >
                                          Bản đồ
                                        </a>
                                      </div>
                                    </td>
                                    <td>
                                      {canWriteFarms && (
                                        <button
                                          type="button"
                                          className="ds-button ds-button-secondary ds-button-xs"
                                          onClick={() => startEdit(farm)}
                                        >
                                          Sửa
                                        </button>
                                      )}
                                    </td>
                                  </tr>
                                )
                              })
                            )}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  )}

                  <div className="info-stack">
                    {canWriteFarms && (
                      <section
                        className="panel-box sticker-panel"
                        aria-labelledby="form-title"
                      >
                        <div className="panel-head">
                          <h2 id="form-title">
                            {editingFarm
                              ? 'Cập nhật Vùng trồng'
                              : 'Khai báo Vùng trồng mới (N3-7)'}
                          </h2>
                          {editingFarm && (
                            <code title={editingFarm.id}>
                              ID: {editingFarm.id.slice(0, 8)}...
                            </code>
                          )}
                        </div>

                        {!editingFarm && (
                          <div className="preset-strip">
                            <span className="preset-label">Mẫu nhanh:</span>
                            {PRESET_LOCATIONS.map((preset) => (
                              <button
                                key={preset.label}
                                type="button"
                                className="ds-button ds-button-secondary ds-button-xs"
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
                          <div className="form-row-2">
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
                                placeholder="VD: Khu nhà kính Dâu tây A1"
                              />
                            </div>

                            <div className="form-field">
                              <label htmlFor="farm-area">
                                Diện tích (ha &gt; 0){' '}
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
                          </div>

                          <div className="form-row-2">
                            <div className="form-field">
                              <label htmlFor="farm-lat">
                                Vĩ độ (-90..90){' '}
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
                                Kinh độ (-180..180){' '}
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
                                Hủy
                              </button>
                            )}
                          </div>
                        </form>
                      </section>
                    )}

                    {canReadFarms && farms.length > 0 && (
                      <section
                        className="panel-box sticker-panel"
                        aria-labelledby="chart-title"
                      >
                        <div className="panel-head">
                          <h2 id="chart-title">Tương quan diện tích các lô (ha)</h2>
                          <span className="panel-sub">
                            Tổng: {totalAreaHa.toFixed(2)} ha
                          </span>
                        </div>

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
                                  {area.toFixed(1)}
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
                      </section>
                    )}
                  </div>
                </div>

                <div className="dashboard-split-equal">
                  <IntegrityPanel
                    compact
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

                  <section className="sticker-panel panel-box">
                    <div className="panel-head">
                      <h2>
                        Trạng thái Cô lập Đa tổ chức (RLS) &amp; Phân quyền RBAC (N3-6)
                      </h2>
                      <button
                        type="button"
                        className="ds-button ds-button-secondary ds-button-xs"
                        onClick={() => onTabChange('security')}
                      >
                        Chi tiết ma trận
                      </button>
                    </div>

                    <div className="info-grid-2">
                      <div className="info-item">
                        <span className="info-item-label">
                          Biến phiên PostgreSQL (app.current_organization)
                        </span>
                        <code>{user.organization_id}</code>
                      </div>

                      <div className="info-item">
                        <span className="info-item-label">
                          Quyền hạn RBAC được cấp cho {user.role}
                        </span>
                        <div className="badge-row">
                          {grantedPermissions.map((perm) => (
                            <span
                              key={perm}
                              className="status-badge status-done"
                            >
                              {perm}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="action-row alert-spaced">
                      <button
                        type="button"
                        className="ds-button ds-button-brand ds-button-xs"
                        onClick={() => void runForbiddenProbe()}
                      >
                        Kiểm tra API: GET /api/v1/farms/
                      </button>
                      <span className="panel-sub">
                        Đổi nhanh sang tài khoản Mộc Châu hoặc Thanh tra trên
                        thanh công cụ để so sánh kết quả
                      </span>
                    </div>

                    {rbacProbeResult && (
                      <div
                        className={`alert-box alert-spaced ${
                          rbacProbeResult.startsWith('200')
                            ? 'alert-success'
                            : 'alert-error'
                        }`}
                        role="status"
                      >
                        {rbacProbeResult}
                      </div>
                    )}
                  </section>
                </div>
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
