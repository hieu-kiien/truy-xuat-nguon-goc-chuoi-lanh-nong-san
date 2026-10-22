import { useEffect, useState, type FormEvent } from 'react'
import { acceptPublicInvitation, getPublicInvitation } from '../services/api'
import { ROLE_LABELS, type InvitationPreview } from '../types'

export function PublicInvitationView() {
  const token = new URLSearchParams(window.location.search).get('token')?.trim() ?? ''
  const [invitation, setInvitation] = useState<InvitationPreview | null>(null)
  const [loading, setLoading] = useState<boolean>(Boolean(token))
  const [error, setError] = useState<string | null>(
    token ? null : 'Thiếu mã lời mời trên đường dẫn.',
  )
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [acceptedEmail, setAcceptedEmail] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    let active = true
    getPublicInvitation(token)
      .then((data) => {
        if (!active) return
        setInvitation(data)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!active) return
        setError(
          err instanceof Error
            ? err.message
            : 'Lời mời không hợp lệ hoặc đã hết hạn.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [token])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || submitting) return
    if (!fullName.trim()) {
      setError('Cần nhập họ tên.')
      return
    }
    if (password.length < 12) {
      setError('Mật khẩu phải có ít nhất 12 ký tự.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await acceptPublicInvitation(token, {
        full_name: fullName.trim(),
        password,
      })
      setAcceptedEmail(result.email)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể chấp nhận lời mời.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="public-trace-shell" aria-label="Chấp nhận lời mời tham gia tổ chức">
      <section className="panel-card panel-box" style={{ maxWidth: '540px', margin: '3rem auto' }}>
        <header className="panel-head">
          <div>
            <h1>Lời mời tham gia tổ chức</h1>
            <p className="panel-sub">
              Hoàn tất thiết lập tài khoản để tham gia tổ chức trên AgroChain.
            </p>
          </div>
        </header>

        {loading && <p role="status" aria-busy="true">Đang kiểm tra lời mời…</p>}

        {error && (
          <div className="alert-box alert-error" role="alert">
            {error}
          </div>
        )}

        {acceptedEmail ? (
          <div className="info-stack">
            <div className="alert-box alert-success" role="status">
              Đã tạo tài khoản cho <strong>{acceptedEmail}</strong>. Bạn có thể đăng nhập ngay bây giờ.
            </div>
            <a href="/login" className="ds-button ds-button-brand">
              Đi tới trang đăng nhập
            </a>
          </div>
        ) : (
          invitation && (
            <form onSubmit={(event) => void handleSubmit(event)} className="form-stack">
              <dl className="lot-detail-facts">
                <div>
                  <dt>Tổ chức</dt>
                  <dd><strong>{invitation.organization_name}</strong></dd>
                </div>
                <div>
                  <dt>Email được mời</dt>
                  <dd>{invitation.email}</dd>
                </div>
                <div>
                  <dt>Vai trò</dt>
                  <dd>{ROLE_LABELS[invitation.role_code] ?? invitation.role_code}</dd>
                </div>
                <div>
                  <dt>Hạn sử dụng</dt>
                  <dd>
                    {invitation.expires_at
                      ? new Date(invitation.expires_at).toLocaleString('vi-VN')
                      : '—'}
                  </dd>
                </div>
              </dl>

              <div className="form-field">
                <label htmlFor="invitation-full-name">Họ và tên</label>
                <input
                  id="invitation-full-name"
                  type="text"
                  required
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Nguyễn Văn A"
                />
              </div>

              <div className="form-field">
                <label htmlFor="invitation-password">Mật khẩu mới (tối thiểu 12 ký tự)</label>
                <input
                  id="invitation-password"
                  type="password"
                  required
                  minLength={12}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Ít nhất 12 ký tự"
                />
              </div>

              <div className="action-row">
                <button
                  type="submit"
                  className="ds-button ds-button-brand"
                  disabled={submitting}
                >
                  {submitting ? 'Đang kích hoạt…' : 'Chấp nhận lời mời'}
                </button>
                <a href="/login" className="ds-button ds-button-secondary">
                  Về trang đăng nhập
                </a>
              </div>
            </form>
          )
        )}
      </section>
    </main>
  )
}
