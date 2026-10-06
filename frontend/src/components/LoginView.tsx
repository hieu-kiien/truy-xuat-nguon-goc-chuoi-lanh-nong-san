import { useState, type FormEvent } from 'react'
import { login } from '../services/api'
import type { SessionUser } from '../types'

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
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (submitting) return

    setSubmitting(true)
    setErrorMessage(null)
    try {
      const user = await login({ email: email.trim(), password })
      onNotify(`Xin chào ${user.full_name}`)
      onLoginSuccess(user)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Không thể đăng nhập. Vui lòng thử lại.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-root-container">
      <div className="login-split-card login-split-card-clean">
        <section className="login-hero-side login-hero-side-clean" aria-labelledby="login-brand-title">
          <div className="login-brand-row-clean">
            <div className="brand-logo-pill">
              <span className="brand-logo-mark" aria-hidden="true">A</span>
              <span className="brand-titles">
                <strong className="brand-name">AgroChain</strong>
                <span className="brand-version">Truy xuất nguồn gốc nông sản</span>
              </span>
            </div>
            <span className="status-indicator-badge" role="status">
              <span className={`status-dot ${backendOnline === true ? 'dot-online' : backendOnline === false ? 'dot-offline' : 'dot-pending'}`} />
              <span className="status-label">
                {backendOnline === true ? 'Đang kết nối' : backendOnline === false ? 'Chưa kết nối máy chủ' : 'Đang kiểm tra'}
              </span>
            </span>
          </div>

          <div className="hero-content-block">
            <p className="login-eyebrow">KHÔNG GIAN LÀM VIỆC</p>
            <h1 id="login-brand-title" className="hero-main-title">
              Theo dõi nguồn gốc và bàn giao nông sản
            </h1>
            <p className="hero-description">
              Quản lý lô hàng, ghi nhận đơn vị đang giữ và xem lịch sử sự kiện trên cùng một nơi.
            </p>
          </div>

          <ul className="login-capability-list">
            <li>Danh sách và thông tin lô hàng</li>
            <li>Ghi nhận yêu cầu bàn giao giữa các đơn vị</li>
            <li>Đối chiếu nhật ký theo quyền được cấp</li>
          </ul>
        </section>

        <section className="login-form-side login-form-side-clean" aria-labelledby="login-title">
          <header className="form-card-header">
            <p className="login-eyebrow">ĐĂNG NHẬP</p>
            <h2 id="login-title" className="form-title">Chào mừng bạn</h2>
            <p className="form-subtitle">Dùng tài khoản do đơn vị của bạn cấp.</p>
          </header>

          {errorMessage && <div className="auth-alert-box" role="alert">{errorMessage}</div>}

          <form onSubmit={(event) => void handleSubmit(event)} className="auth-clean-form">
            <div className="form-group-field">
              <label htmlFor="login-email" className="field-label">Email</label>
              <input
                id="login-email"
                name="email"
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="ten@donvi.vn"
                className="modern-input"
              />
            </div>

            <div className="form-group-field">
              <label htmlFor="login-password" className="field-label">Mật khẩu</label>
              <div className="login-password-row">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Nhập mật khẩu"
                  className="modern-input"
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                >
                  {showPassword ? 'Ẩn' : 'Hiện'}
                </button>
              </div>
            </div>

            <button type="submit" className="submit-login-button" disabled={submitting}>
              {submitting ? 'Đang đăng nhập…' : 'Đăng nhập'}
            </button>
          </form>

          <p className="login-help-text">
            Chưa có tài khoản hoặc quên mật khẩu? Liên hệ quản trị viên đơn vị.
          </p>

          <div className="login-card-footer">
            <button type="button" className="theme-switch-pill" onClick={onToggleTheme}>
              {isDark ? 'Giao diện sáng' : 'Giao diện tối'}
            </button>
            <span className="copyright-tag">AgroChain · Nhóm 3</span>
          </div>
        </section>
      </div>
    </main>
  )
}
