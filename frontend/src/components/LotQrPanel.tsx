import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import type { Lot, LotDetail } from '../types'
import { displayLotCode, getLotPublicUrl } from '../utils/qr'

export interface LotQrPanelProps {
  lot: Pick<Lot, 'id' | 'name' | 'lot_code'> & Partial<Pick<LotDetail, 'product'>>
  onClose?: () => void
  isDialog?: boolean
}

export function LotQrPanel({ lot, onClose, isDialog = false }: LotQrPanelProps) {
  const lotCode = displayLotCode(lot)
  const publicUrl = getLotPublicUrl(lot)
  const [svgString, setSvgString] = useState<string>('')
  const [pngDataUrl, setPngDataUrl] = useState<string>('')
  const [generatedForUrl, setGeneratedForUrl] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const loading = generatedForUrl !== publicUrl && !error

  useEffect(() => {
    let active = true

    // Tạo cả SVG (đồ họa vector in ấn không vỡ hình) và PNG độ phân giải cao (1024x1024px ~ 867 DPI ở kích thước in 3cm)
    Promise.all([
      QRCode.toString(publicUrl, {
        type: 'svg',
        margin: 2,
        errorCorrectionLevel: 'M',
        width: 350,
      }),
      QRCode.toDataURL(publicUrl, {
        width: 1024,
        margin: 2,
        errorCorrectionLevel: 'M',
      }),
    ])
      .then(([svg, png]) => {
        if (!active) return
        setSvgString(svg)
        setPngDataUrl(png)
        setGeneratedForUrl(publicUrl)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!active) return
        setError(err instanceof Error ? err.message : 'Không thể tạo mã QR.')
      })

    return () => {
      active = false
    }
  }, [publicUrl])

  const downloadPng = () => {
    if (!pngDataUrl) return
    const a = document.createElement('a')
    a.href = pngDataUrl
    a.download = `qr-${lotCode}.png`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const downloadSvg = () => {
    if (!svgString) return
    const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `qr-${lotCode}.svg`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(publicUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback nếu không truy cập được clipboard API
      const input = document.createElement('input')
      input.value = publicUrl
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <section className={`panel-card panel-box lot-qr-panel ${isDialog ? 'lot-qr-dialog-content' : ''}`} aria-label="Sinh mã QR cho lô hàng">
      <div className="panel-head">
        <div>
          <h2>Sinh mã QR cho lô hàng</h2>
          <p className="panel-sub">
            Mã QR dùng để in tem nhãn dán lên bao bì khi đóng gói, phục vụ người tiêu dùng quét truy xuất nguồn gốc.
          </p>
        </div>
        {onClose && isDialog && (
          <button type="button" className="ds-button ds-button-secondary" onClick={onClose} aria-label="Đóng hộp thoại">
            Đóng
          </button>
        )}
      </div>

      {error && <div className="alert-box alert-error" role="alert">{error}</div>}

      <div className="lot-qr-content" style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 280px) 1fr', gap: '1.5rem', alignItems: 'start', marginTop: '1rem' }}>
        {/* Khung hiển thị mã QR */}
        <div className="lot-qr-preview-box" style={{ textAlign: 'center', padding: '1rem', background: 'var(--color-bg-subtle, #f8f9fa)', borderRadius: '8px', border: '1px solid var(--color-border, #e2e8f0)' }}>
          {loading ? (
            <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center' }} aria-busy="true">
              Đang tạo mã QR…
            </div>
          ) : pngDataUrl ? (
            <img
              src={pngDataUrl}
              alt={`Mã QR truy xuất lô ${lotCode}`}
              style={{ width: '100%', maxWidth: '240px', height: 'auto', display: 'block', margin: '0 auto', background: '#fff', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          ) : null}
          <p className="panel-sub" style={{ marginTop: '0.75rem', fontSize: '0.875rem' }}>
            Kích thước in khuyến nghị: <strong>3 cm × 3 cm</strong>
            <br />
            (Độ nét cao, quét nhạy với camera điện thoại)
          </p>
        </div>

        {/* Thông tin và nút tải */}
        <div className="lot-qr-details">
          <dl className="lot-detail-facts" style={{ marginBottom: '1.25rem' }}>
            <div>
              <dt>Nông sản</dt>
              <dd><strong>{lot.product?.name ?? lot.name}</strong></dd>
            </div>
            <div>
              <dt>Mã lô công khai</dt>
              <dd><code>{lotCode}</code></dd>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <dt>Đường dẫn công khai (không dùng ID tự tăng)</dt>
              <dd style={{ wordBreak: 'break-all' }}>
                <a href={publicUrl} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-brand, #2b6cb0)', textDecoration: 'underline' }}>
                  {publicUrl}
                </a>
              </dd>
            </div>
          </dl>

          <p className="panel-sub" style={{ marginBottom: '1.25rem', fontSize: '0.875rem', lineHeight: 1.5 }}>
            🛡️ <em>Quy chuẩn bảo mật & kỹ thuật (N3-65):</em> Đường dẫn công khai sử dụng mã lô định danh công khai <code>{lotCode}</code>, không sử dụng ID khóa số tự tăng của cơ sở dữ liệu để tránh lộ thông tin nội bộ.
          </p>

          <div className="action-row" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            <button
              type="button"
              className="ds-button ds-button-brand"
              onClick={downloadPng}
              disabled={loading || !pngDataUrl}
              aria-label="Tải về tệp ảnh PNG cho mã QR"
            >
              📥 Tải về tệp PNG (Chuẩn in ấn 3cm)
            </button>
            <button
              type="button"
              className="ds-button ds-button-secondary"
              onClick={downloadSvg}
              disabled={loading || !svgString}
              aria-label="Tải về tệp đồ họa vector SVG cho mã QR"
            >
              📐 Tải về tệp SVG (Vector không vỡ hình)
            </button>
            <button
              type="button"
              className="ds-button ds-button-secondary"
              onClick={() => void copyUrl()}
              aria-label="Sao chép đường dẫn công khai"
            >
              {copied ? '✓ Đã sao chép' : '📋 Sao chép liên kết'}
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
