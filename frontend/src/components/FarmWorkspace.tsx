import { useState, useEffect, useCallback, useRef, type FormEvent } from 'react'
import {
  createFarm,
  createPiiAnonymizationRequest,
  getFarms,
  getIncomingHandovers,
  updateFarm,
} from '../services/api'
import {
  hasPermission,
  canManageDistribution,
  ROLE_LABELS,
  type Farm,
  type SessionUser,
} from '../types'
import { FarmFormPanel } from './FarmFormPanel'
import { ColdChainConfigPanel } from './ColdChainConfigPanel'
import { ColdChainStatsPanel } from './ColdChainStatsPanel'
import { OrganizationAdminPanel } from './OrganizationAdminPanel'
import { ShipmentCreateForm } from './ShipmentCreateForm'
import { ShipmentReadingForm } from './ShipmentReadingForm'
import { ShipmentTemperaturePanel } from './ShipmentTemperaturePanel'
import { IntegrityPanel } from './IntegrityPanel'
import { HandoversPanel } from './HandoversPanel'
import { LotsPanel } from './LotsPanel'
import { LotDetailPanel } from './LotDetailPanel'
import { LocationsPanel } from './LocationsPanel'
import { ProductManager } from './ProductManager'
import { RecallAlertBanner } from './RecallAlertBanner'
import { AuditPanel } from './AuditPanel'
import { WorkspaceSidebar } from './WorkspaceSidebar'
import { WorkspaceTopbar } from './WorkspaceTopbar'
import { ErrorBoundary } from './ErrorBoundary'
import { EditDialog } from './EditDialog'

export type WorkspaceTab =
  | 'lots'
  | 'products'
  | 'handovers'
  | 'overview'
  | 'security'
  | 'integrity'
  | 'cold-chain-stats'
  | 'cold-chain'
  | 'cold-chain-ops'
  | 'organization'

interface FarmWorkspaceProps {
  user: SessionUser
  activeTab: WorkspaceTab
  isDark: boolean
  onToggleTheme: () => void
  onTabChange: (tab: WorkspaceTab) => void
  onLogout: () => void
  onNotify: (message: string) => void
  selectedLotId: string | null
  onOpenLot: (lotId: string) => void
  onBackToLots: () => void
}

