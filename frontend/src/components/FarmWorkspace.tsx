import { useState, useEffect, useCallback, useRef, type FormEvent } from 'react'
import { ApiError, createFarm, getFarms, updateFarm } from '../services/api'
import { getIncomingHandovers } from '../services/api'
import {
  hasPermission,
  type Farm,
  type SessionUser,
} from '../types'
import { FarmFormPanel } from './FarmFormPanel'
import { HandoversPanel } from './HandoversPanel'
import { IntegrityPanel } from './IntegrityPanel'
import { LotsPanel } from './LotsPanel'
import { ProductsPanel } from './ProductsPanel'
import { SecurityPanel } from './SecurityPanel'
import { WorkspaceSidebar } from './WorkspaceSidebar'
import { WorkspaceTopbar } from './WorkspaceTopbar'

export type WorkspaceTab = 'lots' | 'products' | 'handovers' | 'overview' | 'security' | 'integrity'

interface FarmWorkspaceProps {
  user: SessionUser
  activeTab: WorkspaceTab
  isDark: boolean
  onToggleTheme: () => void
  onTabChange: (tab: WorkspaceTab) => void
  onLogout: () => void
  onNotify: (message: string) => void
}

export function FarmWorkspace({
  user,
  activeTab,
  isDark,
  onToggleTheme,
  onTabChange,
  onLogout,
  onNotify,
}: FarmWorkspaceProps) {
  const canReadFarms = hasPermission(user.role, 'farms:read')
  const canWriteFarms = hasPermission(user.role, 'farms:write')
  const canReadLots = hasPermission(user.role, 'lots:read')
  const canCreateLots = hasPermission(user.role, 'lots:create')
  const canManageProducts = hasPermission(user.role, 'products:update')
  const canCreateHandovers = hasPermission(user.role, 'handovers:create')
  const [pendingHandoverCount, setPendingHandoverCount] = useState(0)

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
  const savingRef = useRef(false)
  const [formFeedback, setFormFeedback] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  useEffect(() => {
    if (!canCreateHandovers) return
    let active = true
    getIncomingHandovers()
      .then((handovers) => {
        if (active) setPendingHandoverCount(handovers.filter((handover) => handover.status === 'pending').length)
      })
      .catch(() => { if (active) setPendingHandoverCount(0) })
    return () => { active = false }
  }, [canCreateHandovers])

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
    onTabChange('overview')
    onNotify(`Đang chỉnh sửa: ${farm.name}`)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (savingRef.current) return

    savingRef.current = true
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
        setFormFeedback({ type: 'success', message: `Đã cập nhật "${updated.name}".` })
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
      savingRef.current = false
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
      if (err instanceof ApiError && err.status === 403) {
        setRbacProbeResult(
          `403 Forbidden — Backend đã chặn truy cập theo đúng ma trận RBAC: "${err.message}"`
        )
        onNotify('Backend đã chặn truy cập trái phép (403 Forbidden)')
      } else {
        setRbacProbeResult(
          `Không kiểm tra được quyền truy cập: ${err instanceof Error ? err.message : 'Lỗi không xác định.'}`
        )
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
        <WorkspaceSidebar
          user={user}
          activeTab={activeTab}
          pendingHandoverCount={pendingHandoverCount}
          sidebarOpen={sidebarOpen}
          onCloseSidebar={() => setSidebarOpen(false)}
          onTabChange={onTabChange}
          onLogout={onLogout}
        />

        <div className="dashboard-main">
          <WorkspaceTopbar
            activeTab={activeTab}
            canReadFarms={canReadFarms}
            searchQuery={searchQuery}
            isDark={isDark}
            onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
            onSearchChange={setSearchQuery}
            onRefresh={() => void refreshFarms()}
            onToggleTheme={onToggleTheme}
          />

          <main className="dashboard-content">
            {activeTab === 'lots' && (
              <LotsPanel
                canReadLots={canReadLots}
                canCreateLots={canCreateLots}
                canReadEvents={hasPermission(user.role, 'events:read')}
              />
            )}

            {activeTab === 'products' && (
              <ProductsPanel canManage={canManageProducts} />
            )}

            {activeTab === 'handovers' && canCreateHandovers && (
              <HandoversPanel onPendingCountChange={setPendingHandoverCount} />
            )}

            {activeTab === 'overview' && (
              <>
                <div className="dashboard-split-main">
                  {!canReadFarms ? (
                    <section className="panel-card panel-box">
                      <div className="panel-head">
                        <h2>
                          Chặn Truy cập Danh mục Vùng trồng theo RBAC (N3-6)
                        </h2>
                        <span className="status-badge status-danger">
                          HTTP 403 Forbidden
                        </span>
                      </div>
                      <p className="panel-sub">Tài khoản hiện tại không có quyền truy cập danh sách vùng trồng.</p>

                      <div className="action-row alert-spaced">
                        <button
                          type="button"
                          className="ds-button ds-button-brand ds-button-sm"
                          onClick={() => void runForbiddenProbe()}
                        >
                          Kiểm tra quyền truy cập
                        </button>
                        <button
                          type="button"
                          className="ds-button ds-button-secondary ds-button-sm"
                          onClick={() => onTabChange('security')}
                        >
                          Xem quyền truy cập
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
                      className="data-table-wrapper panel-card"
                      aria-labelledby="farms-table-title"
                    >
                      <div className="data-table-header">
                        <div>
                          <h2 id="farms-table-title" className="section-title">
                            Vùng trồng ({filteredFarms.length})
                          </h2>
                          <p className="panel-sub">
                            Các vùng trồng thuộc {user.organization_name}.
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
                              <th scope="col">Tên vùng trồng</th>
                              <th scope="col">Diện tích</th>
                              <th scope="col">Vị trí</th>
                              <th scope="col">Thao tác</th>
                            </tr>
                          </thead>
                          <tbody>
                            {loadingFarms ? (
                              <tr>
                                <td colSpan={4} className="cell-center">
                                  Đang tải danh sách vùng trồng...
                                </td>
                              </tr>
                            ) : filteredFarms.length === 0 ? (
                              <tr>
                                <td colSpan={4} className="cell-center">
                                  Không có vùng trồng nào khớp với bộ lọc.
                                </td>
                              </tr>
                            ) : (
                              filteredFarms.map((farm) => {
                                const areaNum = Number(farm.area_ha) || 0
                                return (
                                  <tr
                                    key={farm.id}
                                    className={
                                      editingFarm?.id === farm.id
                                        ? 'row-editing'
                                        : undefined
                                    }
                                  >
                                    <th scope="row" className="cell-strong">
                                      {farm.name}
                                    </th>
                                    <td>
                                      <span className="status-badge status-done">
                                        {areaNum.toFixed(2)} ha
                                      </span>
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

                  <FarmFormPanel
                    canWriteFarms={canWriteFarms}
                    editingFarm={editingFarm}
                    name={name}
                    areaHa={areaHa}
                    latitude={latitude}
                    longitude={longitude}
                    saving={saving}
                    formFeedback={formFeedback}
                    onNameChange={setName}
                    onAreaChange={setAreaHa}
                    onLatChange={setLatitude}
                    onLngChange={setLongitude}
                    onSubmit={handleSubmit}
                    onCancelEdit={resetForm}
                  />
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

            {activeTab === 'integrity' && <IntegrityPanel />}
          </main>
        </div>
      </div>
    </div>
  )
}
