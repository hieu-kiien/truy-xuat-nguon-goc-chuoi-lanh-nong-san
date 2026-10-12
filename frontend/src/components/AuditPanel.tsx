import { useEffect, useState } from 'react'
import { request } from '../services/api'

interface AuditEntry {
  id: string
  recorded_at: string
  actor_name: string | null
  actor_authenticated: boolean
  organization_name: string | null
  client_ip: string | null
  action: string
  object_type: string
  object_id: string | null
  outcome: string
  status_code: number
  reason: string | null
}
interface AuditPage { items: AuditEntry[]; next_cursor: string | null }

export function AuditPanel() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    let cancelled = false
    request<AuditPage>('/api/v1/audit/?limit=25').then(page => {
      if (!cancelled) { setEntries(page.items); setCursor(page.next_cursor); setError('') }
    }).catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : 'Không tải được nhật ký.') })
      .finally(() => { if (!cancelled) setBusy(false) })
    return () => { cancelled = true }
  }, [revision])
  async function loadMore() {
    if (!cursor || busy) return
    setBusy(true)
    try {
      const page = await request<AuditPage>(`/api/v1/audit/?limit=25&cursor=${encodeURIComponent(cursor)}`)
      setEntries(previous => [...previous, ...page.items])
      setCursor(page.next_cursor)
      setError('')
    } catch (e) { setError(e instanceof Error ? e.message : 'Không tải được nhật ký.') }
    finally { setBusy(false) }
  }
  return <section className="panel-card data-table-wrapper">
    <div className="data-table-header">
      <div><h2 className="section-title">Nhật ký thao tác</h2><p className="panel-sub">Ghi nhận thao tác và kết quả xác thực. Nhật ký chỉ đọc; thời gian hiển thị theo thiết bị của bạn.</p></div>
      <button type="button" className="ds-button ds-button-sm" disabled={busy} onClick={() => { setBusy(true); setRevision(n => n + 1) }}>Làm mới nhật ký</button>
    </div>
    {error && <div className="alert-box alert-error" role="alert">{error}</div>}
    <div className="table-scroll"><table className="data-table audit-table">
      <thead><tr><th>Thời gian</th><th>Người thao tác</th><th>Đơn vị</th><th>IP</th><th>Thao tác / đối tượng</th><th>Kết quả</th></tr></thead>
      <tbody>{entries.map(entry => <tr key={entry.id}>
        <td>{new Date(entry.recorded_at).toLocaleString('vi-VN')}</td>
        <td>{entry.actor_name ?? 'Chưa xác định'}{!entry.actor_authenticated && <div className="panel-sub">Chưa xác thực</div>}</td>
        <td>{entry.organization_name ?? '—'}</td><td>{entry.client_ip ?? '—'}</td>
        <td><strong>{entry.action}</strong><div className="panel-sub">{entry.object_type}</div>{entry.object_id && <code>{entry.object_id}</code>}</td>
        <td><span className={`status-badge ${entry.outcome === 'success' ? 'status-done' : 'status-neutral'}`}>{entry.outcome === 'success' ? 'Thành công' : entry.outcome === 'denied' ? 'Từ chối' : 'Lỗi'} · {entry.status_code}</span>{entry.reason && <div className="panel-sub">{entry.reason}</div>}</td>
      </tr>)}</tbody>
    </table></div>
    {!entries.length && !error && <p className="panel-sub" aria-busy={busy}>{busy ? 'Đang tải nhật ký…' : 'Chưa có nhật ký để hiển thị.'}</p>}
    {cursor && <div className="action-row"><button type="button" className="ds-button ds-button-sm" disabled={busy} onClick={() => void loadMore()}>{busy ? 'Đang tải…' : 'Xem thêm nhật ký'}</button></div>}
  </section>
}
