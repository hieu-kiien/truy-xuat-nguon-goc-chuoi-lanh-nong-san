import { useEffect, useState, useCallback, type FormEvent } from 'react'
import { confirmRecallHandling, getRecallNotifications } from '../services/api'
import type { RecallNotification } from '../types'

interface RecallAlertBannerProps {
  organizationId?: string
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
      'Đã gom hàng khỏi kệ và cách ly phần lô ảnh hưởng tại đơn vị.'
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

  return (
    <section
      className="panel-card panel-box"
      aria-label="Thông báo lệnh thu hồi khẩn cấp"
      style={{
        borderLeft: '4px solid #dc2626',
        marginBottom: '1rem',
        backgroundColor: 'rgba(239, 68, 68, 0.05)',
      }}
    >
      <div className="panel-head">
        <div>
          <h2 style={{ color: '#dc2626', margin: 0 }}>
            Cảnh báo lệnh thu hồi liên quan ({notifications.length})
          </h2>
          <p className="panel-sub" style={{ marginTop: '0.25rem' }}>
            Đơn vị của bạn có lô hàng nằm trong diện thu hồi. Vui lòng kiểm tra danh sách lô ảnh hưởng và xác nhận sau khi đã gom hàng khỏi kệ.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}

      <div className="info-stack" style={{ marginTop: '0.75rem' }}>
        {notifications.map((item) => (
          <div
            key={item.recall_id}
            className="panel-box"
            style={{
              border: '1px solid rgba(220, 38, 38, 0.25)',
              borderRadius: '0.5rem',
              padding: '0.85rem',
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
                <strong>Mã lệnh: {item.recall_code}</strong> · Lô gốc:{' '}
                <button
                  type="button"
                  className="ds-button ds-button-secondary ds-button-sm"
                  onClick={() => onOpenLot(item.root_lot_id)}
                >
                  {item.root_lot_code ?? item.root_lot_name}
                </button>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
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
            </div>

            <p style={{ margin: '0.5rem 0', fontSize: '0.9rem' }}>
              <strong>Lý do thu hồi:</strong> {item.reason}
            </p>

            <div style={{ margin: '0.5rem 0', fontSize: '0.9rem' }}>
              <strong>Lô của đơn vị bị ảnh hưởng ({item.affected_lots.length}): </strong>
              {item.affected_lots.map((lot) => (
                <button
                  key={lot.id}
                  type="button"
                  className="ds-button ds-button-secondary ds-button-sm"
                  style={{ marginRight: '0.35rem', marginBottom: '0.25rem' }}
                  onClick={() => onOpenLot(lot.id)}
                >
                  {lot.lot_code ?? lot.name} ({lot.remaining_quantity} {lot.unit ?? 'kg'})
                  {lot.is_multi_source_merge ? ' · Gộp đa nguồn' : ''}
                </button>
              ))}
            </div>

            {item.handling_status === 'pending' ? (
              <form
                onSubmit={(e) => void handleConfirm(e, item.recall_id)}
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  marginTop: '0.5rem',
                }}
              >
                <input
                  type="text"
                  className="ds-input"
                  style={{ flex: '1 1 260px' }}
                  placeholder="Ghi chú xử lý (VD: Đã gom hàng khỏi kệ và cách ly tại kho)"
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
              <p style={{ margin: '0.35rem 0 0', fontSize: '0.85rem', color: '#16a34a' }}>
                ✓ Đơn vị của bạn đã xác nhận xử lý
                {item.note ? `: "${item.note}"` : '.'} (Sự kiện bất biến — không thể ghi đè)
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
