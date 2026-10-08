import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  acceptHandover,
  createHandover,
  getHandoverOrganizations,
  getIncomingHandovers,
  getLots,
  getOutgoingHandovers,
  rejectHandover,
} from '../services/api'
import type { Handover, Lot, OrganizationOption } from '../types'

type HandoverView = 'incoming' | 'outgoing'

interface HandoversPanelProps {
  canCreate: boolean
  canResolve: boolean
  onPendingCountChange?: (count: number) => void
}

function statusText(status: Handover['status']) {
  if (status === 'accepted') return 'Đã nhận'
  if (status === 'rejected') return 'Đã từ chối'
  return 'Đang chờ'
}

function lotCode(lot: Pick<Handover, 'lot_code' | 'lot_id'>) {
  return lot.lot_code ?? lot.lot_id.slice(0, 8)
}

export function HandoversPanel({
  canCreate,
  canResolve,
  onPendingCountChange,
}: HandoversPanelProps) {
  const [incoming, setIncoming] = useState<Handover[]>([])
  const [outgoing, setOutgoing] = useState<Handover[]>([])
  const [organizations, setOrganizations] = useState<OrganizationOption[]>([])
  const [lots, setLots] = useState<Lot[]>([])
  const [view, setView] = useState<HandoverView>('incoming')
  const [lotId, setLotId] = useState('')
  const [organizationId, setOrganizationId] = useState('')
  const [note, setNote] = useState('')
  const [rejectingId, setRejectingId] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async (showLoader = false) => {
    if (showLoader) {
      setLoading(true)
      setError(null)
    }
    try {
      const [received, sent, orgOptions, lotPage] = await Promise.all([
        getIncomingHandovers(),
        getOutgoingHandovers(),
        getHandoverOrganizations(),
        getLots({ page_size: 100 }),
      ])
      setError(null)
      setIncoming(received)
      onPendingCountChange?.(received.filter((handover) => handover.status === 'pending').length)
      setOutgoing(sent)
      setOrganizations(orgOptions)
      setLots(lotPage.items.filter((lot) => lot.status === 'active'))
      setOrganizationId((current) => current || orgOptions[0]?.id || '')
      setLotId((current) => current || lotPage.items.find((lot) => lot.status === 'active')?.id || '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải thông tin bàn giao.')
    } finally {
      setLoading(false)
    }
  }, [onPendingCountChange])

  useEffect(() => {
    let active = true

    const initialLoad = async () => {
      try {
        const [received, sent, orgOptions, lotPage] = await Promise.all([
          getIncomingHandovers(),
          getOutgoingHandovers(),
          getHandoverOrganizations(),
          getLots({ page_size: 100 }),
        ])
        if (!active) return
        setIncoming(received)
        onPendingCountChange?.(received.filter((handover) => handover.status === 'pending').length)
        setOutgoing(sent)
        setOrganizations(orgOptions)
        setLots(lotPage.items.filter((lot) => lot.status === 'active'))
        setOrganizationId(orgOptions[0]?.id || '')
        setLotId(lotPage.items.find((lot) => lot.status === 'active')?.id || '')
        setError(null)
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải thông tin bàn giao.')
      } finally {
        if (active) setLoading(false)
      }
    }

    void initialLoad()
    return () => { active = false }
  }, [onPendingCountChange])

  const sendHandover = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (saving || !lotId || !organizationId) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      await createHandover({ lot_id: lotId, to_organization_id: organizationId, note })
      setNote('')
      setNotice('Đã gửi yêu cầu. Lô vẫn do đơn vị của bạn giữ cho đến khi bên nhận xác nhận.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể gửi yêu cầu bàn giao.')
    } finally {
      setSaving(false)
    }
  }

  const accept = async (handover: Handover) => {
    if (saving) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      await acceptHandover(handover.id)
      setNotice('Đã nhận lô ' + lotCode(handover) + '.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể xác nhận bàn giao.')
    } finally {
      setSaving(false)
    }
  }

  const reject = async (event: FormEvent<HTMLFormElement>, handover: Handover) => {
    event.preventDefault()
    if (saving || reason.trim().length < 10) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      await rejectHandover(handover.id, reason.trim())
      setReason('')
      setRejectingId(null)
      setNotice('Đã từ chối yêu cầu cho lô ' + lotCode(handover) + '.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể từ chối bàn giao.')
    } finally {
      setSaving(false)
    }
  }

  const rows = view === 'incoming' ? incoming : outgoing
  const pendingCount = incoming.filter((handover) => handover.status === 'pending').length
  const creationUnavailable = canCreate && !loading && lots.length === 0
  const listSummary = [
    pendingCount ? pendingCount + ' yêu cầu đang chờ bạn' : 'Theo dõi yêu cầu đến và đã gửi.',
    creationUnavailable ? 'Không có lô đang giữ để gửi bàn giao.' : '',
  ].filter(Boolean).join(' · ')
  const showEmptyMessage = !loading && !error && rows.length === 0

  return (
    <div className="info-stack">
      {canCreate && !creationUnavailable && <section className="panel-card panel-box" aria-labelledby="handover-create-title">
        <div className="panel-head">
          <div>
            <h2 id="handover-create-title">Gửi yêu cầu bàn giao</h2>
            <p className="panel-sub">Bên nhận cần xác nhận trước khi quyền giữ lô được chuyển.</p>
          </div>
        </div>
        <form className="handover-create-form" onSubmit={(event) => void sendHandover(event)}>
          <div className="form-field">
            <label htmlFor="handover-lot">Lô hàng đang giữ</label>
            <select id="handover-lot" value={lotId} onChange={(event) => setLotId(event.target.value)} required disabled={lots.length === 0}>
              <option value="">Chọn lô</option>
              {lots.map((lot) => <option key={lot.id} value={lot.id}>{lot.lot_code ?? lot.id.slice(0, 8)} · {lot.product?.name ?? lot.name}</option>)}
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="handover-recipient">Đơn vị nhận</label>
            <select id="handover-recipient" value={organizationId} onChange={(event) => setOrganizationId(event.target.value)} required disabled={organizations.length === 0}>
              <option value="">Chọn đơn vị</option>
              {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
            </select>
          </div>
          <div className="form-field handover-note-field">
            <label htmlFor="handover-note">Ghi chú (không bắt buộc)</label>
            <input id="handover-note" value={note} maxLength={500} onChange={(event) => setNote(event.target.value)} placeholder="Thông tin cần gửi bên nhận" />
          </div>
          <button className="ds-button ds-button-brand" type="submit" disabled={saving || lots.length === 0 || organizations.length === 0}>
            {saving ? 'Đang gửi…' : 'Gửi yêu cầu'}
          </button>
        </form>
      </section>}

      <section className="data-table-wrapper panel-card" aria-labelledby="handover-list-title">
        <div className="data-table-header handover-list-header">
          <div>
            <h2 id="handover-list-title" className="section-title">Yêu cầu bàn giao</h2>
            <p className="panel-sub">{listSummary}</p>
          </div>
          <button type="button" className="ds-button ds-button-secondary" onClick={() => void load(true)} disabled={loading}>Làm mới</button>
        </div>
        <div className="handover-view-tabs" role="tablist" aria-label="Lọc yêu cầu bàn giao">
          <button type="button" role="tab" aria-selected={view === 'incoming'} className={view === 'incoming' ? 'handover-view-active' : ''} onClick={() => setView('incoming')}>
            Cần xác nhận{pendingCount > 0 ? ' (' + pendingCount + ')' : ''}
          </button>
          <button type="button" role="tab" aria-selected={view === 'outgoing'} className={view === 'outgoing' ? 'handover-view-active' : ''} onClick={() => setView('outgoing')}>Đã gửi</button>
        </div>

        {error && <p className="alert-box alert-error table-alert" role="alert">{error}</p>}
        {notice && <p className="alert-box alert-success table-alert" role="status">{notice}</p>}
        {loading ? (
          <p className="handover-empty" aria-busy="true">Đang tải yêu cầu…</p>
        ) : showEmptyMessage ? (
          <p className="handover-empty">{view === 'incoming' ? 'Chưa có yêu cầu bàn giao gửi đến.' : 'Bạn chưa gửi yêu cầu bàn giao nào.'}</p>
        ) : rows.length === 0 ? null : (
          <div className="handover-list">
            {rows.map((handover) => (
              <article className="handover-card" key={handover.id}>
                <div className="handover-card-heading">
                  <div>
                    <h3>{lotCode(handover)} <span>· {handover.lot_name}</span></h3>
                    <p className="panel-sub">{view === 'incoming' ? 'Từ ' + handover.from_organization_name : 'Đến ' + handover.to_organization_name}</p>
                  </div>
                  <span className={'handover-status handover-status-' + handover.status}>{statusText(handover.status)}</span>
                </div>
                {handover.note && <p className="handover-note">{handover.note}</p>}
                {handover.rejection_reason && <p className="handover-rejection">Lý do từ chối: {handover.rejection_reason}</p>}
                <time className="panel-sub" dateTime={handover.created_at}>{new Date(handover.created_at).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' })}</time>
                {canResolve && view === 'incoming' && handover.status === 'pending' && (
                  <div className="handover-actions">
                    <button type="button" className="ds-button ds-button-brand" disabled={saving} onClick={() => void accept(handover)}>Xác nhận nhận lô</button>
                    {rejectingId === handover.id ? (
                      <form className="handover-reject-form" onSubmit={(event) => void reject(event, handover)}>
                        <label htmlFor={'handover-reason-' + handover.id}>Lý do từ chối (ít nhất 10 ký tự)</label>
                        <input id={'handover-reason-' + handover.id} value={reason} minLength={10} maxLength={1000} required onChange={(event) => setReason(event.target.value)} />
                        <button type="submit" className="ds-button ds-button-secondary" disabled={saving || reason.trim().length < 10}>Từ chối</button>
                        <button type="button" className="ds-button ds-button-secondary" onClick={() => { setRejectingId(null); setReason('') }}>Hủy</button>
                      </form>
                    ) : (
                      <button type="button" className="ds-button ds-button-secondary" disabled={saving} onClick={() => setRejectingId(handover.id)}>Từ chối</button>
                    )}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
