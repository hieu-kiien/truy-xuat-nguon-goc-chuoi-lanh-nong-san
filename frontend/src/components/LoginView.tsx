import { useState, type FormEvent, type FocusEvent } from 'react'
import {
  API_BASE_URL,
  DEMO_LOGIN_ENABLED,
  demoLogin,
  login,
} from '../services/api'
import { DEMO_ACCOUNTS, type DemoAccount, type SessionUser } from '../types'

interface LoginViewProps {
  backendOnline: boolean | null
  isDark: boolean
  onToggleTheme: () => void
  onLoginSuccess: (user: SessionUser) => void
  onNotify: (message: string) => void
}

export function LoginView({
  backendOnline,
  isDark,
  onToggleTheme,
  onLoginSuccess,
  onNotify,
}: LoginViewProps) {
  const [email, setEmail] = useState('grower@caudat.vn')
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

  const executeLogin = async (targetEmail: string, targetPassword: string) => {
    setSubmitting(true)
    setErrorMessage(null)
    try {
      const user = await login({
        email: targetEmail.trim(),
        password: targetPassword,
      })
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

  const executeDemoLogin = async (targetEmail: string) => {
    setSubmitting(true)
    setErrorMessage(null)
    try {
      const user = await demoLogin({ email: targetEmail.trim() })
      onNotify(`Đã mở phiên demo: ${user.full_name}`)
      onLoginSuccess(user)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Không thể mở phiên demo'
      )
    } finally {
      setSubmitting(false)
    }
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const inputs = form.querySelectorAll<HTMLInputElement>('input[required]')
    inputs.forEach(syncAriaInvalid)

    if (!form.checkValidity()) {
      return
    }

    await executeLogin(email, password)
  }

  const applyDemoAccount = (account: DemoAccount) => {
    setEmail(account.email)
    setPassword('')
    setErrorMessage(null)
    onNotify(`Đã điền email demo: ${account.email}`)
  }

  return (
    <div className="login-hero section-pattern">
      <div className="login-container">
        <header className="login-topbar">
          <div className="login-banner-compact">
            <h1>AgroChain — Hệ thống Truy xuất Nguồn gốc &amp; Giám sát Chuỗi lạnh</h1>
            <p>
              Kiến trúc Đa tổ chức (PostgreSQL RLS), Phân quyền RBAC và Xác thực
              Chuỗi Băm SHA-256
            </p>
          </div>

          <div className="action-row">
            <div className="pill-tag">
              <span>
                {backendOnline === true
                  ? 'API: Online'
                  : backendOnline === false
                    ? 'API: Offline'
                    : 'API: Đang kết nối'}
              </span>
              <span>&bull;</span>
              <a
                href={`${API_BASE_URL}/docs`}
                target="_blank"
                rel="noreferrer"
                className="pill-link"
              >
                Swagger Docs
              </a>
            </div>

            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm"
              onClick={onToggleTheme}
            >
              {isDark ? 'Giao diện: Sáng' : 'Giao diện: Tối'}
            </button>
          </div>
        </header>

        <div className="auth-grid">
          <div className="info-stack">
            <section className="panel-card auth-panel">
              <div className="panel-head">
                <h2>Đăng nhập Phiên Làm việc (N3-5)</h2>
                <span className="status-badge status-done">Argon2id + Cookie</span>
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
                  {submitting
                    ? 'Đang xác thực phiên...'
                    : 'Đăng nhập vào Không gian điều hành'}
                </button>

                <p className="security-footnote">
                  Chống Brute-force: Khóa tạm thời 15 phút nếu sai mật khẩu 5 lần
                  liên tiếp.
                </p>
              </form>
            </section>

            <section className="panel-card auth-panel">
              <div className="panel-head">
                <h2>Thông số Kỹ thuật Các Phân hệ Đã Tích hợp</h2>
              </div>
              <div className="info-grid-2">
                <div className="info-item">
                  <span className="info-item-label">N3-4 · Toàn vẹn Chuỗi lạnh</span>
                  <strong className="info-item-value">SHA-256 + RFC 8785</strong>
                </div>
                <div className="info-item">
                  <span className="info-item-label">N3-5 · Quản lý Phiên</span>
                  <strong className="info-item-value">Argon2id + SHA-256 Digest</strong>
                </div>
                <div className="info-item">
                  <span className="info-item-label">N3-6 · Đa tổ chức &amp; Phân quyền</span>
                  <strong className="info-item-value">PostgreSQL RLS</strong>
                </div>
                <div className="info-item">
                  <span className="info-item-label">N3-7 · Danh mục Vùng trồng</span>
                  <strong className="info-item-value">UUID Cố định + GPS WGS84</strong>
                </div>
              </div>
            </section>
          </div>

          <aside className="panel-card auth-panel">
            <div className="panel-head">
              <h2>Kịch bản Kiểm thử Nhanh (3 Tổ chức Demo)</h2>
              <span className="panel-sub">
                {DEMO_LOGIN_ENABLED
                  ? 'Phiên demo không sử dụng mật khẩu công khai'
                  : 'Demo một chạm đang tắt ở môi trường này'}
              </span>
            </div>

            <div className="demo-cards-stack">
              {DEMO_ACCOUNTS.map((account) => {
                const isSelected = email === account.email
                return (
                  <div
                    key={account.email}
                    className={`account-card ${
                      isSelected ? 'account-card-active' : ''
                    }`}
                  >
                    <div className="account-card-header">
                      <span className="account-card-title">{account.label}</span>
                      <code>{account.email}</code>
                    </div>
                    <div className="account-card-role">{account.roleText}</div>
                    <p className="account-card-desc">{account.description}</p>
                    <div className="account-card-actions">
                      <span className="panel-sub">
                        Đơn vị: <strong>{account.organization}</strong>
                      </span>
                      <div className="action-row">
                        <button
                          type="button"
                          className="ds-button ds-button-secondary ds-button-xs"
                          onClick={() => applyDemoAccount(account)}
                        >
                          Điền email
                        </button>
                        {DEMO_LOGIN_ENABLED && (
                          <button
                            type="button"
                            className="ds-button ds-button-brand ds-button-xs"
                            disabled={submitting}
                            onClick={() => {
                              setEmail(account.email)
                              setPassword('')
                              void executeDemoLogin(account.email)
                            }}
                          >
                            Vào demo
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
