import { useState } from 'react'
import type { IntegrityReport, LotEvent } from '../types'

interface EventTimelineProps {
  events: LotEvent[]
  lotName?: string
  loading?: boolean
  integrity?: IntegrityReport
}

const EVENT_LABELS: Record<string, string> = {
  harvest_recorded: 'Ghi nhận thu hoạch',
  handover_pending: 'Gửi yêu cầu bàn giao',
  handover_accepted: 'Đã nhận bàn giao',
  handover_rejected: 'Từ chối bàn giao',
  inspection: 'Kiểm tra chất lượng',
  transport: 'Vận chuyển',
  delivery: 'Giao hàng',
}

const PAYLOAD_LABELS: Record<string, string> = {
  product_name: 'Sản phẩm',
  harvested_on: 'Ngày thu hoạch',
  quantity: 'Khối lượng',
  unit: 'Đơn vị',
  to_organization_name: 'Đơn vị nhận',
  note: 'Ghi chú',
  rejection_reason: 'Lý do từ chối',
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' })
}

function visiblePayload(payload: Record<string, unknown>) {
  return Object.entries(payload).filter(([key, value]) => key in PAYLOAD_LABELS && value !== null && value !== '')
}

export function EventTimeline({ events, lotName, loading = false, integrity }: EventTimelineProps) {
  const [copiedHash, setCopiedHash] = useState<string | null>(null)

  const copyHash = async (hash: string) => {
    try {
      await navigator.clipboard.writeText(hash)
      setCopiedHash(hash)
      window.setTimeout(() => setCopiedHash(null), 1800)
    } catch {
      setCopiedHash(null)
    }
  }

  return (
    <section className="event-timeline" aria-labelledby="event-timeline-title">
      <header className="event-timeline-header">
        <div>
          <h2 id="event-timeline-title">Lịch sử sự kiện{lotName ? ` · ${lotName}` : ''}</h2>
          {!loading && <p className="panel-sub">{events.length} sự kiện</p>}
        </div>
      </header>

      {integrity && !integrity.valid && (
        <div className="alert-box alert-error" role="alert">
          Chuỗi có sai lệch tại sự kiện {integrity.first_invalid_sequence ?? 'không xác định'}.
        </div>
      )}

      {loading ? (
        <p className="event-timeline-empty" aria-busy="true">Đang tải lịch sử…</p>
      ) : events.length === 0 ? (
        <p className="event-timeline-empty">Chưa có sự kiện nào được ghi nhận.</p>
      ) : (
        <ol className="event-timeline-list">
          {events.map((event) => {
            const payload = visiblePayload(event.payload)
            return (
              <li className="event-timeline-item" key={event.id}>
                <div className="event-timeline-main">
                  <div className="event-timeline-title-row">
                    <span className="event-sequence">{event.sequence_number}</span>
                    <h3>{EVENT_LABELS[event.event_type] ?? event.event_type}</h3>
                    <time dateTime={event.recorded_at}>{formatDate(event.recorded_at)}</time>
                  </div>
                  <p className="event-organization">{event.organization_name}</p>
                  {payload.length > 0 && (
                    <dl className="event-payload-list">
                      {payload.map(([key, value]) => (
                        <div key={key}>
                          <dt>{PAYLOAD_LABELS[key]}</dt>
                          <dd>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  <details className="event-hash-details">
                    <summary>Thông tin xác minh</summary>
                    <dl>
                      <div><dt>Mã băm trước</dt><dd><code>{event.prev_hash}</code></dd></div>
                      <div><dt>Mã băm sự kiện</dt><dd><code>{event.event_hash}</code></dd></div>
                    </dl>
                    <button type="button" className="ds-button ds-button-secondary ds-button-sm" onClick={() => void copyHash(event.event_hash)}>
                      {copiedHash === event.event_hash ? 'Đã sao chép' : 'Sao chép mã băm'}
                    </button>
                  </details>
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
