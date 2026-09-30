import { useState, type FormEvent, type FocusEvent } from 'react'
import { API_BASE_URL, login } from '../services/api'
import type { SessionUser } from '../types'

interface LoginViewProps {
  backendOnline: boolean | null
  onLoginSuccess: (user: SessionUser) => void
  onNotify: (message: string) => void
}

interface DemoAccount {
  label: string
  organization: string
  roleText: string
  email: string
  password: string
  description: string
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    label: 'Nông hộ Cầu Đất (Tổ chức A)',
    organization: 'Nông trại Cầu Đất Đà Lạt',
    roleText: 'grower · Quyền đọc & ghi vùng trồng (farms:read, farms:write)',
    email: 'grower@caudat.vn',
    password: 'Password123!',
    description: 'Quản lý danh mục thửa đất và nhật ký canh tác tại Đà Lạt.',
  },
  {
    label: 'Quản trị HTX Mộc Châu (Tổ chức B)',
    organization: 'Hợp tác xã Nông sản Mộc Châu',
    roleText: 'organization_admin · Cô lập dữ liệu đa tổ chức (RLS)',
    email: 'admin@mocchau.vn',
    password: 'Password123!',
    description: 'Kiểm chứng PostgreSQL Row-Level Security (chỉ hiển thị dữ liệu Mộc Châu).',
  },
  {
    label: 'Thanh tra viên (Cơ quan kiểm tra)',
    organization: 'Chi cục Quản lý Chất lượng Nông lâm sản',
    roleText: 'inspector · Chỉ đọc lô hàng (lots:read_all)',
    email: 'inspector@chicuc.gov.vn',
    password: 'Password123!',
    description: 'Kiểm chứng cơ chế RBAC chặn truy cập trái phép (403 Forbidden).',
  },
]

export function LoginView({
  backendOnline,
  onLoginSuccess,
  onNotify,
}: LoginViewProps) {
  const [email, setEmail] = useState('grower@caudat.vn')
  const [password, setPassword] = useState('Password123!')
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

  const applyDemoAccount = (account: DemoAccount) => {
    setEmail(account.email)
    setPassword(account.password)
    setErrorMessage(null)
    onNotify(`Đã chọn tài khoản mẫu: ${account.email}`)
  }

  return (
    <div className="login-hero section-pattern">
      <div className="login-container">
        <header className="login-banner">
          <div className="pill-tag">
            <span>
              {backendOnline === true
                ? '● Backend Online'
                : backendOnline === false
                  ? '○ Backend Offline'
                  : '◌ Đang kết nối máy chủ'}
            </span>
            <span>&bull;</span>
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              style={{ color: 'inherit', textDecoration: 'underline' }}
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
            <div style={{ marginBottom: '20px' }}>
              <h2 style={{ fontSize: '24px', marginBottom: '4px' }}>
                Đăng nhập hệ thống
              </h2>
              <p style={{ fontSize: '14px', color: 'var(--body-subtle)' }}>
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

              <p
                style={{
                  fontSize: '12px',
                  color: 'var(--body-subtle)',
                  marginTop: '4px',
                }}
              >
                Bảo mật Argon2id &amp; chống dò mật khẩu: Tự động khóa 15 phút nếu nhập
                sai 5 lần liên tiếp.
              </p>
            </form>
          </section>

          <aside className="sticker-panel auth-panel">
            <div style={{ marginBottom: '16px' }}>
              <h2 style={{ fontSize: '22px', marginBottom: '4px' }}>
                Chọn nhanh Tài khoản Demo
              </h2>
              <p style={{ fontSize: '14px', color: 'var(--body-subtle)' }}>
                Bấm vào một thẻ bên dưới để điền tự động và kiểm thử các kịch bản phân quyền
              </p>
            </div>

            <div className="demo-cards-stack">
              {DEMO_ACCOUNTS.map((account) => {
                const isSelected = email === account.email
                return (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => applyDemoAccount(account)}
                    className={`demo-sticker-btn ${
                      isSelected ? 'demo-sticker-active' : ''
                    }`}
                  >
                    <div className="demo-sticker-header">
                      <span className="demo-sticker-title">{account.label}</span>
                      <code>{account.email}</code>
                    </div>
                    <div className="demo-sticker-role">{account.roleText}</div>
                    <p className="demo-sticker-desc">{account.description}</p>
                  </button>
                )
              })}
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
