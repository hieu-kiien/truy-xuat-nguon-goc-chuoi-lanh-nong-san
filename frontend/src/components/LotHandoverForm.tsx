import { useEffect, useState, type FormEvent } from 'react'
import { createHandover, getHandoverOrganizations } from '../services/api'
import type { Handover, Lot, OrganizationOption } from '../types'

export interface LotHandoverFormProps {
  lot: Pick<Lot, 'id' | 'lot_code' | 'name' | 'remaining_quantity' | 'product' | 'status'>
  currentOrganizationId?: string
  onSuccess?: (handover: Handover) => void
  onClose?: () => void
  onNotify?: (message: string) => void
}

export function LotHandoverForm({
  lot,
  currentOrganizationId,
  onSuccess,
  onClose,
  onNotify,
}: LotHandoverFormProps) {
  const [organizations, setOrganizations] = useState<OrganizationOption[]>([])
  const [loadingOrgs, setLoadingOrgs] = useState(true)
  const [recipientId, setRecipientId] = useState('')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getHandoverOrganizations()
      .then((orgs) => {
        if (!active) return
        // Tự động loại trừ tổ chức của chính người gửi (Tránh lỗi 400)
        const validRecipients = orgs.filter((org) => org.id !== currentOrganizationId)
        setOrganizations(validRecipients)
        if (validRecipients.length > 0) {
          setRecipientId(validRecipients[0].id)
        }
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải danh sách đơn vị nhận.')
      })
      .finally(() => {
        if (active) setLoadingOrgs(false)
      })
    return () => { active = false }
  }, [currentOrganizationId])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (saving || !recipientId || lot.status !== 'active') return
    setSaving(true)
    setError(null)
    try {
      const created = await createHandover({
        lot_id: lot.id,
        to_organization_id: recipientId,
        note: note.trim() || undefined,
      })
      const recipientName = organizations.find((o) => o.id === recipientId)?.name ?? 'đơn vị nhận'
      onNotify?.(`Đã gửi yêu cầu bàn giao lô ${lot.lot_code ?? lot.id.slice(0, 8)} tới ${recipientName}.`)
      onSuccess?.(created)
      onClose?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể gửi yêu cầu bàn giao.')
    } finally {
      setSaving(false)
    }
  }

  const unit = lot.product?.unit ?? 'kg'
  const displayName = lot.name && lot.name !== lot.product?.name ? lot.name : (lot.product?.name ?? lot.name)

  return (
    <form className="handover-create-form lot-detail-handover-form" onSubmit={(event) => void submit(event)}>
      <div className="lot-handover-current" style={{ marginBottom: '1rem' }}>
        <p><strong>Lô bàn giao:</strong> {lot.lot_code ?? lot.id.slice(0, 8)} · {displayName}</p>
        <p className="panel-sub">Khối lượng sẵn sàng: <strong>{lot.remaining_quantity} {unit}</strong></p>
      </div>

      {error && <p className="alert-box alert-error" role="alert">{error}</p>}

      <div className="form-field">
        <label htmlFor="lot-detail-recipient">Đơn vị nhận</label>
        <select
          id="lot-detail-recipient"
          value={recipientId}
          onChange={(event) => setRecipientId(event.target.value)}
          required
          disabled={loadingOrgs || organizations.length === 0}
        >
          {loadingOrgs ? (
            <option value="">Đang tải danh sách đơn vị...</option>
          ) : organizations.length === 0 ? (
            <option value="">Chưa có đơn vị đối tác liên kết</option>
          ) : (
            organizations.map((org) => (
              <option key={org.id} value={org.id}>{org.name}</option>
            ))
          )}
        </select>
      </div>

      <div className="form-field handover-note-field">
        <label htmlFor="lot-detail-note">Ghi chú (không bắt buộc)</label>
        <input
          id="lot-detail-note"
          value={note}
          maxLength={500}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Thông tin cần gửi bên nhận, ví dụ: Xe lạnh 2-6°C"
        />
        <div className="action-row" style={{ marginTop: '0.25rem' }}>
          <small className="panel-sub">Ghi chú mẫu:</small>
          {['Giao xe lạnh 2-6°C', 'Chuyển về kho Sa Đéc', 'Xuất bán lẻ siêu thị'].map((template) => (
            <button
              key={template}
              type="button"
              className="ds-button ds-button-secondary ds-button-sm"
              style={{ padding: '0.1rem 0.5rem', fontSize: '0.75rem' }}
              onClick={() => setNote(template)}
            >
              {template}
            </button>
          ))}
        </div>
      </div>

      <div className="action-row" style={{ marginTop: '1rem', justifyContent: 'flex-end' }}>
        {onClose && (
          <button type="button" className="ds-button ds-button-secondary" onClick={onClose} disabled={saving}>
            Hủy
          </button>
        )}
        <button
          type="submit"
          className="ds-button ds-button-brand"
          disabled={saving || !recipientId || organizations.length === 0}
        >
          {saving ? 'Đang gửi…' : 'Gửi yêu cầu bàn giao'}
        </button>
      </div>
    </form>
  )
}
