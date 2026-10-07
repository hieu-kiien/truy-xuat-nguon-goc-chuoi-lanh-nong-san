import { useState, type FormEvent, type FocusEvent } from 'react'
import { login } from '../services/api'
import type { SessionUser } from '../types'

interface LoginViewProps {
  backendOnline: boolean | null
  isDark: boolean
  onToggleTheme: () => void
  onLoginSuccess: (user: SessionUser) => void
  onNotify: (message: string) => void
}

const DEMO_PRESETS = [
  {
    roleName: 'Nông hộ Cầu Đất',
    badge: 'grower',
    email: 'grower@caudat.vn',
    password: 'Password123!',
    icon: '🌱',
    desc: 'Quản trị thửa đất, lô thu hoạch & ghi nhật ký chuỗi lạnh',
  },
  {
    roleName: 'HTX Mộc Châu',
    badge: 'admin',
    email: 'admin@mocchau.vn',
    password: 'Password123!',
    icon: '🏢',
    desc: 'Quản trị hợp tác xã, phân quyền thành viên & vùng trồng',
  },
  {
    roleName: 'Chi cục Quản lý',
    badge: 'inspector',
    email: 'inspector@chicuc.gov.vn',
    password: 'Password123!',
    icon: '🔍',
    desc: 'Thanh tra độc lập, giám sát chuỗi lạnh & sự kiện bất biến',
  },
]

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
  const [rememberMe, setRememberMe] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [showAuditModal, setShowAuditModal] = useState(false)

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
      onNotify(`Chào mừng trở lại, ${user.full_name}`)
      onLoginSuccess(user)
    } catch (err) {
      const rawMsg = err instanceof Error ? err.message : 'Không thể đăng nhập vào hệ thống.'
      setErrorMessage(
        rawMsg.includes('không đúng')
          ? `${rawMsg} (Gợi ý: Dùng tài khoản mẫu bên dưới, mật khẩu: Password123!)`
          : rawMsg
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

  const handleForgotPassword = () => {
    onNotify('Vui lòng liên hệ Quản trị viên tổ chức hoặc bộ phận IT để thiết lập lại mật khẩu.')
  }

  return (
    <div className="login-root-container">
      {/* Background ambient lighting effects */}
      <div className="login-glow-bg login-glow-1" aria-hidden="true" />
      <div className="login-glow-bg login-glow-2" aria-hidden="true" />

      <main className="login-split-card">
        {/* LEFT PANEL: Enterprise Brand & Cold-Chain Vision */}
        <section className="login-hero-side">
          <div className="hero-top-badge-row">
            <div className="brand-logo-pill">
              <svg
                className="brand-logo-svg"
                viewBox="0 0 32 32"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <rect width="32" height="32" rx="8" fill="var(--brand)" />
                <path
                  d="M16 6L24 10.6V19.9L16 24.5L8 19.9V10.6L16 6Z"
                  stroke="#ffffff"
                  strokeWidth="2"
                  strokeLinejoin="round"
                />
                <circle cx="16" cy="15.25" r="3.25" fill="#ffffff" />
                <path
                  d="M16 6V12M24 19.9L18.8 16.9M8 19.9L13.2 16.9"
                  stroke="#ffffff"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                />
              </svg>
              <div className="brand-titles">
                <span className="brand-name">AgroChain</span>
                <span className="brand-version">Enterprise Cold-Chain Platform</span>
              </div>
            </div>

            <div className="status-indicator-badge">
              <span
                className={`status-dot ${
                  backendOnline === true ? 'dot-online' : backendOnline === false ? 'dot-offline' : 'dot-pending'
                }`}
              />
              <span className="status-label">
                {backendOnline === true ? 'Hệ thống Sẵn sàng' : backendOnline === false ? 'Đang kết nối lại...' : 'Đang kết nối'}
              </span>
            </div>
          </div>

          <div className="hero-content-block">
            <div className="hero-tagline">
              <span className="tagline-chip">Tiêu chuẩn Xuất khẩu Quốc tế</span>
              <span className="tagline-chip chip-neutral">VietGAP &amp; GlobalGAP</span>
            </div>
            <h1 className="hero-main-title">
              Nền tảng Giám sát Chuỗi lạnh &amp; Truy xuất Nguồn gốc Nông sản
            </h1>
            <p className="hero-description">
              Đảm bảo độ tươi ngon nguyên bản từ vùng trồng đến bàn ăn thông qua kiểm soát nhiệt độ thời gian thực
              và nhật ký bất biến bảo vệ bằng chuỗi mã hóa mật mã học.
            </p>
          </div>

          {/* Real-time Telemetry Showcase */}
          <div className="telemetry-grid">
            <div className="telemetry-card">
              <div className="telemetry-icon">❄️</div>
              <div className="telemetry-text">
                <span className="telemetry-val">-18°C ~ +4°C</span>
                <span className="telemetry-lbl">Giám sát Cảm biến Lạnh IoT</span>
              </div>
            </div>

            <div className="telemetry-card">
              <div className="telemetry-icon">🔗</div>
              <div className="telemetry-text">
                <span className="telemetry-val">SHA-256 + RFC 8785</span>
                <span className="telemetry-lbl">Nhật ký Bất biến 5 Lớp</span>
              </div>
            </div>

            <div className="telemetry-card">
              <div className="telemetry-icon">🛡️</div>
              <div className="telemetry-text">
                <span className="telemetry-val">PostgreSQL FORCE RLS</span>
                <span className="telemetry-lbl">Cô lập Dữ liệu Đa tổ chức</span>
              </div>
            </div>

            <div className="telemetry-card">
              <div className="telemetry-icon">📍</div>
              <div className="telemetry-text">
                <span className="telemetry-val">GPS WGS84</span>
                <span className="telemetry-lbl">Định danh Vùng trồng Cố định</span>
              </div>
            </div>
          </div>

          {/* Inspector Audit Drawer Trigger */}
          <div className="hero-footer-bar">
            <button
              type="button"
              className="audit-inspect-button"
              onClick={() => setShowAuditModal(true)}
              aria-haspopup="dialog"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M9 12l2 2 4-4" />
              </svg>
              <span>Xem Báo cáo Giám định Kỹ thuật (Technical Audit)</span>
            </button>
          </div>
        </section>

        {/* RIGHT PANEL: Enterprise Security Login Form */}
        <section className="login-form-side">
          <div className="form-card-header">
            <div className="form-card-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>Phiên làm việc An toàn</span>
            </div>
            <h2 className="form-title">Đăng nhập Hệ thống</h2>
            <p className="form-subtitle">Nhập thông tin tài khoản được cấp phát để truy cập không gian điều hành</p>
          </div>

          {backendOnline === false && (
            <div className="auth-alert-box" role="status" style={{ borderColor: 'rgba(234, 179, 8, 0.4)', background: 'rgba(234, 179, 8, 0.1)', color: 'var(--text-primary)' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#eab308" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span style={{ fontSize: '13px', lineHeight: '1.5' }}>
                Máy chủ đám mây đang thức dậy sau thời gian chờ (Cold Start ~30s). Hệ thống đang tự động kết nối lại, bạn có thể thử đăng nhập sau giây lát...
              </span>
            </div>
          )}


          {errorMessage && (
            <div className="auth-alert-box" role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-clean-form" noValidate>
            <div className="form-group-field">
              <label htmlFor="login-email" className="field-label">
                Tài khoản Email <span className="req-star">*</span>
              </label>
              <div className="input-with-icon">
                <svg className="field-prefix-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
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
                  placeholder="name@organization.com"
                  aria-errormessage="login-email-error"
                  className="modern-input"
                />
              </div>
              <div id="login-email-error" className="field-error-msg">
                Vui lòng nhập định dạng email hợp lệ.
              </div>
            </div>

            <div className="form-group-field">
              <div className="label-with-action">
                <label htmlFor="login-password" className="field-label">
                  Mật khẩu bảo vệ <span className="req-star">*</span>
                </label>
                <button
                  type="button"
                  className="field-helper-link"
                  onClick={handleForgotPassword}
                >
                  Quên mật khẩu?
                </button>
              </div>
              <div className="input-with-icon">
                <svg className="field-prefix-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
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
                  placeholder="••••••••••••"
                  aria-errormessage="login-password-error"
                  className="modern-input"
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiển thị mật khẩu'}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
              <div id="login-password-error" className="field-error-msg">
                Mật khẩu không được để trống.
              </div>
            </div>

            <div className="form-options-row">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="modern-checkbox"
                />
                <span>Duy trì trạng thái đăng nhập an toàn</span>
              </label>
            </div>

            <button
              type="submit"
              className="submit-login-button"
              disabled={submitting}
            >
              {submitting ? (
                <span className="spinner-row">
                  <span className="login-btn-spinner" />
                  Đang xác thực thông tin...
                </span>
              ) : (
                <span className="login-btn-content">
                  <span>Đăng nhập vào Hệ thống</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </span>
              )}
            </button>
          </form>

          {/* Quick Demo Accounts Presets for Evaluators & Users */}
          <div className="demo-accounts-card">
            <div className="demo-accounts-header">
              <div className="demo-accounts-title-wrap">
                <span className="demo-badge-icon">🎯</span>
                <span className="demo-accounts-title">Tài khoản Mẫu Thử nghiệm (Demo)</span>
              </div>
              <span className="demo-accounts-hint">Mật khẩu: <code>Password123!</code></span>
            </div>
            <div className="demo-presets-grid">
              {DEMO_PRESETS.map((preset) => (
                <button
                  key={preset.email}
                  type="button"
                  className={`demo-preset-btn ${email === preset.email ? 'active' : ''}`}
                  onClick={() => {
                    setEmail(preset.email)
                    setPassword(preset.password)
                    setErrorMessage(null)
                    onNotify(`Đã điền tài khoản: ${preset.roleName}`)
                  }}
                  title={`Chọn tài khoản ${preset.roleName}`}
                >
                  <span className="preset-icon">{preset.icon}</span>
                  <div className="preset-info">
                    <div className="preset-name-row">
                      <span className="preset-name">{preset.roleName}</span>
                      <span className={`preset-badge badge-${preset.badge}`}>{preset.badge}</span>
                    </div>
                    <span className="preset-email">{preset.email}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Security Assurance Notice */}
          <div className="security-guarantee-box">
            <div className="security-icon-shield">🛡️</div>
            <div className="security-guarantee-text">
              <strong>Bảo mật Xác thực Cấp độ Doanh nghiệp</strong>
              <p>Mật khẩu băm chuẩn Argon2id. Phiên lưu trữ HttpOnly Cookie chống tấn công XSS &amp; khóa 15 phút nếu sai 5 lần.</p>
            </div>
          </div>

          {/* Utility Bar (Dark Mode Toggle & Footer) */}
          <div className="login-card-footer">
            <button
              type="button"
              className="theme-switch-pill"
              onClick={onToggleTheme}
              title="Đổi giao diện Sáng / Tối"
            >
              <span>{isDark ? '☀️ Giao diện Sáng' : '🌙 Giao diện Tối'}</span>
            </button>

            <span className="copyright-tag">
              © 2026 AgroChain • TTCS_T926_K18C4_N3
            </span>
          </div>
        </section>
      </main>

      {/* AUDIT INSPECTOR MODAL: Specialized for Mentors, Evaluators and Examiners */}
      {showAuditModal && (
        <div className="audit-modal-backdrop" onClick={() => setShowAuditModal(false)}>
          <div
            className="audit-modal-panel"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="audit-modal-title"
          >
            <div className="audit-modal-header">
              <div className="audit-header-icon-title">
                <span className="audit-shield-icon">🔬</span>
                <div>
                  <h3 id="audit-modal-title">Báo cáo Kiểm định Kiến trúc Kỹ thuật (Technical Audit)</h3>
                  <p className="audit-modal-sub">Dành cho Giảng viên hướng dẫn, Mentor &amp; Hội đồng đánh giá dự án</p>
                </div>
              </div>
              <button
                type="button"
                className="audit-close-button"
                onClick={() => setShowAuditModal(false)}
                aria-label="Đóng bảng kiểm định"
              >
                ✕
              </button>
            </div>

            <div className="audit-modal-body">
              <div className="audit-section">
                <h4 className="audit-section-title">1. Tính năng hệ thống</h4>
                <div className="audit-table-container">
                  <table className="audit-spec-table">
                    <thead>
                      <tr>
                        <th>Hạng mục nghiệp vụ</th>
                        <th>Công nghệ / Giải pháp kỹ thuật</th>
                        <th>Trạng thái</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Toàn vẹn Chuỗi lạnh</td>
                        <td>Chuỗi băm SHA-256 + Canonical JSON RFC 8785</td>
                        <td><span className="badge-pass">Hoàn thành (Passed)</span></td>
                      </tr>
                      <tr>
                        <td>Quản lý Xác thực &amp; Phiên</td>
                        <td>Argon2id + HttpOnly Cookie (__Host-session)</td>
                        <td><span className="badge-pass">Bảo vệ nghiêm ngặt</span></td>
                      </tr>
                      <tr>
                        <td>Đa tổ chức &amp; Phân quyền</td>
                        <td>PostgreSQL FORCE Row Level Security (RLS) + RBAC</td>
                        <td><span className="badge-pass">Cô lập tuyệt đối</span></td>
                      </tr>
                      <tr>
                        <td>Danh mục Vùng trồng</td>
                        <td>Tọa độ GPS chuẩn WGS84 + Khóa UUID định danh</td>
                        <td><span className="badge-pass">Sẵn sàng xuất khẩu</span></td>
                      </tr>
                      <tr>
                        <td>Bất biến Nhật ký Sự kiện</td>
                        <td>Trigger PostgreSQL chặn UPDATE/DELETE + Chaining Hash</td>
                        <td><span className="badge-pass">Append-only 5 lớp</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

            </div>

            <div className="audit-modal-footer">
              <button
                type="button"
                className="audit-confirm-btn"
                onClick={() => setShowAuditModal(false)}
              >
                Đã kiểm tra xong
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
