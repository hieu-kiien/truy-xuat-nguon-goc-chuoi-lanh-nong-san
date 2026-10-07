import { useState } from 'react'
import type { IntegrityReport, LotEvent } from '../types'

interface EventTimelineProps {
  events: LotEvent[]
  lotName?: string
  loading?: boolean
  integrity?: IntegrityReport
}

export function EventTimeline({
  events,
  lotName,
  loading = false,
  integrity,
}: EventTimelineProps) {
  const [copiedHash, setCopiedHash] = useState<string | null>(null)

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash).then(() => {
      setCopiedHash(hash)
      setTimeout(() => setCopiedHash(null), 2000)
    })
  }

  const formatEventType = (type: string): { label: string; color: string } => {
    switch (type.toLowerCase()) {
      case 'harvest':
        return { label: 'Thu hoạch', color: '#16a34a' }
      case 'packaging':
        return { label: 'Sơ chế & Đóng gói', color: '#0284c7' }
      case 'storage_cold':
      case 'cold_storage':
        return { label: 'Bảo quản kho lạnh', color: '#2563eb' }
      case 'transport':
      case 'transit':
        return { label: 'Vận chuyển xe lạnh', color: '#d97706' }
      case 'inspection':
        return { label: 'Kiểm định chất lượng', color: '#9333ea' }
      case 'delivery':
        return { label: 'Bàn giao phân phối', color: '#059669' }
      default:
        return { label: type, color: '#4b5563' }
    }
  }

  const formatTimestamp = (iso: string) => {
    try {
      const date = new Date(iso)
      return date.toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return iso
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        marginTop: '1.5rem',
      }}
    >
      {/* Header and Immutability Guarantee Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div>
          <h3
            style={{
              fontSize: '1.25rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
              margin: 0,
            }}
          >
            Nhật ký sự kiện chuỗi lạnh {lotName ? `— Lô ${lotName}` : ''}
          </h3>
          <p
            style={{
              fontSize: '0.875rem',
              color: 'var(--text-secondary)',
              margin: '0.25rem 0 0 0',
            }}
          >
            {integrity
              ? `Đã kiểm tra ${integrity.checked_events} sự kiện trong chuỗi hash.`
              : `${events.length} sự kiện đã được ghi nhận.`}
          </p>
        </div>

        <div className="timeline-badges">
        <span
          className="status-badge status-neutral"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
          }}
          title="Sự kiện đã ghi không thể chỉnh sửa hoặc xoá"
        >
          <span aria-hidden="true">🔒</span>
          <span>Không sửa/xoá sự kiện</span>
        </span>
        {integrity && (
          <span className={`status-badge ${integrity.valid ? 'status-done' : 'status-danger'}`}>
            {integrity.valid
              ? 'Chuỗi hash hợp lệ'
              : `Sai lệch từ sự kiện ${integrity.first_invalid_sequence ?? 'không xác định'}`}
          </span>
        )}
        </div>
      </div>

      {loading && (
        <div
          style={{
            textAlign: 'center',
            padding: '2rem',
            color: 'var(--text-secondary)',
          }}
        >
          Đang tải dữ liệu chuỗi sự kiện...
        </div>
      )}

      {!loading && events.length === 0 && (
        <div
          style={{
            padding: '2rem',
            textAlign: 'center',
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: '0.5rem',
            border: '1px dashed var(--border-card)',
            color: 'var(--text-secondary)',
          }}
        >
          Chưa có sự kiện nào được ghi nhận cho lô hàng này.
        </div>
      )}

      {!loading && events.length > 0 && (
        <div
          style={{
            position: 'relative',
            paddingLeft: '2rem',
            borderLeft: '2px solid var(--border-card)',
            marginLeft: '0.75rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
          }}
        >
          {events.map((evt) => {
            const badge = formatEventType(evt.event_type)
            const isGenesis =
              evt.sequence_number === 1 ||
              evt.prev_hash === '0'.repeat(64)

            return (
              <div
                key={evt.id}
                style={{
                  position: 'relative',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-card)',
                  borderRadius: '0.5rem',
                  padding: '1rem',
                  boxShadow: 'var(--panel-shadow)',
                }}
              >
                {/* Timeline node marker */}
                <div
                  style={{
                    position: 'absolute',
                    left: '-2.625rem',
                    top: '1rem',
                    width: '1.25rem',
                    height: '1.25rem',
                    borderRadius: '50%',
                    backgroundColor: badge.color,
                    border: '3px solid var(--bg-card)',
                    boxShadow: '0 0 0 2px var(--border-card)',
                  }}
                />

                {/* Event header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    marginBottom: '0.5rem',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    <span
                      style={{
                        padding: '0.2rem 0.5rem',
                        backgroundColor: 'var(--bg-secondary)',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border-card)',
                      }}
                    >
                      #{evt.sequence_number}
                    </span>
                    <span
                      style={{
                        padding: '0.2rem 0.6rem',
                        backgroundColor: `${badge.color}15`,
                        color: badge.color,
                        borderRadius: '0.25rem',
                        fontSize: '0.8125rem',
                        fontWeight: 600,
                      }}
                    >
                      {badge.label}
                    </span>
                  </div>

                  <span
                    style={{
                      fontSize: '0.8125rem',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    {formatTimestamp(evt.recorded_at)}
                  </span>
                </div>

                {/* Event Payload */}
                {evt.payload && Object.keys(evt.payload).length > 0 && (
                  <div
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      borderRadius: '0.375rem',
                      padding: '0.625rem 0.875rem',
                      fontSize: '0.8125rem',
                      marginBottom: '0.75rem',
                      border: '1px solid var(--border-card)',
                    }}
                  >
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns:
                          'repeat(auto-fit, minmax(180px, 1fr))',
                        gap: '0.5rem',
                      }}
                    >
                      {Object.entries(evt.payload).map(([k, v]) => (
                        <div key={k}>
                          <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                            {k}:{' '}
                          </span>
                          <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                            {typeof v === 'object'
                              ? JSON.stringify(v)
                              : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Hash Chain Info */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.25rem',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                    backgroundColor: 'var(--bg-secondary)',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '0.25rem',
                    border: '1px solid var(--border-card)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.25rem',
                    }}
                  >
                    <span>
                      <strong style={{ color: 'var(--text-secondary)' }}>Prev: </strong>
                      {isGenesis ? (
                        <span style={{ color: 'var(--brand)', fontWeight: 600 }}>
                          [Genesis Block - 0x00...00]
                        </span>
                      ) : (
                        <span>
                          {evt.prev_hash.slice(0, 16)}...
                          {evt.prev_hash.slice(-8)}
                        </span>
                      )}
                    </span>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.25rem',
                    }}
                  >
                    <span>
                      <strong style={{ color: 'var(--text-secondary)' }}>Hash: </strong>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                        {evt.event_hash.slice(0, 16)}...
                        {evt.event_hash.slice(-8)}
                      </span>
                    </span>

                    <button
                      type="button"
                      onClick={() => handleCopyHash(evt.event_hash)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: copiedHash === evt.event_hash ? 'var(--brand)' : 'var(--brand-medium)',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        minHeight: '44px',
                        minWidth: '44px',
                        padding: '0.375rem 0.625rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRadius: '4px',
                      }}
                      title="Sao chép toàn bộ mã hash SHA-256"
                    >
                      {copiedHash === evt.event_hash ? '✓ Đã sao chép' : 'Sao chép Hash'}
                    </button>
                  </div>
                </div>

                {/* ARCHITECTURAL GUARANTEE: Strictly NO Edit/Delete buttons rendered */}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
