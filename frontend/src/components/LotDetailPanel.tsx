import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import {
  downloadLotReport,
  getHandoverOrganizations,
  getIncomingHandovers,
  getLot,
  getLotHistory,
  getOutgoingHandovers,
  peekCachedHandoverOrganizations,
  peekCachedIncomingHandovers,
  peekCachedLot,
  peekCachedLotHistory,
  peekCachedOutgoingHandovers,
} from '../services/api'
import type { EventHistory, Handover, Lot, LotDetail, OrganizationOption } from '../types'
import { EventTimeline } from './EventTimeline'
import { LotTransformForm } from './LotTransformForm'
import { LotLifecyclePanel } from './LotLifecyclePanel'
import { lotStatusLabel } from '../types'
import { EventCreateForm } from './EventCreateForm'
import { RecallPanel } from './RecallPanel'
import { LotQrPanel } from './LotQrPanel'
import { LotInputLotsPanel } from './LotInputLotsPanel'
import { ProcessingStepsPanel } from './ProcessingStepsPanel'
import { EditDialog } from './EditDialog'
import { LotHandoverForm } from './LotHandoverForm'
import { displayLotCode } from '../utils/qr'
import { lotReportFileName } from '../utils/report'

const LineagePanel = lazy(() => import('./LineagePanel').then((module) => ({ default: module.LineagePanel })))

interface LotDetailPanelProps {
  canManageDistribution: boolean
  canTransform: boolean
  canOpenRecall?: boolean
  canManageRecall?: boolean
  canConfirmRecall?: boolean
  isSystemAdmin?: boolean
  organizationId: string
  onOpenLot: (lotId: string) => void
  lotId: string
  canReadEvents: boolean
  canCreateEvents: boolean
  canCreateHandover: boolean
  canResolveHandover: boolean
  canReadInputLots?: boolean
  canDeclareInputLots?: boolean
  canReadProcessingSteps?: boolean
  canRecordProcessingSteps?: boolean
  onBack: () => void
}

function statusLabel(status: Lot['status']): string {
  return lotStatusLabel(status)
}

function handoverLabel(status: Handover['status']): string {
  if (status === 'accepted') return 'Đã nhận'
  if (status === 'rejected') return 'Đã từ chối'
  return 'Đang chờ xác nhận'
}

