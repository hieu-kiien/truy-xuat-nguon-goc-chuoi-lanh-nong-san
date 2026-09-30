import { useState, type FormEvent, type FocusEvent } from 'react'
import { API_BASE_URL, login } from '../services/api'
import type { SessionUser } from '../types'

interface LoginViewProps {
  backendOnline: boolean | null
  onLoginSuccess: (user: SessionUser) => void
  onNotify: (message: string) => void
}

export function LoginView({
  backendOnline,
  onLoginSuccess,
  onNotify,
}: LoginViewProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const syncAriaInvalid = (input: HTMLInputElement) => {
    if (!input.checkValidity()) {
      input.setAttribute('aria-invalid', 'true')
    } else {
      input.removeAttribute('aria-invalid')
    }
  }

  const handleBlur = (event: FocusEvent<HTMLInputElement>) => {
    syncAriaInvalid(event.currentTarget)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const inputs = form.querySelectorAll<HTMLInputElement>('input[required]')
    inputs.forEach(syncAriaInvalid)

    if (!form.checkValidity()) {
      return
    }

    setSubmitting(true)
    setErrorMessage(null)

    try {
      const user = await login({ email: email.trim(), password })
      onNotify(`Đăng nhập thành công: ${user.full_name}`)
      onLoginSuccess(user)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Không thể đăng nhập vào hệ thống'
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-hero section-pattern">
      <div className="login-container">
        <header className="login-banner">
          <div className="pill-tag">
            <span>
              {backendOnline === true
                ? 'Backend Online'
                : backendOnline === false
                  ? 'Backend Offline'
                  : 'Đang kết nối máy chủ'}
            </span>
            <span>&bull;</span>
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="pill-link"
            >
              OpenAPI Swagger
            </a>
          </div>
          <h1>AgroChain — Truy xuất Nguồn gốc Chuỗi lạnh</h1>
          <p>
            Nền tảng quản lý vùng trồng, giám sát nhiệt độ bảo quản và xác thực toàn vẹn
            chuỗi sự kiện nông sản
          </p>
        </header>

        <div className="auth-grid">
          <section className="sticker-panel auth-panel">
            <div className="panel-head">
              <h2>Đăng nhập hệ thống</h2>
              <p className="panel-sub">
                Xác thực phiên làm việc theo đơn vị thành viên trong chuỗi cung ứng
              </p>
            </div>

            {errorMessage && (
              <div className="alert-box alert-error" role="alert">
                {errorMessage}
              </div>
            )}

            <form onSubmit={handleSubmit} className="form-stack" noValidate>
              <div className="form-field">
                <label htmlFor="login-email">
                  Địa chỉ Email <span className="required-mark">*</span>
                </label>
                <input
                  id="login-email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onBlur={handleBlur}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    if (e.currentTarget.checkValidity()) {
                      e.currentTarget.removeAttribute('aria-invalid')
                    }
                  }}
                  placeholder="ten@tochuc.vn"
                  aria-errormessage="login-email-error"
                />
                <div id="login-email-error" className="field-error">
                  [!] Vui lòng nhập địa chỉ email hợp lệ.
                </div>
              </div>

              <div className="form-field">
                <label htmlFor="login-password">
                  Mật khẩu <span className="required-mark">*</span>
                </label>
                <input
                  id="login-password"
                  name="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onBlur={handleBlur}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    if (e.currentTarget.checkValidity()) {
                      e.currentTarget.removeAttribute('aria-invalid')
                    }
                  }}
                  placeholder="Nhập mật khẩu"
                  aria-errormessage="login-password-error"
                />
                <div id="login-password-error" className="field-error">
                  [!] Mật khẩu không được để trống.
                </div>
              </div>

              <button
                type="submit"
                className="ds-button ds-button-brand ds-button-block"
                disabled={submitting}
              >
                {submitting ? 'Đang xác thực phiên...' : 'Đăng nhập vào Không gian làm việc'}
              </button>

              <p className="security-footnote">
                Bảo mật Argon2id &amp; chống dò mật khẩu: Tự động khóa 15 phút nếu nhập
                sai 5 lần liên tiếp.
              </p>
            </form>
          </section>

          <aside className="sticker-panel auth-panel">
            <div className="panel-head">
              <h2>Bảo vệ phiên đăng nhập</h2>
              <p className="panel-sub">
                Phiên làm việc được xác thực bằng cookie HttpOnly; mã phiên không được
                đưa vào JavaScript hoặc lưu trong Web Storage.
              </p>
            </div>

            <div className="demo-cards-stack">
              <p className="demo-sticker-role">
                Mật khẩu được kiểm tra bằng Argon2id. Sau năm lần đăng nhập sai liên
                tiếp, tài khoản tạm khóa trong 15 phút.
              </p>
              <p className="demo-sticker-desc">
                Quyền truy cập và cách ly tổ chức được áp dụng phía máy chủ và
                PostgreSQL.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
