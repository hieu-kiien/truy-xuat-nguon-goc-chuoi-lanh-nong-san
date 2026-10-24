import { useEffect, useState, useCallback, type FormEvent } from 'react'
import { confirmRecallHandling, getRecallNotifications } from '../services/api'
import type { RecallNotification } from '../types'

interface RecallAlertBannerProps {
  organizationId?: string
  canConfirmRecall?: boolean
  onOpenLot: (lotId: string) => void
  onNotify?: (message: string) => void
  initialNotifications?: RecallNotification[]
}

const CACHE_TTL_MS = 15_000
const cachedByOrg = new Map<string, RecallNotification[]>()
const lastFetchedAtByOrg = new Map<string, number>()
const inFlightByOrg = new Map<string, Promise<RecallNotification[]>>()

function fetchRecallNotificationsForOrg(
  cacheKey: string,
  force: boolean,
): Promise<RecallNotification[]> {
  const now = Date.now()
  const lastFetched = lastFetchedAtByOrg.get(cacheKey) ?? 0
  if (!force && cachedByOrg.has(cacheKey) && now - lastFetched < CACHE_TTL_MS) {
    return Promise.resolve(cachedByOrg.get(cacheKey) ?? [])
  }
  const existing = inFlightByOrg.get(cacheKey)
  if (existing && !force) {
    return existing
  }
  const promise = getRecallNotifications(false)
    .then((data) => {
      cachedByOrg.set(cacheKey, data)
      lastFetchedAtByOrg.set(cacheKey, Date.now())
      return data
    })
    .finally(() => {
      inFlightByOrg.delete(cacheKey)
    })
  inFlightByOrg.set(cacheKey, promise)
  return promise
}

