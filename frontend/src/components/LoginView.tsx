import { useRef, useState, type FormEvent, type FocusEvent } from 'react'
import { API_BASE_URL, DEMO_LOGIN_ENABLED, demoLogin, login } from '../services/api'
import { DEMO_ACCOUNTS, type DemoAccount, type SessionUser } from '../types'
import { Icon } from './Icons'
import { GatewayJourney } from './GatewayJourney'

interface LoginViewProps {
  backendOnline: boolean | null
  isDark: boolean
  onToggleTheme: () => void
  onLoginSuccess: (user: SessionUser) => void
  onNotify: (message: string) => void
}

export function LoginView({ backendOnline, isDark, onToggleTheme, onLoginSuccess, onNotify }: LoginViewProps) {
  const [passport, setPassport] = useState(DEMO_ACCOUNTS[0].organization)
  const [email, setEmail] = useState('grower@caudat.vn')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const errorRef = useRef<HTMLDivElement>(null)

  const setInputValidity = (input: HTMLInputElement) => {
    input.setAttribute('aria-invalid', String(!input.checkValidity()))
  }

  const onBlur = (event: FocusEvent<HTMLInputElement>) => setInputValidity(event.currentTarget)

  const runLogin = async (targetEmail: string, targetPassword: string) => {
    setSubmitting(true)
    setErrorMessage(null)
    try {
      const user = await login({ email: targetEmail.trim(), password: targetPassword })
      onNotify(`Đăng nhập thành công: ${user.full_name}`)
      onLoginSuccess(user)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Không thể đăng nhập vào hệ thống.'
      setErrorMessage(message)
      requestAnimationFrame(() => errorRef.current?.focus())
    } finally {
      setSubmitting(false)
    }
  }

  const runDemoLogin = async (account: DemoAccount) => {
    if (!DEMO_LOGIN_ENABLED) return
    setSubmitting(true)
    setErrorMessage(null)
    setPassport(account.organization)
    setEmail(account.email)
    setPassword('')
    try {
      const user = await demoLogin({ email: account.email })
      onNotify(`Đã mở phiên demo: ${user.full_name}`)
      onLoginSuccess(user)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Không thể mở phiên demo.'
      setErrorMessage(message)
      requestAnimationFrame(() => errorRef.current?.focus())
    } finally {
      setSubmitting(false)
    }
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const requiredInputs = Array.from(form.querySelectorAll<HTMLInputElement>('input[required]'))
    requiredInputs.forEach(setInputValidity)
    if (!form.reportValidity()) return
    void runLogin(email, password)
  }

  const applyAccount = (account: DemoAccount) => {
    setPassport(account.organization)
    setEmail(account.email)
    setPassword('')
    setErrorMessage(null)
    onNotify(`Đã điền email: ${account.email}`)
  }

  return (
    <main className="secure-gateway">
      <section className="gateway-story" aria-label="AgroChain Secure Gateway">
        <div className="gateway-topline"><a href="#gateway-main" className="gateway-brand"><span className="brand-mark"><Icon name="agro" size={21} /></span><span>AgroChain<small>NGUỒN GỐC / CHUỖI LẠNH</small></span></a><span className="gateway-version">FIELD NOTES / 01</span><a className="gateway-jump" href="#gateway-main">Đăng nhập <Icon name="arrow" size={14} /></a></div>
        <div className="gateway-story-copy"><p className="eyebrow">TỪ ĐẤT LÀNH ĐẾN DẤU VẾT SỐ</p><h1>Mỗi mùa vụ,<br /><em>một câu chuyện.</em></h1><p>Đi theo một kiện hàng. Chạm vào dữ liệu. Khám phá điều làm nên một nguồn gốc đáng tin.</p></div>
        <GatewayJourney passport={passport} onToggleTheme={onToggleTheme} isDark={isDark} />
        <div className="gateway-story-footer"><span><i className={`api-indicator ${backendOnline === true ? 'api-indicator-online' : backendOnline === false ? 'api-indicator-offline' : ''}`} />{backendOnline === true ? 'API SẴN SÀNG' : backendOnline === false ? 'API CHƯA KẾT NỐI' : 'ĐANG KẾT NỐI API'}</span><span>MÔ PHỎNG TƯƠNG TÁC / 01</span></div>
      </section>

      <section className="gateway-access" id="gateway-main" tabIndex={-1} aria-labelledby="gateway-title">
        <div className="gateway-access-toolbar"><div className="mobile-gateway-brand"><span className="brand-mark"><Icon name="agro" size={18} /></span><span>AgroChain</span></div><div className="gateway-tools"><span className="api-status"><i className={`api-indicator ${backendOnline === true ? 'api-indicator-online' : backendOnline === false ? 'api-indicator-offline' : ''}`} />{backendOnline === true ? 'API online' : backendOnline === false ? 'API offline' : 'API connecting'}</span><a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer" className="text-action">API docs <Icon name="arrow" size={13} /></a><button type="button" className="icon-button" aria-label={isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'} onClick={onToggleTheme}><Icon name={isDark ? 'sun' : 'moon'} size={17} /></button></div></div>

        <div className="gateway-access-body">
          <div className="gateway-form-heading"><p className="eyebrow">KHÔNG GIAN LÀM VIỆC</p><h2 id="gateway-title">Bắt đầu từ<br />nguồn gốc.</h2><p>Đăng nhập bằng tài khoản tổ chức để tiếp tục theo dõi nguồn gốc và vùng trồng.</p></div>

          <div className={`gateway-auth-state ${errorMessage ? 'auth-rejected' : submitting ? 'auth-pending' : ''}`} role="status"><Icon name={errorMessage ? 'close' : 'shield'} size={16} /><span>{submitting ? 'Đang xác thực danh tính với máy chủ…' : errorMessage ? 'Xác thực chưa thành công. Kiểm tra thông tin bên dưới.' : 'Đăng nhập để mở workspace của tổ chức.'}</span></div>
          <form className="gateway-form" onSubmit={submit} noValidate>
            {errorMessage && <div ref={errorRef} className="gateway-error" role="alert" tabIndex={-1}><span className="error-mark">!</span><div><strong>Không thể mở phiên làm việc.</strong><p>{errorMessage}</p></div></div>}
            <label htmlFor="gateway-email">Email tổ chức <span>*</span><input id="gateway-email" name="email" type="email" required autoComplete="username" value={email} onBlur={onBlur} onChange={(event) => { setEmail(event.target.value); setErrorMessage(null); event.currentTarget.removeAttribute('aria-invalid') }} placeholder="ten@tochuc.vn" aria-describedby="gateway-email-help" /></label>
            <p id="gateway-email-help" className="field-help">Dùng email được cấp cho tenant của bạn.</p>
            <label htmlFor="gateway-password">Mật khẩu <span>*</span><input id="gateway-password" name="password" type="password" required autoComplete="current-password" value={password} onBlur={onBlur} onChange={(event) => { setPassword(event.target.value); setErrorMessage(null); event.currentTarget.removeAttribute('aria-invalid') }} placeholder="Nhập mật khẩu" /></label>
            <button type="submit" className="button button-primary gateway-submit" disabled={submitting}>{submitting ? <><span className="button-spinner" />Đang xác thực với API…</> : <>Mở workspace <Icon name="arrow" size={16} /></>}</button>
            <p className="gateway-auth-note"><Icon name="shield" size={15} />Phiên bảo mật qua cookie HttpOnly. Đăng nhập bằng tài khoản được cấp cho tổ chức của bạn.</p>
          </form>

          <div className="gateway-divider"><span /> <small>KHÁM PHÁ VỚI TỔ CHỨC DEMO</small> <span /></div>
          <div className="demo-passports" aria-label="Tài khoản tổ chức demo">
            {DEMO_ACCOUNTS.map((account, index) => (
              <article className={`demo-passport ${email === account.email ? 'demo-passport-selected' : ''}`} key={account.email}>
                <span className="passport-index">0{index + 1}</span><div className="passport-copy"><span className="micro-label">{index === 0 ? 'GROWER / TENANT A' : index === 1 ? 'ORG ADMIN / TENANT B' : 'INSPECTOR / READ ONLY'}</span><h3>{account.shortName}</h3><p>{account.organization}</p><code>{account.email}</code><button type="button" className="passport-preview" disabled={submitting} onClick={() => applyAccount(account)}>Chọn passport <Icon name="arrow" size={12} /></button></div>
                {DEMO_LOGIN_ENABLED ? <button type="button" className="passport-enter" aria-label={`Vào demo ${account.label}`} disabled={submitting} onClick={() => void runDemoLogin(account)}><Icon name="arrow" size={16} /></button> : <button type="button" className="passport-enter passport-fill" disabled={submitting} aria-label={`Điền email ${account.email}`} onClick={() => applyAccount(account)}><Icon name="plus" size={16} /></button>}
              </article>
            ))}
          </div>
          {!DEMO_LOGIN_ENABLED && <p className="demo-disabled-note">Một chạm demo đang tắt. Các passport chỉ điền email; đăng nhập vẫn dùng mật khẩu của bạn.</p>}
          {DEMO_LOGIN_ENABLED && <p className="demo-enabled-note"><Icon name="check" size={14} />Phiên demo dùng endpoint allowlist — không có mật khẩu demo trong frontend.</p>}
        </div>
        <footer className="gateway-access-footer"><span>AGROCHAIN / SECURE GATEWAY</span><span>POSTGRESQL RLS · RBAC · SHA-256</span></footer>
      </section>
    </main>
  )
}
