import { lazy, Suspense, useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, getPublicRoute, getPublicTrace } from '../services/api'
import type { PublicRoute, PublicTraceResponse, PublicTraceWarning } from '../types'
import { SquircleIcon, VietFarmJourneyStepper } from './VietFarmVisuals'

const RouteMap = lazy(() => import('./RouteMap').then((module) => ({ default: module.RouteMap })))

const LOT_CODE_PATTERN = /^[A-Za-z0-9-]{4,32}$/

const normalizeCode = (raw: string): string => raw.trim().toUpperCase()

/** Mã lô lấy từ URL khi quét tem QR: `/trace/<mã>`, `/truy-xuat/<mã>` hoặc `?code=<mã>` (N3-65). */
function readInitialLotCode(): string {
  if (typeof window === 'undefined') return ''
  const match = /^\/(?:trace|truy-xuat)\/([^/?#]+)\/?$/i.exec(window.location?.pathname ?? '')
  let raw = ''
  if (match?.[1]) {
    try {
      raw = decodeURIComponent(match[1])
    } catch {
      raw = match[1]
    }
  } else {
    raw = new URLSearchParams(window.location?.search ?? '').get('code') ?? ''
  }
  const normalized = normalizeCode(raw)
  return LOT_CODE_PATTERN.test(normalized) ? normalized : ''
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
  const [code, setCode] = useState(readInitialLotCode)
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [result, setResult] = useState<PublicTraceResponse | null>(null)
  const [route, setRoute] = useState<PublicRoute | null>(null)
  const autoLookupDone = useRef(false)

  const lookup = useCallback(async (rawCode: string) => {
    const normalized = normalizeCode(rawCode)
    if (!LOT_CODE_PATTERN.test(normalized)) {
      setErrorMessage('Mã lô gồm 4–12 ký tự chữ và số, không có ký tự đặc biệt.')
      setResult(null)
      setRoute(null)
      return
    }

    setCode(normalized)
    setLoading(true)
    setErrorMessage(null)
    setResult(null)
    setRoute(null)
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

    try {
      setRoute(await getPublicRoute(normalized))
    } catch {
      setRoute(null)
    }
  }, [])

  useEffect(() => {
    if (autoLookupDone.current) return
    const initial = readInitialLotCode()
    if (!initial) return
    autoLookupDone.current = true
    const timer = window.setTimeout(() => {
      void lookup(initial)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [lookup])

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void lookup(code)
  }

  const trace = result?.trace

  return (
    <div className="login-root-container public-trace-page">
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
                <span className="brand-version">VietFarm Public Traceability</span>
              </div>
            </div>
            <a
              href="/login"
              className="ds-button ds-button-secondary ds-button-sm"
              style={{ textDecoration: 'none' }}
            >
              ← Cổng đăng nhập
            </a>
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
              <SquircleIcon kind="seedling" size="sm" />
              <div className="telemetry-text">
                <span className="telemetry-val">Vùng trồng Minh bạch</span>
                <span className="telemetry-lbl">Tên vùng trồng hiển thị công khai</span>
              </div>
            </div>
            <div className="telemetry-card">
              <SquircleIcon kind="frost" size="sm" />
              <div className="telemetry-text">
                <span className="telemetry-val">Giám sát Chuỗi lạnh</span>
                <span className="telemetry-lbl">Cảnh báo bảo quản được ghi nhận</span>
              </div>
            </div>
            <div className="telemetry-card">
              <SquircleIcon kind="rice" size="sm" />
              <div className="telemetry-text">
                <span className="telemetry-val">Chỉ hiện Trường Công khai</span>
                <span className="telemetry-lbl">Giấu khối lượng, giá &amp; đối tác</span>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '14px' }}>
            <VietFarmJourneyStepper compact />
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
                  placeholder="VD: XRVT7PXY, BZ84PFZ3, JQMB7MZ9"
                  autoComplete="off"
                  maxLength={12}
                  disabled={loading}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Mã lô mẫu có sẵn:</span>
              {(typeof window !== 'undefined' && window.location?.hostname?.includes('onrender.com')
                ? [
                    { code: '4S594256', label: '4S594256 (Bắp cải D1 + Bản đồ)' },
                    { code: 'P8V8RDPM', label: 'P8V8RDPM (Dâu tây HTX 40kg)' },
                    { code: 'WJS2JKHZ', label: 'WJS2JKHZ (Dâu tây Nông trại)' },
                    { code: 'YEQTXCQ7', label: 'YEQTXCQ7 (Lô đang thu hồi)' },
                  ]
                : [
                    { code: 'XRVT7PXY', label: 'XRVT7PXY (Bắp cải D1 + Bản đồ)' },
                    { code: 'BZ84PFZ3', label: 'BZ84PFZ3 (Dâu tây HTX + Chế biến)' },
                    { code: 'JQMB7MZ9', label: 'JQMB7MZ9 (Dâu tây Nông trại)' },
                    { code: 'DB99A7YK', label: 'DB99A7YK (Đã tiêu thụ)' },
                  ]
              ).map((item) => (
                <button
                  key={item.code}
                  type="button"
                  className="ds-button ds-button-secondary ds-button-xs"
                  disabled={loading}
                  onClick={() => {
                    setCode(item.code)
                    void lookup(item.code)
                  }}
                >
                  {item.label}
                </button>
              ))}
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
        </section>

        {trace && result && (
          <section className="public-trace-result public-trace-result-full">
            {result.warnings.map((warning) => (
              <div
                key={warning.code}
                className="auth-alert-box"
                role={warning.level === 'danger' ? 'alert' : 'status'}
                style={
                  warning.level === 'danger'
                    ? undefined
                    : {
                        borderColor: 'rgba(217, 130, 43, 0.4)',
                        background: 'rgba(217, 130, 43, 0.1)',
                        color: 'var(--text-primary)',
                      }
                }
              >
                <WarningIcon level={warning.level} />
                <span>{warning.message}</span>
              </div>
            ))}

            <div className={`public-trace-bento-body ${route && route.points.length > 0 ? 'has-route-map' : ''}`}>
              <div className="public-trace-bento-left">
                <div className="trace-lot-summary vf-trace-summary-with-icon">
                  <SquircleIcon nameHint={trace.product_name} size="lg" />
                  <div>
                    <span className="trace-lot-chip">
                      Mã lô <code>{trace.lot_code ?? '—'}</code>
                    </span>
                    <h3 className="trace-product-name">{trace.product_name ?? 'Sản phẩm'}</h3>
                  </div>
                </div>

                <div className="trace-fields-grid">
                  <div className="trace-field-tile">
                    <SquircleIcon kind="basket" size="sm" />
                    <div>
                      <span className="trace-field-lbl">Quy cách</span>
                      <span className="trace-field-val">
                        {trace.product_unit ? `${trace.product_unit}` : 'Chưa cập nhật'}
                      </span>
                    </div>
                  </div>
                  <div className="trace-field-tile">
                    <SquircleIcon kind="bokchoy" size="sm" />
                    <div>
                      <span className="trace-field-lbl">Ngày thu hoạch</span>
                      <span className="trace-field-val">{trace.harvested_on ?? 'Chưa cập nhật'}</span>
                    </div>
                  </div>
                  <div className="trace-field-tile">
                    <SquircleIcon kind="seedling" size="sm" />
                    <div>
                      <span className="trace-field-lbl">Vùng trồng</span>
                      <span className="trace-field-val">{trace.farm_name ?? 'Chưa cập nhật'}</span>
                    </div>
                  </div>
                  <div className="trace-field-tile">
                    <SquircleIcon kind="rice" size="sm" />
                    <div>
                      <span className="trace-field-lbl">Nguồn gốc</span>
                      <span className="trace-field-val">
                        {trace.origin_organization_type === 'farm'
                          ? 'Nông trại sản xuất'
                          : trace.origin_organization_type === 'cooperative'
                            ? 'Hợp tác xã'
                            : trace.origin_organization_type ?? '—'}
                      </span>
                    </div>
                  </div>
                  <div className="trace-field-tile">
                    <SquircleIcon kind="frost" size="sm" />
                    <div>
                      <span className="trace-field-lbl">Trạng thái</span>
                      <span className="trace-field-val">
                        {trace.status === 'active'
                          ? 'Đang lưu hành'
                          : trace.status === 'pending_handover'
                            ? 'Chờ bàn giao'
                            : trace.status === 'consumed'
                              ? 'Đã tiêu thụ'
                              : trace.status ?? '—'}
                      </span>
                    </div>
                  </div>
                  {trace.processing_summary ? (
                    <div className="trace-field-tile">
                      <SquircleIcon kind="carrot" size="sm" />
                      <div>
                        <span className="trace-field-lbl">Công đoạn chế biến</span>
                        <span className="trace-field-val">{trace.processing_summary}</span>
                      </div>
                    </div>
                  ) : null}
                </div>

                <p className="public-trace-note">
                  🔒 Trang chỉ hiển thị các trường công khai nhằm bảo vệ thông tin kinh doanh
                  của đơn vị tham gia chuỗi.
                </p>
              </div>

              {route && route.points.length > 0 && (
                <div className="public-trace-bento-right">
                  <Suspense fallback={<div className="route-map" aria-busy="true" />}>
                    <RouteMap route={route} lotCode={trace.lot_code ?? ''} />
                  </Suspense>
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
