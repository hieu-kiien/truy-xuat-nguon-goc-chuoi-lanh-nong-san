import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, getPublicTrace } from '../services/api'
import type { PublicTraceResponse, PublicTraceWarning } from '../types'

const LOT_CODE_PATTERN = /^[A-Za-z0-9]{4,12}$/

const normalizeCode = (raw: string): string => raw.trim().toUpperCase()

/** Mã lô truyền qua `?code=` khi người tiêu dùng quét tem QR. */
function readRequestedCode(): string | null {
  if (typeof window === 'undefined') return null
  const requested = normalizeCode(new URLSearchParams(window.location.search).get('code') ?? '')
  return LOT_CODE_PATTERN.test(requested) ? requested : null
}

function WarningIcon({ level }: { level: PublicTraceWarning['level'] }) {
  if (level === 'danger') {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    )
  }
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  )
}

export function PublicTracePage() {
  const [requestedCode] = useState(readRequestedCode)
  const [code, setCode] = useState(requestedCode ?? '')
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [result, setResult] = useState<PublicTraceResponse | null>(null)
  const autoLookupDone = useRef(false)

  const lookup = useCallback(async (rawCode: string) => {
    const normalized = normalizeCode(rawCode)
    if (!LOT_CODE_PATTERN.test(normalized)) {
      setErrorMessage('Mã lô gồm 4–12 ký tự chữ và số, không có ký tự đặc biệt.')
      setResult(null)
      return
    }

    setCode(normalized)
    setLoading(true)
    setErrorMessage(null)
    setResult(null)
    try {
      const payload = await getPublicTrace(normalized)
      setResult(payload)
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setErrorMessage(
          'Không tìm thấy lô hàng với mã này. Vui lòng kiểm tra lại mã in trên bao bì.',
        )
      } else if (err instanceof ApiError && err.message) {
        setErrorMessage(err.message)
      } else {
        setErrorMessage('Không tra cứu được lúc này. Vui lòng thử lại.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  // Quét tem QR sẽ mở /truy-xuat?code=<mã lô>: tra cứu ngay, không bắt người dùng nhập lại.
  useEffect(() => {
    if (!requestedCode || autoLookupDone.current) return
    autoLookupDone.current = true
    void lookup(requestedCode)
  }, [lookup, requestedCode])

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void lookup(code)
  }

  const trace = result?.trace

  return (
    <div className="login-root-container">
      {/* Background ambient lighting effects */}
      <div className="login-glow-bg login-glow-1" aria-hidden="true" />
      <div className="login-glow-bg login-glow-2" aria-hidden="true" />

      <main className="login-split-card">
        {/* LEFT PANEL: Public Traceability Brand */}
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
                <span className="brand-version">Public Traceability Portal</span>
              </div>
            </div>
          </div>

          <div className="hero-content-block">
            <div className="hero-tagline">
              <span className="tagline-chip">Tra cứu Công khai</span>
              <span className="tagline-chip chip-neutral">Không cần Đăng nhập</span>
            </div>
            <h1 className="hero-main-title">Kiểm tra Nguồn gốc Nông sản bằng Mã lô</h1>
            <p className="hero-description">
              Nhập mã lô in trên bao bì để xem xuất xứ, vùng trồng và cảnh báo an toàn thực
              phẩm. Thông tin kinh doanh riêng tư của đơn vị trong chuỗi không hiển thị
              trên trang này.
            </p>
          </div>

          <div className="telemetry-grid">
            <div className="telemetry-card">
              <div className="telemetry-icon">🌱</div>
              <div className="telemetry-text">
                <span className="telemetry-val">Vùng trồng Minh bạch</span>
                <span className="telemetry-lbl">Tên vùng trồng hiển thị công khai</span>
              </div>
            </div>
            <div className="telemetry-card">
              <div className="telemetry-icon">❄️</div>
              <div className="telemetry-text">
                <span className="telemetry-val">Giám sát Chuỗi lạnh</span>
                <span className="telemetry-lbl">Cảnh báo bảo quản được ghi nhận</span>
              </div>
            </div>
            <div className="telemetry-card">
              <div className="telemetry-icon">🛡️</div>
              <div className="telemetry-text">
                <span className="telemetry-val">Chỉ hiện Trường Công khai</span>
                <span className="telemetry-lbl">Giấu khối lượng, giá &amp; đối tác</span>
              </div>
            </div>
          </div>
        </section>

        {/* RIGHT PANEL: Lookup Form & Public Result */}
        <section className="login-form-side">
          <div className="form-card-header">
            <div className="form-card-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <span>Tra cứu Công khai</span>
            </div>
            <h2 className="form-title">Tra cứu Mã lô</h2>
            <p className="form-subtitle">
              Nhập mã lô (4–12 ký tự chữ và số) in trên bao bì sản phẩm
            </p>
          </div>

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

          <form className="auth-clean-form" noValidate onSubmit={(event) => void handleSubmit(event)}>
            <div className="form-group-field">
              <label htmlFor="public-lot-code" className="field-label">
                Mã lô <span className="req-star">*</span>
              </label>
              <div className="input-with-icon">
                <svg className="field-prefix-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <input
                  id="public-lot-code"
                  className="modern-input"
                  value={code}
                  onChange={(event) => setCode(event.target.value.toUpperCase())}
                  placeholder="VD: K3M7P2QZ"
                  autoComplete="off"
                  maxLength={12}
                  disabled={loading}
                />
              </div>
            </div>

            <button type="submit" className="submit-login-button" disabled={loading}>
              {loading ? (
                <span className="spinner-row">
                  <span className="login-btn-spinner" />
                  Đang tra cứu...
                </span>
              ) : (
                <span className="login-btn-content">
                  <span>Truy xuất Nguồn gốc</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </span>
              )}
            </button>
          </form>

          {trace && result && (
            <div className="public-trace-result">
              {result.warnings.map((warning) => (
                <div
                  key={warning.code}
                  className="auth-alert-box"
                  role={warning.level === 'danger' ? 'alert' : 'status'}
                  style={
                    warning.level === 'danger'
                      ? undefined
                      : {
                          borderColor: 'rgba(234, 179, 8, 0.4)',
                          background: 'rgba(234, 179, 8, 0.1)',
                          color: 'var(--text-primary)',
                        }
                  }
                >
                  <WarningIcon level={warning.level} />
                  <span>{warning.message}</span>
                </div>
              ))}

              <div className="trace-lot-summary">
                <span className="trace-lot-chip">
                  Mã lô <code>{trace.lot_code ?? '—'}</code>
                </span>
                <h3 className="trace-product-name">{trace.product_name ?? 'Sản phẩm'}</h3>
              </div>

              <div className="trace-fields-grid">
                <div className="trace-field-tile">
                  <span className="trace-field-icon" aria-hidden="true">📦</span>
                  <div>
                    <span className="trace-field-lbl">Quy cách</span>
                    <span className="trace-field-val">
                      {trace.product_unit ? `${trace.product_unit}` : 'Chưa cập nhật'}
                    </span>
                  </div>
                </div>
                <div className="trace-field-tile">
                  <span className="trace-field-icon" aria-hidden="true">📅</span>
                  <div>
                    <span className="trace-field-lbl">Ngày thu hoạch</span>
                    <span className="trace-field-val">{trace.harvested_on ?? 'Chưa cập nhật'}</span>
                  </div>
                </div>
                <div className="trace-field-tile">
                  <span className="trace-field-icon" aria-hidden="true">🌱</span>
                  <div>
                    <span className="trace-field-lbl">Vùng trồng</span>
                    <span className="trace-field-val">{trace.farm_name ?? 'Chưa cập nhật'}</span>
                  </div>
                </div>
                <div className="trace-field-tile">
                  <span className="trace-field-icon" aria-hidden="true">📍</span>
                  <div>
                    <span className="trace-field-lbl">Nguồn gốc</span>
                    <span className="trace-field-val">{trace.origin_organization_type ?? '—'}</span>
                  </div>
                </div>
                <div className="trace-field-tile">
                  <span className="trace-field-icon" aria-hidden="true">🏷️</span>
                  <div>
                    <span className="trace-field-lbl">Trạng thái</span>
                    <span className="trace-field-val">{trace.status ?? '—'}</span>
                  </div>
                </div>
              </div>

              <p className="public-trace-note">
                🔒 Trang chỉ hiển thị các trường công khai nhằm bảo vệ thông tin kinh doanh
                của đơn vị tham gia chuỗi.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
