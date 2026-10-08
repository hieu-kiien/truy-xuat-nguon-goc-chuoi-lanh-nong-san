import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  createHandover,
  getHandoverOrganizations,
  getIncomingHandovers,
  getLot,
  getLotHistory,
  getOutgoingHandovers,
} from '../services/api'
import type { EventHistory, Handover, Lot, OrganizationOption } from '../types'
import { EventTimeline } from './EventTimeline'

interface LotDetailPanelProps {
  lotId: string
  canReadEvents: boolean
  canCreateHandover: boolean
  canResolveHandover: boolean
  onBack: () => void
}

function displayLotCode(lot: Lot): string {
  return lot.lot_code ?? lot.id.slice(0, 8)
}

function statusLabel(status: Lot['status']): string {
  if (status === 'pending_handover') return 'Chờ xác nhận bàn giao'
  if (status === 'closed') return 'Đã đóng'
  return 'Đang lưu hành'
}

function handoverLabel(status: Handover['status']): string {
  if (status === 'accepted') return 'Đã nhận'
  if (status === 'rejected') return 'Đã từ chối'
  return 'Đang chờ xác nhận'
}

export function LotDetailPanel({
  lotId,
  canReadEvents,
  canCreateHandover,
  canResolveHandover,
  onBack,
}: LotDetailPanelProps) {
  const [lot, setLot] = useState<Lot | null>(null)
  const [history, setHistory] = useState<EventHistory | null>(null)
  const [organizations, setOrganizations] = useState<OrganizationOption[]>([])
  const [handover, setHandover] = useState<Handover | null>(null)
  const [loadedLotId, setLoadedLotId] = useState<string | null>(null)
  const [recipientId, setRecipientId] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const savingRef = useRef(false)

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
        setRecipientId((current) => current || details.organizations[0]?.id || '')
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
    return () => { active = false }
  }, [loadDetails, lotId])

  const sendHandover = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (savingRef.current || !lot || !recipientId || lot.status !== 'active') return
    savingRef.current = true
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const created = await createHandover({
        lot_id: lot.id,
        to_organization_id: recipientId,
        note: note.trim() || undefined,
      })
      setHandover(created)
      setLot((current) => current ? { ...current, status: 'pending_handover' } : current)
      setNote('')
      setNotice('Đã gửi yêu cầu. Lô vẫn do đơn vị của bạn giữ cho đến khi bên nhận xác nhận.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể gửi yêu cầu bàn giao.')
    } finally {
      savingRef.current = false
      setSaving(false)
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
        <section className="panel-card panel-box" aria-busy="true">Đang tải chi tiết lô…</section>
      ) : lot ? (
        <>
          <section className="panel-card panel-box" aria-labelledby="lot-detail-title">
            <div className="panel-head lot-detail-heading">
              <div>
                <p className="panel-sub">Chi tiết lô hàng</p>
                <h2 id="lot-detail-title"><code>{displayLotCode(lot)}</code></h2>
                <p className="panel-sub">{lot.product?.name ?? lot.name}</p>
                <p className="panel-sub">Đơn vị đang giữ: <strong>{lot.current_holder_organization_name}</strong></p>
              </div>
              <span className={`status-badge ${lot.status === 'active' ? 'status-done' : 'status-neutral'}`}>
                {statusLabel(lot.status)}
              </span>
            </div>
            <dl className="lot-detail-facts">
              <div><dt>Ngày thu hoạch</dt><dd>{lot.harvested_on ?? '—'}</dd></div>
              <div><dt>Khối lượng ban đầu</dt><dd>{lot.quantity ?? '—'} {lot.product?.unit ?? ''}</dd></div>
              <div><dt>Còn lại</dt><dd>{lot.remaining_quantity} {lot.product?.unit ?? ''}</dd></div>
              <div><dt>Mã vùng trồng</dt><dd><code>{lot.farm_id.slice(0, 8)}</code></dd></div>
            </dl>
          </section>

          <section className="panel-card panel-box" aria-labelledby="lot-handover-title">
            <div className="panel-head">
              <div>
                <h2 id="lot-handover-title">Bàn giao lô</h2>
                <p className="panel-sub">Đơn vị nhận cần xác nhận trước khi quyền giữ lô được chuyển.</p>
              </div>
              {handover && <span className={`handover-status handover-status-${handover.status}`}>{handoverLabel(handover.status)}</span>}
            </div>

            {handover && (
              <div className="lot-handover-current">
                <p>
                  {handover.from_organization_name} → {handover.to_organization_name}
                </p>
                {handover.note && <p className="panel-sub">Ghi chú: {handover.note}</p>}
                <time className="panel-sub" dateTime={handover.created_at}>
                  {new Date(handover.created_at).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' })}
                </time>
              </div>
            )}

            {canCreateHandover && lot.status === 'active' && (
              <form className="handover-create-form lot-detail-handover-form" onSubmit={(event) => void sendHandover(event)}>
                <div className="form-field">
                  <label htmlFor="lot-detail-recipient">Đơn vị nhận</label>
                  <select
                    id="lot-detail-recipient"
                    value={recipientId}
                    onChange={(event) => setRecipientId(event.target.value)}
                    required
                    disabled={organizations.length === 0}
                  >
                    <option value="">Chọn đơn vị nhận</option>
                    {organizations.map((organization) => (
                      <option key={organization.id} value={organization.id}>{organization.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-field handover-note-field">
                  <label htmlFor="lot-detail-note">Ghi chú (không bắt buộc)</label>
                  <input
                    id="lot-detail-note"
                    value={note}
                    maxLength={500}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder="Thông tin cần gửi bên nhận"
                  />
                </div>
                <button className="ds-button ds-button-brand" type="submit" disabled={saving || !recipientId}>
                  {saving ? 'Đang gửi…' : 'Gửi yêu cầu bàn giao'}
                </button>
              </form>
            )}
            {canCreateHandover && lot.status === 'pending_handover' && !handover && (
              <p className="panel-sub">Lô đang chờ xác nhận bàn giao.</p>
            )}
            {canCreateHandover && organizations.length === 0 && lot.status === 'active' && (
              <p className="panel-sub">Chưa có đơn vị nhận khả dụng để gửi bàn giao.</p>
            )}
          </section>

          {canReadEvents && history && (
            <section className="panel-card panel-box" aria-label={`Lịch sử lô ${displayLotCode(lot)}`}>
              <EventTimeline
                events={history.events}
                lotName={displayLotCode(lot)}
                loading={false}
                integrity={history.integrity}
              />
            </section>
          )}
        </>
      ) : null}
    </div>
  )
}
