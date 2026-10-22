import { useEffect, useState, useMemo, useCallback, type FormEvent } from 'react'
import {
  completeRecallOrder,
  confirmRecallHandling,
  getLotRecall,
  getRecallOrder,
  getRecalls,
  openRecallOrder,
  updateRecallLotFlag,
} from '../services/api'
import type { RecallReport, RecallLotItem, RecallOrder } from '../types'
import { lotStatusLabel } from '../types'

interface RecallPanelProps {
  lotId: string
  onOpenLot: (lotId: string) => void
  canOpenRecall?: boolean
  canManageRecall?: boolean
  canConfirmRecall?: boolean
  organizationId?: string
}

export function RecallPanel({
  lotId,
  onOpenLot,
  canOpenRecall = false,
  canManageRecall = false,
  canConfirmRecall = false,
  organizationId,
}: RecallPanelProps) {
  const [reportLotId, setReportLotId] = useState<string | null>(null)
  const [report, setReport] = useState<RecallReport | null>(null)
  const [recallOrder, setRecallOrder] = useState<RecallOrder | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'consumed' | 'closed'>('all')

  const [reasonInput, setReasonInput] = useState('')
  const [openingOrder, setOpeningOrder] = useState(false)
  const [confirmNote, setConfirmNote] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [completingOrder, setCompletingOrder] = useState(false)
  const [updatingLotId, setUpdatingLotId] = useState<string | null>(null)

  const loadData = useCallback(async (targetLotId: string) => {
    const [reportData, orders] = await Promise.all([
      getLotRecall(targetLotId),
      getRecalls().catch(() => [] as RecallOrder[]),
    ])
    const matchedOrder =
      orders.find(
        (o) =>
          o.root_lot_id === targetLotId ||
          o.affected_lots?.some((item) => item.id === targetLotId),
      ) ?? null
    return { reportData, matchedOrder }
  }, [])

  useEffect(() => {
    let active = true
    loadData(lotId)
      .then(({ reportData, matchedOrder }) => {
        if (!active) return
        setReport(reportData)
        setRecallOrder(matchedOrder)
        setReportLotId(lotId)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!active) return
        setError(err instanceof Error ? err.message : 'Không thể tải báo cáo thu hồi.')
        setReportLotId(lotId)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [loadData, lotId])

  const handleRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      if (recallOrder) {
        const refreshedOrder = await getRecallOrder(recallOrder.id)
        setRecallOrder(refreshedOrder)
        if (refreshedOrder.root_lot && refreshedOrder.summary) {
          setReport({
            root_lot: refreshedOrder.root_lot,
            summary: refreshedOrder.summary,
            descendants: refreshedOrder.descendants,
            affected_lots: refreshedOrder.affected_lots,
          })
        } else {
          const freshReport = await getLotRecall(lotId)
          setReport(freshReport)
        }
      } else {
        const { reportData, matchedOrder } = await loadData(lotId)
        setReport(reportData)
        setRecallOrder(matchedOrder)
      }
      setNotice('Đã tính toán lại danh sách hậu duệ và tiến độ thu hồi trực tiếp từ đồ thị phả hệ.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể làm mới danh sách thu hồi.')
    } finally {
      setRefreshing(false)
    }
  }

  const handleOpenRecall = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (openingOrder || reasonInput.trim().length < 20) return
    setOpeningOrder(true)
    setError(null)
    setNotice(null)
    try {
      const created = await openRecallOrder(lotId, reasonInput.trim())
      setRecallOrder(created)
      if (created.root_lot && created.summary) {
        setReport({
          root_lot: created.root_lot,
          summary: created.summary,
          descendants: created.descendants,
          affected_lots: created.affected_lots,
        })
      }
      setReasonInput('')
      setNotice(`Đã phát lệnh thu hồi ${created.recall_code}. Mọi tổ chức liên quan đã nhận thông báo.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể mở lệnh thu hồi.')
    } finally {
      setOpeningOrder(false)
    }
  }

  const handleConfirmHandling = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!recallOrder || confirming) return
    const noteText =
      confirmNote.trim() || 'Đã gom hàng khỏi kệ và cách ly phần lô ảnh hưởng tại đơn vị.'
    setConfirming(true)
    setError(null)
    setNotice(null)
    try {
      const updated = await confirmRecallHandling(recallOrder.id, noteText)
      setRecallOrder(updated)
      setConfirmNote('')
      setNotice(
        updated.status === 'completed'
          ? `Tất cả đơn vị đã xác nhận (${updated.progress_text}). Lệnh thu hồi ${updated.recall_code} tự động chuyển sang Hoàn tất!`
          : `Đã ghi nhận xác nhận xử lý của đơn vị. Tiến độ hiện tại: ${updated.progress_text}.`,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể xác nhận xử lý thu hồi.')
    } finally {
      setConfirming(false)
    }
  }

  const isLoading = loading || reportLotId !== lotId

  const activeLotsList = useMemo(() => {
    if (recallOrder && recallOrder.affected_lots && recallOrder.affected_lots.length > 0) {
      return recallOrder.affected_lots
    }
    return report?.affected_lots ?? []
  }, [recallOrder, report])

  const filteredLots = useMemo(() => {
    if (statusFilter === 'all') return activeLotsList
    if (statusFilter === 'active') return activeLotsList.filter((item) => item.status === 'active' || item.status === 'pending_handover')
    if (statusFilter === 'consumed') return activeLotsList.filter((item) => item.status === 'consumed')
    if (statusFilter === 'closed') return activeLotsList.filter((item) => item.status === 'closed')
    return activeLotsList
  }, [activeLotsList, statusFilter])

  const exportCsv = () => {
    if (!report) return
    const headers = [
      'Mã lô',
      'Tên lô',
      'Tầng',
      'Trạng thái',
      'Đơn vị đang giữ',
      'Loại đơn vị',
      'Địa điểm kho',
      'Địa chỉ kho',
      'Khối lượng ban đầu (kg)',
      'Còn lại trong kho (kg)',
      'Lượng có thể thu hồi (kg)',
      'Đã bán/tiêu thụ (kg)',
      'Gộp đa nguồn',
    ]

    const rows = activeLotsList.map((item) => [
      `"${item.lot_code ?? item.id}"`,
      `"${item.name.replace(/"/g, '""')}"`,
      item.tier,
      `"${lotStatusLabel(item.status)}"`,
      `"${item.current_holder_organization_name ?? '—'}"`,
      `"${item.holder_org_type ?? '—'}"`,
      `"${item.current_location?.name ?? '—'}"`,
      `"${item.current_location?.address ?? '—'}"`,
      item.quantity ?? '0.000',
      item.remaining_quantity,
      item.recoverable_quantity,
      item.consumed_quantity,
      item.is_multi_source_merge ? 'Có' : 'Không',
    ])

    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map((row) => row.join(','))].join('\r\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `danh-sach-thu-hoi-${report.root_lot.lot_code ?? lotId.slice(0, 8)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return <section className="panel-card panel-box" aria-busy="true">Đang tổng hợp danh sách thu hồi phả hệ…</section>
  }

  if (error && !report) {
    return <div className="alert-box alert-error" role="alert">{error}</div>
  }

  if (!report) {
    return <p>Không có dữ liệu thu hồi cho lô này.</p>
  }

  const summary = recallOrder?.summary ?? report.summary
  const root_lot = recallOrder?.root_lot ?? report.root_lot
  const myOrgProgress = recallOrder?.organizations_progress.find(
    (p) => p.organization_id === organizationId,
  )

  return (
    <section className="panel-card panel-box" aria-labelledby="recall-panel-title">
      <div className="panel-head">
        <div>
          <h2 id="recall-panel-title">Danh sách và Kế hoạch Thu hồi</h2>
          <p className="panel-sub">
            Truy vết xuôi động toàn bộ các nhánh phân phối từ lô <strong>{root_lot.lot_code ?? root_lot.name}</strong> (kể cả lô gộp đa nguồn) để xác định vị trí tồn kho và theo dõi tiến độ xác nhận.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="ds-button ds-button-secondary"
            onClick={() => void handleRefresh()}
            disabled={refreshing}
          >
            {refreshing ? 'Đang làm mới…' : 'Làm mới danh sách động'}
          </button>
          <button
            type="button"
            className="ds-button ds-button-secondary"
            onClick={exportCsv}
          >
            Xuất báo cáo CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert-box alert-success" role="status">
          {notice}
        </div>
      )}

      {/* Recall Order Status, Progress & Confirmation Section (N3-52 & N3-55) */}
      {recallOrder ? (
        <div
          className="panel-box"
          style={{
            marginTop: '1rem',
            marginBottom: '1rem',
            border:
              recallOrder.status === 'completed'
                ? '1px solid rgba(22, 163, 74, 0.35)'
                : '1px solid rgba(220, 38, 38, 0.35)',
            borderRadius: '0.5rem',
            padding: '1rem',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem',
            }}
          >
            <div>
              <h3 style={{ margin: 0 }}>
                Lệnh thu hồi: <code>{recallOrder.recall_code}</code>
              </h3>
              <p className="panel-sub" style={{ marginTop: '0.25rem' }}>
                Lý do: <strong>{recallOrder.reason}</strong>
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span className="status-badge status-neutral">
                Tiến độ xác nhận: {recallOrder.progress_text}
              </span>
              <span
                className={`status-badge ${recallOrder.status === 'completed' ? 'status-done' : 'status-warning'}`}
              >
                {recallOrder.status === 'completed' ? 'Hoàn tất' : 'Đang mở thu hồi'}
              </span>
              {canManageRecall && recallOrder.status === 'open' && (
                <button
                  type="button"
                  className="ds-button ds-button-secondary ds-button-sm"
                  disabled={completingOrder}
                  onClick={() => {
                    setCompletingOrder(true)
                    setError(null)
                    setNotice(null)
                    completeRecallOrder(recallOrder.id)
                      .then((updated) => {
                        setRecallOrder(updated)
                        setNotice(`Đã đóng và hoàn tất lệnh thu hồi ${updated.recall_code}.`)
                      })
                      .catch((err: unknown) => {
                        setError(
                          err instanceof Error
                            ? err.message
                            : 'Không thể hoàn tất lệnh thu hồi.',
                        )
                      })
                      .finally(() => setCompletingOrder(false))
                  }}
                >
                  {completingOrder ? 'Đang hoàn tất…' : 'Hoàn tất lệnh thu hồi'}
                </button>
              )}
            </div>
          </div>

          <div style={{ marginTop: '0.75rem', fontSize: '0.9rem' }}>
            <div>
              <strong>Đã xác nhận ({recallOrder.confirmed_organizations_count}/{recallOrder.total_organizations_count}): </strong>
              <span>
                {recallOrder.confirmed_organizations.length > 0
                  ? recallOrder.confirmed_organizations.join(' · ')
                  : 'Chưa có đơn vị nào xác nhận'}
              </span>
            </div>
            <div style={{ marginTop: '0.25rem' }}>
              <strong>Đang chờ xử lý ({recallOrder.pending_organizations.length}): </strong>
              <span style={{ color: recallOrder.pending_organizations.length > 0 ? '#dc2626' : '#16a34a' }}>
                {recallOrder.pending_organizations.length > 0
                  ? recallOrder.pending_organizations.join(' · ')
                  : 'Tất cả tổ chức liên quan đã hoàn tất xử lý'}
              </span>
            </div>
          </div>

          {/* Organization Progress Table */}
          {recallOrder.organizations_progress.length > 0 && (
            <div className="lineage-table-scroll" style={{ marginTop: '0.75rem' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tổ chức liên quan</th>
                    <th>Lô ảnh hưởng</th>
                    <th>Tồn kho cần thu hồi</th>
                    <th>Trạng thái xử lý</th>
                    <th>Ghi chú & Thời điểm xác nhận</th>
                  </tr>
                </thead>
                <tbody>
                  {recallOrder.organizations_progress.map((orgProg) => (
                    <tr key={orgProg.organization_id}>
                      <td>
                        <strong>{orgProg.organization_name}</strong>
                        {orgProg.organization_type && (
                          <span style={{ fontSize: '0.8rem', opacity: 0.75 }}>
                            {' '}
                            ({orgProg.organization_type})
                          </span>
                        )}
                      </td>
                      <td>{orgProg.affected_lot_codes.join(', ') || '—'}</td>
                      <td>
                        {orgProg.recoverable_quantity} {root_lot.unit ?? 'kg'}
                      </td>
                      <td>
                        <span
                          className={`status-badge ${orgProg.status === 'confirmed' ? 'status-done' : 'status-warning'}`}
                        >
                          {orgProg.status === 'confirmed' ? 'Đã xử lý' : 'Đang chờ'}
                        </span>
                      </td>
                      <td>
                        {orgProg.status === 'confirmed' ? (
                          <span>
                            {orgProg.note}
                            {orgProg.confirmed_at
                              ? ` (${new Date(orgProg.confirmed_at).toLocaleString('vi-VN')})`
                              : ''}
                          </span>
                        ) : (
                          <span style={{ opacity: 0.7 }}>Chưa xác nhận</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Action form for involved organization to confirm its part (N3-55 AC2) */}
          {canConfirmRecall &&
            recallOrder.status === 'open' &&
            myOrgProgress &&
            myOrgProgress.status === 'pending' && (
              <form
                onSubmit={(e) => void handleConfirmHandling(e)}
                style={{
                  marginTop: '0.85rem',
                  display: 'flex',
                  gap: '0.5rem',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                }}
              >
                <input
                  type="text"
                  className="ds-input"
                  style={{ flex: '1 1 280px' }}
                  placeholder="Ghi chú xác nhận đã gom hàng khỏi kệ / cách ly kho..."
                  value={confirmNote}
                  onChange={(e) => setConfirmNote(e.target.value)}
                />
                <button
                  type="submit"
                  className="ds-button ds-button-brand"
                  disabled={confirming}
                >
                  {confirming ? 'Đang ghi nhận…' : 'Xác nhận đã xử lý phần của đơn vị'}
                </button>
              </form>
            )}
        </div>
      ) : (
        canOpenRecall &&
        root_lot.status !== 'consumed' && (
          <form
            onSubmit={(e) => void handleOpenRecall(e)}
            className="panel-box"
            style={{
              marginTop: '1rem',
              marginBottom: '1rem',
              padding: '1rem',
              border: '1px solid rgba(217, 119, 6, 0.35)',
              borderRadius: '0.5rem',
            }}
          >
            <h3 style={{ marginTop: 0 }}>Phát lệnh thu hồi chính thức</h3>
            <p className="panel-sub">
              Nhập lý do thu hồi (tối thiểu 20 ký tự) để phong tỏa toàn bộ lô hậu duệ và gửi cảnh báo cho các tổ chức liên quan.
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
              <input
                type="text"
                className="ds-input"
                style={{ flex: '1 1 320px' }}
                placeholder="Lý do thu hồi (tối thiểu 20 ký tự, VD: Phát hiện dư lượng thuốc BVTV vượt ngưỡng)"
                value={reasonInput}
                onChange={(e) => setReasonInput(e.target.value)}
              />
              <button
                type="submit"
                className="ds-button ds-button-brand"
                disabled={openingOrder || reasonInput.trim().length < 20}
              >
                {openingOrder ? 'Đang phát lệnh…' : 'Mở lệnh thu hồi'}
              </button>
            </div>
          </form>
        )
      )}

      {summary.has_consumed_lot && (
        <div className="alert-box alert-error" role="alert">
          <strong>CẢNH BÁO KHẨN CẤP:</strong> Đã có <strong>{summary.total_consumed_kg} {root_lot.unit ?? 'kg'}</strong> sản phẩm được bán / tiêu thụ ra thị trường. Cần phát lệnh cảnh báo thu hồi tới các đại lý bán lẻ và người tiêu dùng!
        </div>
      )}

      {summary.has_multi_source_merge && (
        <div className="alert-box alert-warning" role="alert">
          <strong>LƯU Ý LÂY NHIỄM CHÉO:</strong> Có lô được gộp từ nhiều nguồn nông sản khác nhau trong chuỗi. Các sản phẩm gộp này đều nằm trong phạm vi nghi nhiễm.
        </div>
      )}

      {/* KPI Cards */}
      <div className="dashboard-kpi-grid">
        <div className="kpi-card">
          <div className="kpi-title">Tổng lô ảnh hưởng</div>
          <div className="kpi-value">{summary.total_affected_lots}</div>
          <div className="kpi-subtitle">Gồm lô gốc và {summary.total_descendants_count} lô hậu duệ</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-title">Tồn kho có thể thu hồi</div>
          <div className="kpi-value">{summary.total_recoverable_kg} <span className="kpi-unit">{root_lot.unit ?? 'kg'}</span></div>
          <div className="kpi-subtitle">Đang nằm tại các kho và điểm tập kết</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-title">Đã bán / Tiêu thụ</div>
          <div className="kpi-value" style={{ color: summary.has_consumed_lot ? '#dc2626' : 'inherit' }}>
            {summary.total_consumed_kg} <span className="kpi-unit">{root_lot.unit ?? 'kg'}</span>
          </div>
          <div className="kpi-subtitle">Đã xuất bán hoặc đưa vào tiêu thụ</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-title">Đơn vị liên quan</div>
          <div className="kpi-value">{summary.involved_organizations_count}</div>
          <div className="kpi-subtitle">Cần gửi thông báo phong tỏa kho</div>
        </div>
      </div>

      {/* Involved Organizations List */}
      <div className="panel-box" style={{ marginTop: '1rem' }}>
        <strong>Các tổ chức cần liên hệ thu hồi khẩn cấp: </strong>
        <span>{summary.involved_organizations.join(' · ') || 'Chưa xác định'}</span>
      </div>

      {/* Filter Toolbar */}
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '1.25rem', marginBottom: '0.75rem' }}>
        <span>Lọc theo trạng thái:</span>
        <button
          type="button"
          className={`ds-button ${statusFilter === 'all' ? 'ds-button-brand' : 'ds-button-secondary'} ds-button-sm`}
          onClick={() => setStatusFilter('all')}
        >
          Tất cả ({activeLotsList.length})
        </button>
        <button
          type="button"
          className={`ds-button ${statusFilter === 'active' ? 'ds-button-brand' : 'ds-button-secondary'} ds-button-sm`}
          onClick={() => setStatusFilter('active')}
        >
          Còn tồn kho ({activeLotsList.filter((item) => item.status === 'active' || item.status === 'pending_handover').length})
        </button>
        <button
          type="button"
          className={`ds-button ${statusFilter === 'consumed' ? 'ds-button-brand' : 'ds-button-secondary'} ds-button-sm`}
          onClick={() => setStatusFilter('consumed')}
        >
          Đã bán/tiêu thụ ({activeLotsList.filter((item) => item.status === 'consumed').length})
        </button>
        <button
          type="button"
          className={`ds-button ${statusFilter === 'closed' ? 'ds-button-brand' : 'ds-button-secondary'} ds-button-sm`}
          onClick={() => setStatusFilter('closed')}
        >
          Đã chia tách/gộp ({activeLotsList.filter((item) => item.status === 'closed').length})
        </button>
      </div>

      {/* Detailed Recall Lots Table */}
      <div className="lineage-table-scroll">
        <table className="data-table source-table">
          <thead>
            <tr>
              <th>Mã lô</th>
              <th>Tên lô</th>
              <th>Tầng</th>
              <th>Đang ở đâu (Đơn vị & Địa điểm kho)</th>
              <th>Còn bao nhiêu (Tồn kho)</th>
              <th>Đã bán bao nhiêu (Tiêu thụ)</th>
              <th>Trạng thái</th>
              <th>Pha trộn</th>
              {canManageRecall && recallOrder && recallOrder.status === 'open' && (
                <th>Phạm vi thu hồi</th>
              )}
            </tr>
          </thead>
          <tbody>
            {filteredLots.map((item: RecallLotItem) => {
              const orderLotEntry = recallOrder?.lots?.find((entry) => entry.lot_id === item.id)
              const isFlagged = orderLotEntry ? orderLotEntry.incident_flag : true
              return (
              <tr key={item.id} style={{ backgroundColor: item.status === 'consumed' ? 'rgba(239, 68, 68, 0.08)' : undefined }}>
                <td>
                  <button
                    type="button"
                    className="ds-button ds-button-secondary ds-button-sm"
                    onClick={() => onOpenLot(item.id)}
                  >
                    {item.lot_code ?? item.id.slice(0, 8)}
                  </button>
                </td>
                <td>
                  <strong>{item.name}</strong>
                  {item.id === root_lot.id && <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: '#dc2626' }}>[Lô khởi nguồn]</span>}
                </td>
                <td>
                  <span className="status-badge status-neutral">Tầng {item.tier}</span>
                </td>
                <td>
                  <div>
                    <strong>{item.current_holder_organization_name ?? '—'}</strong>
                    {item.holder_org_type && <span style={{ fontSize: '0.8rem', opacity: 0.8 }}> ({item.holder_org_type})</span>}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted, #666)' }}>
                    {item.current_location ? `${item.current_location.name} — ${item.current_location.address}` : 'Chưa gán vị trí kho cụ thể'}
                  </div>
                </td>
                <td>
                  <span style={{ fontWeight: item.recoverable_quantity !== '0.000' && item.recoverable_quantity !== '0' ? 'bold' : 'normal' }}>
                    {item.remaining_quantity} {item.unit ?? 'kg'}
                  </span>
                  {item.status === 'active' && <span style={{ display: 'block', fontSize: '0.75rem', color: '#16a34a' }}>Thu hồi ngay</span>}
                </td>
                <td>
                  <span style={{ fontWeight: item.consumed_quantity !== '0.000' && item.consumed_quantity !== '0' ? 'bold' : 'normal', color: item.status === 'consumed' ? '#dc2626' : 'inherit' }}>
                    {item.consumed_quantity} {item.unit ?? 'kg'}
                  </span>
                  {item.status === 'consumed' && <span style={{ display: 'block', fontSize: '0.75rem', color: '#dc2626' }}>Đã xuất bán</span>}
                </td>
                <td>
                  <span className={`status-badge ${item.status === 'active' ? 'status-done' : item.status === 'consumed' ? 'status-warning' : 'status-neutral'}`}>
                    {lotStatusLabel(item.status)}
                  </span>
                </td>
                <td>
                  {item.is_multi_source_merge ? (
                    <span style={{ color: '#d97706', fontSize: '0.8rem', fontWeight: 'bold' }}>Gộp đa nguồn</span>
                  ) : (
                    <span style={{ color: '#6b7280', fontSize: '0.8rem' }}>Đơn nguồn</span>
                  )}
                </td>
                {canManageRecall && recallOrder && recallOrder.status === 'open' && (
                  <td>
                    <button
                      type="button"
                      className="ds-button ds-button-secondary ds-button-sm"
                      disabled={updatingLotId === item.id || item.id === root_lot.id}
                      onClick={() => {
                        setUpdatingLotId(item.id)
                        setError(null)
                        setNotice(null)
                        updateRecallLotFlag(recallOrder.id, item.id, !isFlagged)
                          .then((updated) => {
                            setRecallOrder(updated)
                            setNotice(
                              `Đã cập nhật phạm vi thu hồi cho lô ${item.lot_code ?? item.name}.`,
                            )
                          })
                          .catch((err: unknown) => {
                            setError(
                              err instanceof Error
                                ? err.message
                                : 'Không thể cập nhật cờ ảnh hưởng của lô.',
                            )
                          })
                          .finally(() => setUpdatingLotId(null))
                      }}
                    >
                      {isFlagged ? 'Đang thu hồi (Loại trừ)' : 'Đã loại trừ (Đưa lại)'}
                    </button>
                  </td>
                )}
              </tr>
            )})}
          </tbody>
        </table>
      </div>
    </section>
  )
}
