import { useState, type FormEvent, type FocusEvent } from 'react'
import { login } from '../services/api'
import type { SessionUser } from '../types'
import { SquircleIcon } from './VietFarmVisuals'

interface LoginViewProps {
  backendOnline: boolean | null
  isDark: boolean
  onToggleTheme: () => void
  onLoginSuccess: (user: SessionUser) => void
  onNotify: (message: string) => void
}

const DEMO_PRESETS = [
  {
    roleName: 'Quản trị hệ thống',
    badge: 'system_admin',
    email: 'admin@system.vn',
    password: 'Password123!',
    iconKey: 'rice' as const,
    desc: 'Quản lý cấu hình, nhật ký kiểm toán và danh mục dùng chung toàn hệ thống',
  },
  {
    roleName: 'Nông hộ Cầu Đất',
    badge: 'grower',
    email: 'grower@caudat.vn',
    password: 'Password123!',
    iconKey: 'bokchoy' as const,
    desc: 'Quản trị thửa đất, lô thu hoạch & ghi nhật ký chuỗi lạnh',
  },
  {
    roleName: 'Quản trị HTX Mộc Châu',
    badge: 'organization_admin',
    email: 'admin@mocchau.vn',
    password: 'Password123!',
    iconKey: 'basket' as const,
    desc: 'Nhận bàn giao, tách lô, gộp lô và điều phối trong hợp tác xã',
  },
  {
    roleName: 'Đơn vị Vận chuyển Lạnh',
    badge: 'transporter',
    email: 'transporter@vantai.vn',
    password: 'Password123!',
    iconKey: 'truck' as const,
    desc: 'Vận chuyển thùng xe lạnh, cập nhật số đo và giám sát vi phạm',
  },
  {
    roleName: 'Nhà phân phối Chuỗi lạnh',
    badge: 'distributor',
    email: 'distributor@phanphoi.vn',
    password: 'Password123!',
    iconKey: 'frost' as const,
    desc: 'Quản lý kho lạnh/cửa hàng, di chuyển lô và ghi nhận tiêu thụ cuối',
  },
  {
    roleName: 'Chi cục Quản lý',
    badge: 'inspector',
    email: 'inspector@chicuc.gov.vn',
    password: 'Password123!',
    iconKey: 'carrot' as const,
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
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [traceCode, setTraceCode] = useState('')

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

  const handleQuickTrace = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = traceCode.trim()
    if (!trimmed) {
      window.location.href = '/truy-xuat?code=XRVT7PXY'
      return
    }
    window.location.href = `/truy-xuat?code=${encodeURIComponent(trimmed)}`
  }

  return (
    <div className="login-root-container">
      {/* Background organic ambient lighting with smooth float animation */}
      <div className="login-ambient-orb login-orb-1" aria-hidden="true" />
      <div className="login-ambient-orb login-orb-2" aria-hidden="true" />

      <main className="login-split-card">
        {/* LEFT PANEL: Landing Hero & Hành trình Nông sản */}
        <section className="login-hero-side animate-fade-in-1" aria-labelledby="hero-title">
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
                <span className="brand-version">Truy xuất nguồn gốc &amp; Chuỗi lạnh</span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className="status-indicator-badge">
                <span
                  className={`status-dot ${
                    backendOnline === true ? 'dot-online' : backendOnline === false ? 'dot-offline' : 'dot-pending'
                  }`}
                />
                <span className="status-label">
                  {backendOnline === true ? 'Hệ thống sẵn sàng' : backendOnline === false ? 'Đang kết nối lại...' : 'Đang kết nối'}
                </span>
              </div>
            </div>
          </div>

          <div className="hero-content-block">
            <div className="hero-tagline">
              <span className="tagline-chip">Chuỗi cung ứng minh bạch</span>
              <span className="tagline-chip chip-neutral">Môi trường thử nghiệm giả lập</span>
            </div>
            <h1 id="hero-title" className="hero-main-title">
              Hành trình nông sản từ vùng trồng đến điểm phân phối
            </h1>
            <p className="hero-description">
              Hệ thống giám sát điều kiện nhiệt độ thùng xe lạnh và ghi nhận nhật ký bất biến của từng lô hàng,
              giúp các bên đối tác và người tiêu dùng xác thực nguồn gốc minh bạch.
            </p>
          </div>

          {/* Sơ đồ hành trình nông sản bằng CSS thuần (4 chặng) */}
          <div className="journey-flow-container" aria-label="Sơ đồ hành trình một lô hàng">
            <div className="journey-flow-header">
              <span className="journey-flow-title">Vòng đời một lô hàng trong chuỗi lạnh</span>
            </div>
            <div className="journey-flow-steps">
              <div className="journey-step-item">
                <div className="step-badge-indicator">
                  <span className="step-num">1</span>
                  <SquircleIcon kind="seedling" size="sm" />
                </div>
                <div className="step-content">
                  <span className="step-title">Vùng trồng</span>
                  <span className="step-desc">Định danh thửa đất, cây trồng và nhật ký canh tác ban đầu.</span>
                </div>
              </div>

              <div className="journey-step-divider" aria-hidden="true" />

              <div className="journey-step-item">
                <div className="step-badge-indicator">
                  <span className="step-num">2</span>
                  <SquircleIcon kind="basket" size="sm" />
                </div>
                <div className="step-content">
                  <span className="step-title">Lô thu hoạch</span>
                  <span className="step-desc">Cấp mã định danh duy nhất, sơ chế và đóng gói quy chuẩn.</span>
                </div>
              </div>

              <div className="journey-step-divider" aria-hidden="true" />

              <div className="journey-step-item">
                <div className="step-badge-indicator">
                  <span className="step-num">3</span>
                  <SquircleIcon kind="truck" size="sm" />
                </div>
                <div className="step-content">
                  <span className="step-title">Vận chuyển lạnh</span>
                  <span className="step-desc">Thùng xe lạnh duy trì ngưỡng nhiệt độ bảo quản trên đường.</span>
                </div>
              </div>

              <div className="journey-step-divider" aria-hidden="true" />

              <div className="journey-step-item">
                <div className="step-badge-indicator">
                  <span className="step-num">4</span>
                  <SquircleIcon kind="frost" size="sm" />
                </div>
                <div className="step-content">
                  <span className="step-title">Điểm phân phối</span>
                  <span className="step-desc">Tiếp nhận kiểm định, đưa vào quầy kệ và phục vụ người dùng.</span>
                </div>
              </div>
            </div>
          </div>

          {/* Ô tra cứu mã lô nhanh (Quick Trace) */}
          <div className="quick-trace-section">
            <div className="quick-trace-card">
              <div className="quick-trace-title-row">
                <span className="quick-trace-label">Tra cứu nguồn gốc lô hàng công khai</span>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {(['XRVT7PXY', 'BZ84PFZ3', 'JQMB7MZ9'] as const).map((sample) => (
                    <a
                      key={sample}
                      href={`/truy-xuat?code=${sample}`}
                      className="qr-scanner-btn"
                      title={`Tra cứu ngay lô mẫu ${sample}`}
                      style={{ textDecoration: 'none' }}
                    >
                      <code>{sample}</code>
                    </a>
                  ))}
                </div>
              </div>

              <form onSubmit={handleQuickTrace} className="quick-trace-form">
                <div className="trace-input-wrap">
                  <input
                    type="text"
                    value={traceCode}
                    onChange={(e) => setTraceCode(e.target.value)}
                    placeholder="Nhập mã lô thực tế (VD: XRVT7PXY, BZ84PFZ3, JQMB7MZ9)..."
                    aria-label="Nhập mã lô để tra cứu"
                    className="trace-input"
                  />
                  <button type="submit" className="ds-button ds-button-brand trace-submit-btn">
                    Tra cứu
                  </button>
                </div>
              </form>

              <div className="quick-trace-footer-link">
                <a href="/truy-xuat?code=XRVT7PXY" className="trace-direct-link">
                  Mở trang tra cứu công khai kèm bản đồ hành trình →
                </a>
              </div>
            </div>
          </div>

          <div className="hero-disclaimer-note">
            <span>Ghi chú: Toàn bộ thông tin, số đo nhiệt độ và sự kiện trên hệ thống là dữ liệu mẫu giả lập phục vụ nghiên cứu và kiểm thử.</span>
          </div>
        </section>

        {/* RIGHT PANEL: Form Đăng nhập & Tài khoản mẫu */}
        <section className="login-form-side" aria-labelledby="form-title">
          <div className="form-card-header">
            <div className="form-card-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>Phiên làm việc bảo vệ</span>
            </div>
            <h2 id="form-title" className="form-title">Đăng nhập</h2>
            <p className="form-subtitle">Nhập thông tin tài khoản được cấp phát hoặc chọn tài khoản mẫu bên dưới</p>
          </div>

          {backendOnline === false && (
            <div className="auth-alert-box" role="status" style={{ borderColor: 'var(--border-subtle)', background: 'var(--neutral-secondary-soft)', color: 'var(--text-primary)' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span style={{ fontSize: '13px', lineHeight: '1.5' }}>
                Hệ thống đang kết nối tới máy chủ dữ liệu. Bạn có thể thử đăng nhập sau giây lát...
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
                Tài khoản email <span className="req-star">*</span>
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
                  disabled={submitting}
                  value={email}
                  onBlur={handleBlur}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    if (e.currentTarget.checkValidity()) {
                      e.currentTarget.removeAttribute('aria-invalid')
                    }
                  }}
                  placeholder="name@organization.vn"
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
                  Mật khẩu <span className="req-star">*</span>
                </label>
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
                  disabled={submitting}
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
                  disabled={submitting}
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

            <button
              type="submit"
              className="submit-login-button"
              disabled={submitting}
            >
              {submitting ? (
                <span className="spinner-row">
                  <span className="login-btn-spinner" />
                  Đang đăng nhập...
                </span>
              ) : (
                <span className="login-btn-content">
                  <span>Đăng nhập</span>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </span>
              )}
            </button>
          </form>

          {/* Danh sách 6 tài khoản mẫu theo từng vai trò */}
          <div className="demo-accounts-card">
            <div className="demo-accounts-header">
              <div className="demo-accounts-title-wrap">
                <span className="demo-badge-icon">🎯</span>
                <span className="demo-accounts-title">Tài khoản mẫu thử nghiệm</span>
              </div>
              <span className="demo-accounts-hint">Mật khẩu chung: <code>Password123!</code></span>
            </div>
            <div className="demo-presets-grid">
              {DEMO_PRESETS.map((preset) => (
                <button
                  key={preset.email}
                  type="button"
                  disabled={submitting}
                  className={`demo-preset-btn ${email === preset.email ? 'active' : ''}`}
                  onClick={() => {
                    setEmail(preset.email)
                    setPassword(preset.password)
                    setErrorMessage(null)
                    void executeLogin(preset.email, preset.password)
                  }}
                  title={`Đăng nhập nhanh bằng tài khoản ${preset.roleName}`}
                >
                  <SquircleIcon kind={preset.iconKey} size="sm" />
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

          {/* Chuyển đổi giao diện sáng / tối & thông tin chân trang */}
          <div className="login-card-footer">
            <button
              type="button"
              className="theme-switch-pill"
              onClick={onToggleTheme}
              title="Chuyển đổi giao diện Sáng / Tối"
            >
              <span>{isDark ? 'Chế độ sáng' : 'Chế độ tối'}</span>
            </button>

            <span className="copyright-tag">
              AgroChain • Đề tài Nghiên cứu Khoa học
            </span>
          </div>
        </section>
      </main>
    </div>
  )
}
