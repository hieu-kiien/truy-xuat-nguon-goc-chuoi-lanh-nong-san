import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../services/api'
import type { NotificationItem } from '../types'

const KIND_LABELS: Record<string, string> = {
  handover_pending: 'Bàn giao',
  recall_affected: 'Thu hồi',
  cold_chain_violation: 'Chuỗi lạnh',
}

interface NotificationBellProps {
  canRead: boolean
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function NotificationBell({ canRead }: NotificationBellProps) {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    if (!canRead) return
    setLoading(true)
    try {
      const payload = await getNotifications()
      setItems(payload.items)
      setUnreadCount(payload.unread_count)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải thông báo.',
      )
    } finally {
      setLoading(false)
    }
  }, [canRead])

  useEffect(() => {
    if (!canRead) return
    const timer = window.setTimeout(() => {
      void load()
    }, 200)
    return () => {
      window.clearTimeout(timer)
    }
  }, [canRead, load])

  useEffect(() => {
    if (!open) return
    const onDocumentClick = (event: MouseEvent) => {
      const target = event.target instanceof Node ? event.target : null
      if (target && containerRef.current?.contains(target)) return
      setOpen(false)
    }
    document.addEventListener('click', onDocumentClick)
    return () => {
      document.removeEventListener('click', onDocumentClick)
    }
  }, [open])

  if (!canRead) return null

  const openItem = async (item: NotificationItem) => {
    setOpen(false)
    if (item.read_at) return
    try {
      await markNotificationRead(item.id)
      setItems((previous) =>
        previous.map((entry) =>
          entry.id === item.id
            ? { ...entry, read_at: new Date().toISOString() }
            : entry,
        ),
      )
      setUnreadCount((previous) => Math.max(previous - 1, 0))
    } catch {
      // The link still opens the right page even when the read state fails.
    }
  }

  const markAll = async () => {
    try {
      await markAllNotificationsRead()
      const now = new Date().toISOString()
      setItems((previous) => previous.map((entry) => ({ ...entry, read_at: entry.read_at ?? now })))
      setUnreadCount(0)
    } catch {
      // Keep the badge as it is when the request fails.
    }
  }

  const badge = unreadCount > 99 ? '99+' : String(unreadCount)

  return (
    <div className="notification-bell" ref={containerRef}>
      <button
        type="button"
        className="notification-bell-btn"
        aria-label={
          unreadCount > 0
            ? `Thông báo, ${unreadCount} chưa đọc`
            : 'Thông báo, không có thông báo chưa đọc'
        }
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => {
          setOpen((previous) => !previous)
          if (!open) void load()
        }}
      >
        <span aria-hidden="true">🔔</span>
        {unreadCount > 0 && (
          <span className="notification-bell-badge" data-testid="notification-badge">
            {badge}
          </span>
        )}
      </button>

      {open && (
        <div className="notification-panel" role="dialog" aria-label="Trung tâm thông báo">
          <header className="notification-panel-head">
            <h2>Thông báo</h2>
            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-xs"
              onClick={() => void markAll()}
              disabled={unreadCount === 0}
            >
              Đánh dấu đã đọc tất cả
            </button>
          </header>

          {error && (
            <div className="alert-box alert-error" role="alert">
              {error}
            </div>
          )}
          {loading && items.length === 0 && <p role="status">Đang tải thông báo…</p>}
          {!loading && !error && items.length === 0 && (
            <p role="status">Bạn không có thông báo nào.</p>
          )}

          <ul className="notification-list">
            {items.map((item) => (
              <li
                key={item.id}
                className={item.read_at ? 'notification-item is-read' : 'notification-item'}
              >
                <a
                  href={
                    item.kind === 'recall_affected' && !item.link_path.includes('?')
                      ? `${item.link_path}?view=recall`
                      : item.link_path
                  }
                  onClick={() => {
                    void openItem(item)
                  }}
                >
                  <span className="notification-item-kind">
                    {KIND_LABELS[item.kind] ?? item.kind}
                  </span>
                  <span className="notification-item-title">{item.title}</span>
                  <span className="notification-item-body">{item.body}</span>
                  <time dateTime={item.created_at}>{formatTime(item.created_at)}</time>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