export function RecallAlertBanner({
  organizationId,
  canConfirmRecall = true,
  onOpenLot,
  onNotify,
  initialNotifications,
}: RecallAlertBannerProps) {
  const cacheKey = organizationId ?? '__default__'
  const [notifications, setNotifications] = useState<RecallNotification[]>(
    () =>
      initialNotifications ??
      (organizationId ? (cachedByOrg.get(cacheKey) ?? []) : []),
  )
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [notes, setNotes] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const data = await fetchRecallNotificationsForOrg(
        cacheKey,
        true,
      )
      setNotifications(data)
    } catch {
      // Ignore background notification errors
    }
  }, [cacheKey])

  useEffect(() => {
    if (initialNotifications !== undefined) return
    let active = true
    const force = !organizationId
    fetchRecallNotificationsForOrg(cacheKey, force)
      .then((data) => {
        if (active) setNotifications(data)
      })
      .catch(() => {
        // Ignore background fetch failure
      })
    return () => {
      active = false
    }
  }, [cacheKey, initialNotifications, organizationId])

  const handleConfirm = async (
    event: FormEvent<HTMLFormElement>,
    recallId: string,
  ) => {
    event.preventDefault()
    if (confirmingId) return
    const noteText =
      (notes[recallId] ?? '').trim() ||
      'Đã cách ly và xử lý phần lô ảnh hưởng tại đơn vị.'
    setConfirmingId(recallId)
    setError(null)
    try {
      const updated = await confirmRecallHandling(recallId, noteText)
      onNotify?.(
        updated.status === 'completed'
          ? `Đã xác nhận xử lý và hoàn tất lệnh thu hồi ${updated.recall_code} (${updated.progress_text})`
          : `Đã ghi nhận xác nhận xử lý thu hồi ${updated.recall_code} (Tiến độ: ${updated.progress_text})`,
      )
      await refresh()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Không thể gửi xác nhận xử lý thu hồi.',
      )
    } finally {
      setConfirmingId(null)
    }
  }

  if (notifications.length === 0) {
    return null
  }

  const visibleItems = showAll ? notifications : notifications.slice(0, 1)
  const hiddenCount = Math.max(0, notifications.length - visibleItems.length)

  return (
    <section
      className="panel-card panel-box recall-alert-banner"
      aria-label="Thông báo lệnh thu hồi khẩn cấp"
    >
      <div className="recall-alert-header">
        <div className="recall-alert-title-group">
          <span className="recall-alert-badge-dot" aria-hidden="true" />
          <div>
            <h2 className="recall-alert-heading">
              Cảnh báo lệnh thu hồi liên quan ({notifications.length})
            </h2>
            <p className="panel-sub recall-alert-sub">
              Đơn vị của bạn có lô hàng nằm trong diện thu hồi. Vui lòng kiểm tra lô ảnh hưởng và xác nhận sau khi đã cách ly/xử lý.
            </p>
          </div>
        </div>

        <div className="recall-alert-header-actions">
          {notifications.length > 1 && !collapsed && (
            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm"
              onClick={() => setShowAll((prev) => !prev)}
            >
              {showAll
                ? 'Chỉ hiện 1 lệnh mới nhất ▴'
                : `Xem tất cả (${notifications.length} lệnh) ▾`}
            </button>
          )}
          <button
            type="button"
            className="ds-button ds-button-secondary ds-button-sm"
            onClick={() => setCollapsed((prev) => !prev)}
          >
            {collapsed ? `Mở chi tiết (${notifications.length}) ▾` : 'Thu gọn ▴'}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-error" role="alert" style={{ marginTop: '0.5rem' }}>
          {error}
        </div>
      )}

      {!collapsed && (
        <div className="recall-alert-list">
          {visibleItems.map((item) => (
            <div key={item.recall_id} className="recall-alert-item-card">
              <div className="recall-alert-item-left">
                <div className="recall-alert-meta-row">
                  <strong>Mã lệnh: {item.recall_code}</strong>
                  <span>· Lô gốc:</span>
                  <button
                    type="button"
                    className="ds-button ds-button-secondary ds-button-xs"
                    onClick={() => onOpenLot(item.root_lot_id)}
                  >
                    {item.root_lot_code ?? item.root_lot_name}
                  </button>
                  <span className="recall-alert-divider">·</span>
                  <span>
                    <strong>Lô của đơn vị bị ảnh hưởng ({item.affected_lots.length}): </strong>
                  </span>
                  {item.affected_lots.map((lot) => (
                    <button
                      key={lot.id}
                      type="button"
                      className="ds-button ds-button-secondary ds-button-xs"
                      onClick={() => onOpenLot(lot.id)}
                    >
                      {lot.lot_code ?? lot.name} ({lot.remaining_quantity} {lot.unit ?? 'kg'})
                      {lot.is_multi_source_merge ? ' · Gộp đa nguồn' : ''}
                    </button>
                  ))}
                </div>

                <p className="recall-alert-reason">
                  <strong>Lý do thu hồi:</strong> {item.reason}
                </p>
              </div>

              <div className="recall-alert-item-right">
                <div className="recall-alert-badges">
                  <span className="status-badge status-neutral">
                    Tiến độ: {item.progress_text} đơn vị
                  </span>
                  <span
                    className={`status-badge ${item.handling_status === 'confirmed' ? 'status-done' : 'status-warning'}`}
                  >
                    {item.handling_status === 'confirmed'
                      ? 'Đã xác nhận xử lý'
                      : 'Đang chờ xác nhận'}
                  </span>
                </div>

                {item.handling_status === 'pending' ? (
                  canConfirmRecall ? (
                    <form
                      onSubmit={(e) => void handleConfirm(e, item.recall_id)}
                      className="recall-alert-confirm-form"
                    >
                      <input
                        type="text"
                        className="ds-input recall-alert-input"
                        placeholder="Ghi chú xử lý (VD: Đã cách ly lô hàng tại kho đơn vị)"
                        value={notes[item.recall_id] ?? ''}
                        onChange={(e) =>
                          setNotes((prev) => ({
                            ...prev,
                            [item.recall_id]: e.target.value,
                          }))
                        }
                      />
                      <button
                        type="submit"
                        className="ds-button ds-button-brand ds-button-sm"
                        disabled={confirmingId === item.recall_id}
                      >
                        {confirmingId === item.recall_id
                          ? 'Đang lưu…'
                          : 'Xác nhận đã xử lý phần của đơn vị'}
                      </button>
                    </form>
                  ) : (
                    <p className="panel-sub" style={{ margin: 0 }}>
                      Đang chờ đơn vị giữ lô xác nhận cách ly và xử lý.
                    </p>
                  )
                ) : (
                  <p className="recall-alert-confirmed-note">
                    ✓ Đơn vị của bạn đã xác nhận xử lý
                    {item.note ? `: "${item.note}"` : '.'} (Sự kiện bất biến — không thể ghi đè)
                  </p>
                )}
              </div>
            </div>
          ))}

          {hiddenCount > 0 && (
            <button
              type="button"
              className="recall-alert-more-btn"
              onClick={() => setShowAll(true)}
            >
              + Còn {hiddenCount} lệnh thu hồi liên quan khác — Nhấn để xem tất cả
            </button>
          )}
        </div>
      )}
    </section>
  )
}