export function LotDetailPanel({
  canManageDistribution,
  canTransform,
  canOpenRecall = false,
  canManageRecall = false,
  canConfirmRecall = false,
  isSystemAdmin = false,
  organizationId,
  onOpenLot,
  lotId,
  canReadEvents,
  canCreateEvents,
  canCreateHandover,
  canResolveHandover,
  canReadInputLots = false,
  canDeclareInputLots = false,
  canReadProcessingSteps = false,
  canRecordProcessingSteps = false,
  onBack,
}: LotDetailPanelProps) {
  const initialCachedLot = peekCachedLot(lotId)
  const initialCachedHistory = canReadEvents ? peekCachedLotHistory(lotId) : null
  const initialCachedOrgs = canCreateHandover ? (peekCachedHandoverOrganizations() ?? []) : []
  const initialCachedHandover = (() => {
    const out = canCreateHandover ? (peekCachedOutgoingHandovers() ?? []) : []
    const inc = canResolveHandover ? (peekCachedIncomingHandovers() ?? []) : []
    return (
      [...out, ...inc]
        .filter((item) => item.lot_id === lotId)
        .sort((left, right) => right.created_at.localeCompare(left.created_at))[0] ?? null
    )
  })()

  const [lot, setLot] = useState<LotDetail | null>(() => initialCachedLot)
  const [history, setHistory] = useState<EventHistory | null>(() => initialCachedHistory)
  const [organizations, setOrganizations] = useState<OrganizationOption[]>(() => initialCachedOrgs)
  const [handover, setHandover] = useState<Handover | null>(() => initialCachedHandover)
  const [loadedLotId, setLoadedLotId] = useState<string | null>(() => (initialCachedLot ? lotId : null))
  const [loading, setLoading] = useState(() => !initialCachedLot)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [qrModalOpen, setQrModalOpen] = useState(false)
  const [exportingReport, setExportingReport] = useState(false)

  const task = new URLSearchParams(window.location.search).get('task')
  const [activeModal, setActiveModal] = useState<string | null>(() => task)
  const initialView = new URLSearchParams(window.location.search).get('view')
  const [view, setView] = useState(
    (initialView === 'history' && canReadEvents) ||
      initialView === 'origins' ||
      initialView === 'recall' ||
      (initialView === 'inputs' && canReadInputLots) ||
      (initialView === 'steps' && canReadProcessingSteps)
      ? initialView
      : 'overview'
  )

  const closeModal = useCallback(() => {
    setActiveModal(null)
    if (typeof window !== 'undefined' && window.location.search.includes('task=')) {
      const params = new URLSearchParams(window.location.search)
      params.delete('task')
      params.delete('parents')
      const search = params.toString() ? `?${params.toString()}` : ''
      window.history.replaceState({}, '', `${window.location.pathname}${search}`)
    }
  }, [])

  const loadDetails = useCallback(async () => {
    const [lotResult, historyResult, outgoing, incoming, orgOptions] = await Promise.all([
      getLot(lotId),
      canReadEvents ? getLotHistory(lotId) : Promise.resolve(null),
      canCreateHandover ? getOutgoingHandovers() : Promise.resolve([]),
      canResolveHandover ? getIncomingHandovers() : Promise.resolve([]),
      canCreateHandover ? getHandoverOrganizations() : Promise.resolve([]),
    ])
    const latest = [...outgoing, ...incoming]
      .filter((item) => item.lot_id === lotId)
      .sort((left, right) => right.created_at.localeCompare(left.created_at))[0]
    return { lot: lotResult, history: historyResult, organizations: orgOptions, handover: latest ?? null }
  }, [canCreateHandover, canReadEvents, canResolveHandover, lotId])

  useEffect(() => {
    let active = true
    loadDetails()
      .then((details) => {
        if (!active) return
        setLot(details.lot)
        setLoadedLotId(lotId)
        setHistory(details.history)
        setOrganizations(details.organizations)
        setHandover(details.handover)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!active) return
        setLot(null)
        setLoadedLotId(lotId)
        setError(err instanceof Error ? err.message : 'Không thể tải chi tiết lô.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [loadDetails, lotId])

  const exportReport = async () => {
    if (!lot || exportingReport) return
    setExportingReport(true)
    setError(null)
    setNotice(null)
    try {
      const blob = await downloadLotReport(lot.id)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = lotReportFileName(lot)
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 0)
      setNotice('Đã xuất hồ sơ truy xuất PDF kèm kết quả kiểm tra toàn vẹn.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể xuất hồ sơ PDF.')
    } finally {
      setExportingReport(false)
    }
  }

  return (
    <div className="info-stack lot-detail-page">
      <button type="button" className="ds-button ds-button-secondary lot-detail-back" onClick={onBack}>
        ← Danh sách lô
      </button>

      {error && <div className="alert-box alert-error" role="alert">{error}</div>}
      {notice && <div className="alert-box alert-success" role="status">{notice}</div>}
      {loading || loadedLotId !== lotId ? (
        <section className="panel-card panel-box" aria-busy="true">
          Đang tải chi tiết lô…
        </section>
      ) : lot ? (
        <>
          <section className="panel-card panel-box" aria-labelledby="lot-detail-title">
            <div className="panel-head lot-detail-heading">
              <div>
                <p className="panel-sub">Chi tiết lô hàng</p>
                <h2 id="lot-detail-title">
                  {lot.name && lot.name !== lot.product?.name ? lot.name : (lot.product?.name ?? lot.name)}
                </h2>
                <p className="panel-sub">
                  Mã truy xuất: <code>{displayLotCode(lot)}</code>
                </p>
                <p className="panel-sub">
                  Đơn vị đang giữ: <strong>{lot.current_holder_organization_name}</strong>
                </p>
              </div>
              <div className="lot-detail-heading-actions">
                <span className={`status-badge ${lot.status === 'active' ? 'status-done' : 'status-neutral'}`}>
                  {statusLabel(lot.status)}
                </span>
                {history?.integrity && (
                  <span
                    className={`status-badge ${history.integrity.valid ? 'status-done' : 'status-danger'}`}
                    title={`Đã kiểm tra ${history.integrity.checked_events} sự kiện trong chuỗi băm SHA-256`}
                  >
                    <span aria-hidden="true">{history.integrity.valid ? '✓' : '⚠'}</span>{' '}
                    {history.integrity.valid
                      ? 'Chuỗi băm toàn vẹn'
                      : `Sai lệch hash (#${history.integrity.first_invalid_sequence ?? '?'})`}
                  </span>
                )}
                <button
                  type="button"
                  className="ds-button ds-button-secondary lot-qr-btn"
                  onClick={() => setQrModalOpen(true)}
                >
                  Sinh mã QR
                </button>
                <button
                  type="button"
                  className="ds-button ds-button-secondary"
                  onClick={() => void exportReport()}
                  disabled={exportingReport}
                  aria-label="Xuất hồ sơ truy xuất PDF"
                >
                  {exportingReport ? 'Đang xuất…' : 'Xuất hồ sơ PDF'}
                </button>
              </div>
            </div>
            <dl className="lot-detail-facts">
              {canReadEvents && (
                <div>
                  <dt>Hoạt động & Toàn vẹn</dt>
                  <dd>
                    {lot.event_count} sự kiện
                    {history?.integrity && (
                      <small className="panel-sub" style={{ display: 'block', marginTop: '0.2rem' }}>
                        {history.integrity.valid
                          ? `✓ ${history.integrity.checked_events} hash hợp lệ`
                          : `⚠ Sai lệch #${history.integrity.first_invalid_sequence}`}
                      </small>
                    )}
                  </dd>
                </div>
              )}
              <div>
                <dt>Ngày thu hoạch</dt>
                <dd>{lot.harvested_on ?? '—'}</dd>
              </div>
              <div>
                <dt>Khối lượng ban đầu</dt>
                <dd>
                  {lot.quantity ?? '—'} {lot.product?.unit ?? ''}
                </dd>
              </div>
              <div>
                <dt>Còn lại</dt>
                <dd>
                  {lot.remaining_quantity} {lot.product?.unit ?? ''}
                </dd>
              </div>
              <div>
                <dt>Địa điểm hiện tại</dt>
                <dd>
                  {lot.current_location ? (
                    <>
                      {lot.current_location.name}
                      <br />
                      {lot.current_location.address}
                    </>
                  ) : (
                    'Chưa gán địa điểm'
                  )}
                </dd>
              </div>
              <div>
                <dt>Vùng trồng gốc</dt>
                <dd>
                  {(lot.root_farms ?? lot.direct_farms).map((farm) => farm.name).join(', ') ||
                    'Chưa có thông tin vùng trồng'}
                </dd>
              </div>
            </dl>
          </section>

          {/* Persistent 5 tabs — continuously mounted without unmounting */}
          <nav
            className="detail-tabs"
            role="tablist"
            aria-label="Thông tin lô"
            onKeyDown={(event) => {
              if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
              event.preventDefault()
              const tabs = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role=tab]'))
              const index = tabs.findIndex((tab) => tab === document.activeElement)
              const next =
                event.key === 'Home'
                  ? 0
                  : event.key === 'End'
                  ? tabs.length - 1
                  : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
              tabs[next]?.click()
              tabs[next]?.focus()
            }}
          >
            {(
              [
                'overview',
                ...(canReadEvents ? ['history'] : []),
                'origins',
                ...(canReadInputLots ? ['inputs'] : []),
                ...(canReadProcessingSteps ? ['steps'] : []),
              ] as const
            ).map((tab) => (
              <button
                key={tab}
                id={`tab-${tab}`}
                type="button"
                role="tab"
                aria-selected={view === tab}
                aria-controls="lot-tab-content"
                tabIndex={view === tab ? 0 : -1}
                onClick={() => setView(tab)}
              >
                {tab === 'overview'
                  ? 'Tổng quan'
                  : tab === 'history'
                  ? 'Lịch sử sự kiện'
                  : tab === 'inputs'
                  ? 'Vật tư đã dùng'
                  : tab === 'steps'
                  ? 'Công đoạn chế biến'
                  : 'Nguồn gốc'}
              </button>
            ))}
          </nav>

          <div key={view} id="lot-tab-content" role="tabpanel" aria-labelledby={`tab-${view}`} className="info-stack detail-tab-panel-animate">
            {view === 'overview' && (
              <section className="panel-card panel-box">
                <h2>Thao tác với lô</h2>
                <p className="panel-sub">Chọn thao tác phù hợp với lô nông sản đang giữ.</p>
                <div className="action-row">
                  {lot.status === 'active' && lot.current_holder_organization_id === organizationId && (
                    <>
                      {canTransform && (
                        <>
                          <a
                            href={`/lots/${lot.id}?task=split`}
                            className="ds-button ds-button-brand"
                            onClick={(e) => {
                              e.preventDefault()
                              setActiveModal('split')
                            }}
                          >
                            Tách lô
                          </a>
                          <a
                            href={`/lots/${lot.id}?task=merge`}
                            className="ds-button ds-button-secondary"
                            onClick={(e) => {
                              e.preventDefault()
                              setActiveModal('merge')
                            }}
                          >
                            Gộp lô
                          </a>
                        </>
                      )}
                      {canManageDistribution && (
                        <>
                          <a
                            href={`/lots/${lot.id}?task=move`}
                            className="ds-button ds-button-secondary"
                            onClick={(e) => {
                              e.preventDefault()
                              setActiveModal('move')
                            }}
                          >
                            Di chuyển lô
                          </a>
                          <a
                            href={`/lots/${lot.id}?task=consume`}
                            className="ds-button ds-button-secondary"
                            onClick={(e) => {
                              e.preventDefault()
                              setActiveModal('consume')
                            }}
                          >
                            Ghi nhận tiêu thụ
                          </a>
                        </>
                      )}
                      {canCreateHandover && (
                        <a
                          href={`/lots/${lot.id}?task=handover`}
                          className="ds-button ds-button-secondary"
                          onClick={(e) => {
                            e.preventDefault()
                            setActiveModal('handover')
                          }}
                        >
                          Bàn giao lô
                        </a>
                      )}
                      {canCreateEvents && (
                        <a
                          href={`/lots/${lot.id}?task=event`}
                          className="ds-button ds-button-secondary"
                          onClick={(e) => {
                            e.preventDefault()
                            setActiveModal('event')
                          }}
                        >
                          Ghi nhận hoạt động
                        </a>
                      )}
                    </>
                  )}
                  <a
                    href={`/lots/${lot.id}?task=recall`}
                    className="ds-button ds-button-secondary"
                    onClick={(e) => {
                      e.preventDefault()
                      setActiveModal('recall')
                    }}
                  >
                    Kế hoạch thu hồi
                  </a>
                </div>
                {lot.status !== 'active' && (
                  <p>
                    Lô {statusLabel(lot.status).toLocaleLowerCase('vi-VN')}. Xem lịch sử hoặc kế hoạch thu hồi để kiểm tra dòng chảy sản phẩm.
                  </p>
                )}
                {lot.current_holder_organization_id !== organizationId && (
                  <p>Bạn đang xem thông tin. Đơn vị đang giữ lô mới có thể thực hiện thao tác.</p>
                )}
                {handover && (
                  <p>
                    Bàn giao gần nhất: {handoverLabel(handover.status)} · {handover.from_organization_name} → {handover.to_organization_name}
                    {handover.overdue_at && handover.status === 'pending' ? ' · Quá hạn xác nhận' : ''}
                  </p>
                )}
              </section>
            )}

            {view === 'history' && history && (
              <section className="panel-card panel-box">
                <EventTimeline
                  key={lot.id}
                  lotId={lot.id}
                  nextCursor={history.next_cursor}
                  events={history.events}
                  lotName={displayLotCode(lot)}
                  loading={false}
                  integrity={history.integrity}
                />
              </section>
            )}

            {view === 'steps' && (
              <ProcessingStepsPanel
                key={lot.id}
                lotId={lot.id}
                canRecord={canRecordProcessingSteps}
                canManageCatalog={isSystemAdmin}
              />
            )}

            {view === 'inputs' && (
              <LotInputLotsPanel key={lot.id} lotId={lot.id} canDeclare={canDeclareInputLots} />
            )}

            {view === 'origins' && (
              <>
                <section className="panel-card panel-box" aria-label="Nguồn gốc và quan hệ trực tiếp">
                  <h2>Nguồn gốc và quan hệ</h2>
                  <p>
                    Vùng trồng liên quan trực tiếp:{' '}
                    {lot.direct_farms.map((farm) => farm.name).join(', ') || 'Xem vùng trồng gốc trong sơ đồ bên dưới'}
                  </p>
                  <p>
                    Lô mẹ:{' '}
                    {lot.parents.length === 0
                      ? 'Lô thu hoạch gốc'
                      : lot.parents.map((parent) => (
                          <button
                            key={parent.id}
                            type="button"
                            disabled={parent.historical_only}
                            title={parent.historical_only ? 'Xem lịch sử trong sơ đồ bên dưới' : undefined}
                            className="ds-button ds-button-secondary"
                            onClick={() => onOpenLot(parent.id)}
                          >
                            {displayLotCode(parent)}
                          </button>
                        ))}
                  </p>
                  <p>
                    Lô con:{' '}
                    {lot.children.length === 0
                      ? 'Chưa có lô con'
                      : lot.children.map((child) => (
                          <button
                            key={child.id}
                            type="button"
                            disabled={child.historical_only}
                            title={child.historical_only ? 'Xem lịch sử trong sơ đồ bên dưới' : undefined}
                            className="ds-button ds-button-secondary"
                            onClick={() => onOpenLot(child.id)}
                          >
                            {displayLotCode(child)}
                          </button>
                        ))}
                  </p>
                </section>

                <Suspense fallback={<section className="panel-card panel-box" aria-busy="true">Đang tải sơ đồ phả hệ…</section>}>
                  <LineagePanel key={`${lot.id}:${lot.status}:${lot.current_location_id}`} lotId={lot.id} onOpenLot={onOpenLot} />
                </Suspense>

                <div style={{ marginTop: '1rem' }}>
                  <RecallPanel
                    key={lot.id}
                    lotId={lot.id}
                    onOpenLot={onOpenLot}
                    canOpenRecall={canOpenRecall}
                    canManageRecall={canManageRecall}
                    canConfirmRecall={canConfirmRecall}
                    organizationId={organizationId}
                  />
                </div>
              </>
            )}
          </div>

          {/* 1. Split Modal */}
          {activeModal === 'split' && canTransform && (
            <EditDialog title="Tách lô nông sản" onClose={closeModal}>
              <LotTransformForm
                key={`split-${lot.id}`}
                initialMode="split"
                lot={lot}
                canManageDistribution={canManageDistribution}
                onClose={closeModal}
                onCompleted={(newLotId) => {
                  closeModal()
                  onOpenLot(newLotId)
                }}
                onNotify={(msg) => setNotice(msg)}
                onTransformed={async () => {
                  try {
                    const details = await loadDetails()
                    setLot(details.lot)
                    setHistory(details.history)
                    setHandover(details.handover)
                    setNotice('Đã tách lô thành công.')
                  } catch {
                    setError('Thao tác đã được lưu, nhưng chưa tải lại được thông tin lô nguồn.')
                  }
                }}
              />
            </EditDialog>
          )}

          {/* 2. Merge Modal */}
          {activeModal === 'merge' && canTransform && (
            <EditDialog title="Gộp lô cùng nông sản" onClose={closeModal}>
              <LotTransformForm
                key={`merge-${lot.id}`}
                initialMode="merge"
                lot={lot}
                canManageDistribution={canManageDistribution}
                onClose={closeModal}
                onCompleted={(newLotId) => {
                  closeModal()
                  onOpenLot(newLotId)
                }}
                onNotify={(msg) => setNotice(msg)}
                onTransformed={async () => {
                  try {
                    const details = await loadDetails()
                    setLot(details.lot)
                    setHistory(details.history)
                    setHandover(details.handover)
                    setNotice('Đã gộp lô thành công.')
                  } catch {
                    setError('Thao tác đã được lưu, nhưng chưa tải lại được thông tin lô nguồn.')
                  }
                }}
              />
            </EditDialog>
          )}

          {/* 3. Move Location Modal */}
          {activeModal === 'move' && canManageDistribution && (
            <EditDialog title="Di chuyển vị trí lô hàng" onClose={closeModal}>
              <LotLifecyclePanel
                key={`move-${lot.id}:${lot.current_location_id}`}
                operation="move"
                lot={lot}
                onCompleted={async () => {
                  const details = await loadDetails()
                  setLot(details.lot)
                  setHistory(details.history)
                  setHandover(details.handover)
                  setNotice('Đã di chuyển lô. Địa điểm hiện tại đã được cập nhật.')
                  closeModal()
                }}
              />
            </EditDialog>
          )}

          {/* 4. Consume Modal */}
          {activeModal === 'consume' && canManageDistribution && (
            <EditDialog title="Ghi nhận tiêu thụ lô hàng" onClose={closeModal}>
              <LotLifecyclePanel
                key={`consume-${lot.id}:${lot.current_location_id}`}
                operation="consume"
                lot={lot}
                onCompleted={async () => {
                  const details = await loadDetails()
                  setLot(details.lot)
                  setHistory(details.history)
                  setHandover(details.handover)
                  setNotice('Đã ghi nhận tiêu thụ và kết thúc lô.')
                  closeModal()
                }}
              />
            </EditDialog>
          )}

          {/* 5. Handover Modal */}
          {activeModal === 'handover' && canCreateHandover && (
            <EditDialog title="Bàn giao lô nông sản" onClose={closeModal}>
              <section className="panel-box" aria-labelledby="lot-handover-modal-title">
                <div className="panel-head" style={{ marginBottom: '1rem' }}>
                  <div>
                    <h3 id="lot-handover-modal-title">Khởi tạo bàn giao lô nông sản</h3>
                    <p className="panel-sub">Đơn vị nhận cần xác nhận trước khi quyền giữ lô được chuyển.</p>
                  </div>
                  {handover && (
                    <span className={`handover-status handover-status-${handover.status}`}>
                      {handoverLabel(handover.status)}
                    </span>
                  )}
                </div>

                {handover && (
                  <div className="lot-handover-current" style={{ marginBottom: '1rem' }}>
                    <p>
                      {handover.from_organization_name} → {handover.to_organization_name}
                    </p>
                    {handover.note && <p className="panel-sub">Ghi chú: {handover.note}</p>}
                    {handover.status === 'pending' && handover.overdue_at && (
                      <p className="alert-box alert-error" role="status">
                        Quá hạn xác nhận bàn giao · Bên nhận vẫn có thể xác nhận nhận lô.
                      </p>
                    )}
                    <time className="panel-sub" dateTime={handover.created_at}>
                      {new Date(handover.created_at).toLocaleString('vi-VN', {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })}
                    </time>
                  </div>
                )}

                {lot.current_holder_organization_id === organizationId && lot.status === 'active' && (
                  <LotHandoverForm
                    lot={lot}
                    currentOrganizationId={organizationId}
                    onClose={closeModal}
                    onNotify={(msg) => setNotice(msg)}
                    onSuccess={async (newHandover) => {
                      setHandover(newHandover)
                      setLot((curr) => (curr ? { ...curr, status: 'pending_handover' } : curr))
                      setNotice('Đã gửi yêu cầu bàn giao thành công.')
                      try {
                        const details = await loadDetails()
                        setLot(details.lot)
                        setHistory(details.history)
                        setHandover(details.handover)
                      } catch {
                        // preserve state
                      }
                    }}
                  />
                )}

                {lot.status === 'pending_handover' && (
                  <p className="panel-sub">Lô đang chờ xác nhận bàn giao từ phía đối tác nhận.</p>
                )}
                {organizations.length === 0 && lot.status === 'active' && (
                  <p className="panel-sub">Chưa có đơn vị nhận khả dụng để gửi bàn giao.</p>
                )}
              </section>
            </EditDialog>
          )}

          {/* 6. Event Creation Modal */}
          {activeModal === 'event' &&
            canCreateEvents &&
            lot.current_holder_organization_id === organizationId &&
            lot.status === 'active' && (
              <EditDialog title="Ghi nhận hoạt động chuỗi lạnh" onClose={closeModal}>
                <EventCreateForm
                  lot={lot}
                  onClose={closeModal}
                  onNotify={(msg) => setNotice(msg)}
                  onCreated={async () => {
                    closeModal()
                    try {
                      const details = await loadDetails()
                      setLot(details.lot)
                      setHistory(details.history)
                      setHandover(details.handover)
                      setNotice('Đã lưu sự kiện mới vào lịch sử chuỗi băm.')
                      setView('history')
                    } catch {
                      setError('Đã ghi nhận sự kiện nhưng chưa tải lại được lịch sử.')
                    }
                  }}
                />
              </EditDialog>
            )}

          {/* 7. Recall Modal */}
          {activeModal === 'recall' && (
            <EditDialog title="Kế hoạch thu hồi lô hàng" onClose={closeModal}>
              <RecallPanel
                key={`recall-${lot.id}`}
                lotId={lot.id}
                onOpenLot={(targetLotId) => {
                  closeModal()
                  onOpenLot(targetLotId)
                }}
                canOpenRecall={canOpenRecall}
                canManageRecall={canManageRecall}
                canConfirmRecall={canConfirmRecall}
                organizationId={organizationId}
              />
            </EditDialog>
          )}

          {/* QR Modal */}
          {qrModalOpen && (
            <EditDialog title="Sinh mã QR cho lô hàng" onClose={() => setQrModalOpen(false)}>
              <LotQrPanel lot={lot} />
            </EditDialog>
          )}
        </>
      ) : null}
    </div>
  )
}