export function FarmWorkspace({
  user,
  activeTab,
  isDark,
  onToggleTheme,
  onTabChange,
  onLogout,
  onNotify,
  selectedLotId,
  onOpenLot,
  onBackToLots,
}: FarmWorkspaceProps) {
  const task = new URLSearchParams(window.location.search).get('task')
  const editId = new URLSearchParams(window.location.search).get('id')
  const canReadFarms = hasPermission(user.role, 'farms:read')
  const canWriteFarms = hasPermission(user.role, 'farms:write')
  const canReadLots = hasPermission(user.role, 'lots:read')
  const canCreateLots = hasPermission(user.role, 'lots:create')
  const canReadEvents = hasPermission(user.role, 'events:read')
  const canUseHandovers =
    hasPermission(user.role, 'handovers:create') ||
    hasPermission(user.role, 'handovers:resolve')
  const canResolveHandovers = hasPermission(user.role, 'handovers:resolve')
  const canVerifyEvents = hasPermission(user.role, 'events:verify')
  const canRequestPii = hasPermission(user.role, 'pii:request')
  const [piiFarm, setPiiFarm] = useState<Farm | null>(null)
  const [piiReason, setPiiReason] = useState('')
  const [piiBusy, setPiiBusy] = useState(false)
  const [piiFeedback, setPiiFeedback] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const [farms, setFarms] = useState<Farm[]>([])
  const [loadingFarms, setLoadingFarms] = useState<boolean>(canReadFarms)
  const [listError, setListError] = useState<string | null>(null)

  const [farmFormOpen, setFarmFormOpen] = useState(task === 'create' || task === 'edit')
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

  const [pendingHandoverCount, setPendingHandoverCount] = useState<number | null>(
    canResolveHandovers ? null : 0,
  )
  const contentRef = useRef<HTMLElement>(null)

  useEffect(() => {
    window.scrollTo(0, 0)
    contentRef.current?.focus({preventScroll: true})
  }, [activeTab, selectedLotId])

  const updatePendingHandoverCount = useCallback((count: number) => {
    setPendingHandoverCount(count)
  }, [])

  useEffect(() => {
    if (!canResolveHandovers) return
    let active = true
    getIncomingHandovers()
      .then((handovers) => {
        if (active) {
          setPendingHandoverCount(
            handovers.filter((handover) => handover.status === 'pending').length,
          )
        }
      })
      .catch(() => {
        if (active) setPendingHandoverCount(null)
      })
    return () => { active = false }
  }, [canResolveHandovers])

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
          if (task === 'edit') {
            const farm = data.find(item => item.id === editId)
            if (farm) { setEditingFarm(farm); setName(farm.name); setAreaHa(String(farm.area_ha)); setLatitude(String(farm.latitude)); setLongitude(String(farm.longitude)) }
            else setListError('Không tìm thấy vùng trồng cần sửa.')
          }
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
  }, [canReadFarms, task, editId])

  const resetForm = () => {
    setEditingFarm(null)
    setName('')
    setAreaHa('')
    setLatitude('')
    setLongitude('')
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (savingRef.current) return

    const trimmedName = name.trim()
    if (!trimmedName) {
      setFormFeedback({ type: 'error', message: 'Tên vùng trồng không được để trống.' })
      return
    }

    savingRef.current = true
    setSaving(true)
    setFormFeedback(null)

    try {
      const payload = {
        name: trimmedName,
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
      setFarmFormOpen(false)
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

  const filteredFarms = farms.filter((f) => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return true
    return (
      f.name.toLowerCase().includes(q) ||
      f.id.toLowerCase().includes(q) ||
      (f.latitude !== null && f.latitude !== undefined && String(f.latitude).includes(q)) ||
      (f.longitude !== null && f.longitude !== undefined && String(f.longitude).includes(q))
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
      <a className="skip-link" href="#main-content">Đến nội dung chính</a>
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
          sidebarOpen={sidebarOpen}
          onCloseSidebar={() => setSidebarOpen(false)}
          onTabChange={onTabChange}
          onLogout={onLogout}
          pendingHandoverCount={pendingHandoverCount}
        />

        <div className="dashboard-main">
          <WorkspaceTopbar
            user={user}
            activeTab={activeTab}
            canReadFarms={canReadFarms}
            searchQuery={searchQuery}
            isDark={isDark}
            onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
            onSearchChange={setSearchQuery}
            onRefresh={() => void refreshFarms()}
            onToggleTheme={onToggleTheme}
          />

          <main id="main-content" tabIndex={-1} ref={contentRef} className="dashboard-content">
            {hasPermission(user.role, 'recalls:read') && (
              <RecallAlertBanner
                onOpenLot={onOpenLot}
                onNotify={onNotify}
              />
            )}
            {activeTab === 'overview' && canReadFarms && (
              <section aria-label="Tóm tắt vùng trồng">
              <div className="stats-grid">
                <article className="stat-card panel-card">
                  <p className="stat-label">Đơn vị</p>
                  <p
                    className="stat-value stat-value-sans"
                    title={user.organization_name}
                  >
                    {user.organization_name}
                  </p>
                  <p className="stat-trend">{ROLE_LABELS[user.role]}</p>
                </article>

                <article className="stat-card panel-card">
                  <p className="stat-label">Vùng trồng thuộc đơn vị</p>
                  <p className="stat-value">
                    {loadingFarms ? 'Đang tải…' : `${farms.length} vùng`}
                  </p>
                  <p className="stat-trend">Trong đơn vị hiện tại</p>
                </article>

                <article className="stat-card panel-card">
                  <p className="stat-label">Tổng diện tích canh tác</p>
                  <p className="stat-value">
                    {loadingFarms ? 'Đang tải…' : `${totalAreaHa.toFixed(2)} ha`}
                  </p>
                  <p className="stat-trend">
                    {loadingFarms
                      ? 'Đang tải dữ liệu vùng trồng'
                      : farms.length > 0
                      ? `Trung bình ${avgAreaHa.toFixed(2)} ha / vùng`
                      : 'Chưa có dữ liệu diện tích'}
                  </p>
                </article>
              </div>

              </section>
            )}

            {activeTab === 'lots' && (
              selectedLotId ? (
                <LotDetailPanel
                    canManageDistribution={canManageDistribution(user)}
                    canTransform={hasPermission(user.role, 'lots:transform')}
                    canOpenRecall={hasPermission(user.role, 'recalls:open')}
                    canConfirmRecall={hasPermission(user.role, 'recalls:confirm')}
                    organizationId={user.organization_id}
                    onOpenLot={onOpenLot}
                  lotId={selectedLotId}
                  canReadEvents={canReadEvents}
                  canCreateEvents={hasPermission(user.role, 'events:create')}
                  canCreateHandover={hasPermission(user.role, 'handovers:create')}
                  canResolveHandover={canResolveHandovers}
                  canReadInputLots={hasPermission(user.role, 'input_lots:read')}
                  canDeclareInputLots={hasPermission(user.role, 'input_lots:create')}
                  canReadProcessingSteps={hasPermission(user.role, 'processing_steps:read')}
                  canRecordProcessingSteps={hasPermission(user.role, 'processing_steps:create')}
                  onBack={onBackToLots}
                />
              ) : (
                <>
                {canManageDistribution(user) && task !== 'create' && <LocationsPanel />}
                {task === 'locations' && !canManageDistribution(user) && <p role="status">Chỉ đơn vị phân phối có thể quản lý cửa hàng và kho.</p>}
                {task !== 'locations' && <LotsPanel
                  canReadLots={canReadLots}
                  canCreateLots={canCreateLots}
                  canTransform={hasPermission(user.role, 'lots:transform')}
                  organizationId={user.organization_id}
                  canReadEvents={canReadEvents}
                  onOpenLot={onOpenLot}
                />}
                </>
              )
            )}

            {activeTab === 'products' && (
              hasPermission(user.role, 'products:read') ? (
                <>
                  <ProductManager user={user} />
                  <ColdChainConfigPanel
                    canWrite={hasPermission(user.role, 'products:write')}
                  />
                </>
              ) : (
                <section className="panel-card panel-box" role="status">
                  Bạn không có quyền xem danh mục sản phẩm.
                </section>
              )
            )}

            {activeTab === 'handovers' && (
              canUseHandovers ? (
                <HandoversPanel
                  canCreate={hasPermission(user.role, 'handovers:create')}
                  canResolve={canResolveHandovers}
                  onPendingCountChange={updatePendingHandoverCount}
                />
              ) : (
                <section className="panel-card panel-box" role="status">
                  Tài khoản này không có quyền xử lý bàn giao.
                </section>
              )

            )}


            {activeTab === 'overview' && (
              <>
                {task && <a className="ds-button ds-button-secondary" href="/farms">← Danh sách vùng trồng</a>}
                {task && loadingFarms && <p aria-busy="true">Đang tải vùng trồng…</p>}
                {task && listError && <p role="alert">{listError}</p>}
                {task && !canWriteFarms && <p role="status">Tài khoản này không có quyền chỉnh sửa vùng trồng.</p>}
                {!farmFormOpen && formFeedback && <p role={formFeedback.type === 'error' ? 'alert' : 'status'}>{formFeedback.message}</p>}
                <div className="dashboard-split-main">
                  {(!canReadFarms ? (
                    <section className="panel-card panel-box" role="status">
                      Tài khoản này không có quyền xem hoặc chỉnh sửa vùng trồng.
                    </section>
                  ) : (
                    <section
                      className="data-table-wrapper panel-card"
                      aria-labelledby="farms-table-title"
                    >
                      <div className="data-table-header">
                        <div>
                          <h2 id="farms-table-title" className="section-title">
                            Vùng trồng ({filteredFarms.length}
                            )
                          </h2>
                          <p className="panel-sub">
                            Danh sách vùng trồng thuộc đơn vị hiện tại.
                          </p>
                        </div>
                        <span className="status-badge status-done">
                          {filteredFarms.length} vùng
                        </span>
                        {canWriteFarms && <button type="button" className="ds-button ds-button-brand" onClick={() => { resetForm(); setFormFeedback(null); setFarmFormOpen(true) }}>Thêm vùng trồng</button>}
                      </div>

                      {listError && (
                        <div className="alert-box alert-error table-alert">
                          {listError}
                        </div>
                      )}

                      <div className="table-scroll">
                        <table className="data-table farms-table">
                          <thead>
                            <tr>
                              <th scope="col">Vùng trồng</th>
                              <th scope="col">Diện tích</th>
                              <th scope="col">Tỷ trọng</th>
                              <th scope="col">Tọa độ GPS (WGS84)</th>
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
                                        {farm.latitude !== null && farm.latitude !== undefined && farm.longitude !== null && farm.longitude !== undefined ? (
                                          <>
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
                                          </>
                                        ) : (
                                          <span className="panel-sub">Đã ẩn danh vị trí</span>
                                        )}
                                      </div>
                                    </td>
                                    <td>
                                      {canWriteFarms && (
                                        <button type="button" className="ds-button ds-button-secondary" onClick={() => { setEditingFarm(farm); setName(farm.name); setAreaHa(String(farm.area_ha)); setLatitude(farm.latitude === null || farm.latitude === undefined ? '' : String(farm.latitude)); setLongitude(farm.longitude === null || farm.longitude === undefined ? '' : String(farm.longitude)); setFormFeedback(null); setFarmFormOpen(true) }}>Sửa<span className="sr-only"> {farm.name}</span></button>
                                      )}
                                      {canRequestPii && (
                                        <button type="button" className="ds-button ds-button-secondary" onClick={() => { setPiiFarm(farm); setPiiReason(''); setPiiFeedback(null) }}>Ẩn danh<span className="sr-only"> dữ liệu định danh của {farm.name}</span></button>
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
                  ))}

                  {piiFarm && (
                    <section className="panel-card" aria-label="Yêu cầu ẩn danh dữ liệu định danh">
                      <h3>Yêu cầu xoá dữ liệu định danh</h3>
                      <p className="panel-sub">
                        Vùng trồng <strong>{piiFarm.name}</strong>. Khi yêu cầu được quản trị hệ thống xác nhận, tên tổ chức, tên tài khoản, email và toạ độ vùng trồng sẽ được thay bằng dữ liệu ẩn danh. Chuỗi hash của các lô vẫn giữ nguyên và vẫn kiểm tra được.
                      </p>
                      <label className="form-field">
                        Lý do yêu cầu (không bắt buộc)
                        <textarea
                          value={piiReason}
                          rows={3}
                          maxLength={1000}
                          onChange={event => setPiiReason(event.target.value)}
                        />
                      </label>
                      {piiFeedback && (
                        <p className={piiFeedback.startsWith('Đã') ? 'panel-sub' : 'alert-box alert-error'} role="status">
                          {piiFeedback}
                        </p>
                      )}
                      <div className="action-row">
                        <button
                          type="button"
                          className="ds-button ds-button-brand"
                          disabled={piiBusy}
                          onClick={() => {
                            setPiiBusy(true)
                            setPiiFeedback(null)
                            createPiiAnonymizationRequest(piiFarm.id, piiReason.trim() || undefined)
                              .then(() => {
                                setPiiFeedback('Đã gửi yêu cầu ẩn danh. Quản trị hệ thống sẽ xác nhận phạm vi dữ liệu cần xoá.')
                                setPiiFarm(null)
                              })
                              .catch((err: unknown) => {
                                setPiiFeedback(err instanceof Error ? err.message : 'Không gửi được yêu cầu.')
                              })
                              .finally(() => setPiiBusy(false))
                          }}
                        >
                          {piiBusy ? 'Đang gửi…' : 'Gửi yêu cầu'}
                        </button>
                        <button type="button" className="ds-button ds-button-secondary" disabled={piiBusy} onClick={() => setPiiFarm(null)}>
                          Huỷ
                        </button>
                      </div>
                    </section>
                  )}

                  {farmFormOpen && canWriteFarms && <EditDialog title={editingFarm ? 'Sửa vùng trồng' : 'Thêm vùng trồng'} busy={saving} onClose={() => setFarmFormOpen(false)}><FarmFormPanel showChart={false}
                    canReadFarms={canReadFarms}
                    canWriteFarms={canWriteFarms}
                    farms={farms}
                    totalAreaHa={totalAreaHa}
                    maxAreaHa={maxAreaHa}
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
                    onApplyPreset={(preset) => {
                      setName(preset.name)
                      setAreaHa(preset.area_ha)
                      setLatitude(preset.latitude)
                      setLongitude(preset.longitude)
                      setFormFeedback(null)
                      onNotify(`Đã điền mẫu: ${preset.name}`)
                    }}
                    onSubmit={handleSubmit}
                    onCancelEdit={() => {
                      setFarmFormOpen(false)
                      resetForm()
                      setFormFeedback(null)
                    }}
                  /></EditDialog>}
                </div>

              </>
            )}

            {activeTab === 'security' && user.role === 'system_admin' && (
              <ErrorBoundary fallbackTitle="Không thể tải nhật ký thao tác">
                <AuditPanel />
              </ErrorBoundary>
            )}

            {activeTab === 'security' && user.role !== 'system_admin' && (
              <section className="panel-card panel-box" role="status">
                Chỉ quản trị hệ thống mới có quyền xem nhật ký thao tác.
              </section>
            )}

            {activeTab === 'integrity' && (

              <IntegrityPanel canReadLots={canReadLots} canVerify={canVerifyEvents} />

            )}

            {activeTab === 'cold-chain-stats' && (
              <ErrorBoundary fallbackTitle="Không thể tải thống kê vi phạm chuỗi lạnh">
                <ColdChainStatsPanel />
              </ErrorBoundary>
            )}

            {activeTab === 'cold-chain' && (
              <ErrorBoundary fallbackTitle="Không thể tải chuỗi nhiệt độ của chuyến vận chuyển">
                <ShipmentTemperaturePanel />
              </ErrorBoundary>
            )}

            {activeTab === 'cold-chain-ops' && (
              <ErrorBoundary fallbackTitle="Không thể tải thao tác chuỗi lạnh">
                <ShipmentCreateForm />
                <ShipmentReadingForm />
              </ErrorBoundary>
            )}

            {activeTab === 'organization' && (
              <ErrorBoundary fallbackTitle="Không thể tải thông tin quản trị tổ chức">
                <OrganizationAdminPanel
                  canManage={hasPermission(user.role, 'organizations:manage')}
                />
              </ErrorBoundary>
            )}
          </main>
        </div>
      </div>
    </div>
  )
}
