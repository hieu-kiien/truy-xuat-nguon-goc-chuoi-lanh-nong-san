import { useState, type FormEvent, type FocusEvent } from 'react'
import { login } from '../services/api'
import type { SessionUser } from '../types'

interface LoginViewProps {
  onLoginSuccess: (user: SessionUser) => void
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
    roleText: 'grower — Quyền đọc/ghi vùng trồng',
    email: 'grower@caudat.vn',
    password: 'Password123!',
    description: 'Quản lý thửa đất thuộc Nông trại Cầu Đất Đà Lạt.',
  },
  {
    label: 'Quản trị HTX Mộc Châu (Tổ chức B)',
    organization: 'Hợp tác xã Nông sản Mộc Châu',
    roleText: 'organization_admin — Cô lập dữ liệu RLS',
    email: 'admin@mocchau.vn',
    password: 'Password123!',
    description: 'Kiểm chứng cô lập dữ liệu đa tổ chức (chỉ thấy vùng trồng Mộc Châu).',
  },
  {
    label: 'Thanh tra viên (Cơ quan kiểm tra)',
    organization: 'Chi cục Quản lý Chất lượng Nông lâm sản',
    roleText: 'inspector — Chỉ đọc lô hàng (lots:read_all)',
    email: 'inspector@chicuc.gov.vn',
    password: 'Password123!',
    description: 'Kiểm chứng phân quyền RBAC chặn truy cập trái phép (403 Forbidden).',
  },
]

export function LoginView({ onLoginSuccess }: LoginViewProps) {
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
  }

  return (
    <div className="auth-layout">
      <section className="card auth-card">
        <div className="card-header">
          <h2>Đăng nhập hệ thống</h2>
          <p className="text-muted">
            Xác thực phiên làm việc bảo mật theo tổ chức và vai trò chuỗi cung ứng
          </p>
        </div>

        {errorMessage && (
          <div className="alert alert-error" role="alert">
            <strong>Lỗi xác thực:</strong> {errorMessage}
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
              <span aria-hidden="true">[!]</span> Vui lòng nhập địa chỉ email hợp lệ.
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
              <span aria-hidden="true">[!]</span> Mật khẩu không được để trống.
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? 'Đang xác thực...' : 'Đăng nhập'}
          </button>

          <p className="security-note">
            Bảo mật Argon2id &amp; chống dò mật khẩu: Tài khoản tự động khóa tạm thời 15 phút nếu nhập sai 5 lần liên tiếp.
          </p>
        </form>
      </section>

      <aside className="card demo-accounts-card">
        <div className="card-header">
          <h3>Tài khoản kiểm thử nhanh</h3>
          <p className="text-muted">
            Chọn một tài khoản bên dưới để điền sẵn thông tin và kiểm tra phân quyền đa tổ chức
          </p>
        </div>

        <div className="demo-list">
          {DEMO_ACCOUNTS.map((account) => {
            const isSelected = email === account.email
            return (
              <button
                key={account.email}
                type="button"
                onClick={() => applyDemoAccount(account)}
                className={`demo-item ${isSelected ? 'demo-item-active' : ''}`}
              >
                <div className="demo-item-top">
                  <strong>{account.label}</strong>
                  <span className="badge badge-neutral">{account.email}</span>
                </div>
                <div className="demo-item-role">{account.roleText}</div>
                <p className="demo-item-desc">{account.description}</p>
              </button>
            )
          })}
        </div>
      </aside>
    </div>
  )
}
