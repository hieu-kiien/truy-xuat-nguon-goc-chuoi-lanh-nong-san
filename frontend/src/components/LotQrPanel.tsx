import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import type { Lot, LotDetail } from '../types'
import {
  QR_ERROR_CORRECTION,
  QR_PNG_SIZE_PX,
  QR_QUIET_ZONE_MODULES,
  applyPrintSize,
  displayLotCode,
  getLotPublicUrl,
  qrFileName,
} from '../utils/qr'

export interface LotQrPanelProps {
  lot: Pick<Lot, 'id' | 'name' | 'lot_code'> & Partial<Pick<LotDetail, 'product'>>
}

interface QrAssets {
  url: string
  png: string
  svg: string
}

const copyFallback = (text: string) => {
  const input = document.createElement('input')
  input.value = text
  document.body.appendChild(input)
  input.select()
  document.execCommand('copy')
  document.body.removeChild(input)
}

export function LotQrPanel({ lot }: LotQrPanelProps) {
  const lotCode = displayLotCode(lot)
  const publicUrl = getLotPublicUrl(lot)
  const [assets, setAssets] = useState<QrAssets | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const ready = assets?.url === publicUrl
  const loading = !ready && error === null

  useEffect(() => {
    let active = true

    Promise.all([
      QRCode.toDataURL(publicUrl, {
        width: QR_PNG_SIZE_PX,
        margin: QR_QUIET_ZONE_MODULES,
        errorCorrectionLevel: QR_ERROR_CORRECTION,
      }),
      QRCode.toString(publicUrl, {
        type: 'svg',
        margin: QR_QUIET_ZONE_MODULES,
        errorCorrectionLevel: QR_ERROR_CORRECTION,
      }),
    ])
      .then(([png, svg]) => {
        if (!active) return
        setAssets({ url: publicUrl, png, svg: applyPrintSize(svg) })
        setError(null)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason.message : 'Không thể tạo mã QR cho lô này.')
      })

    return () => {
      active = false
    }
  }, [publicUrl])

  const downloadFile = (href: string, fileName: string) => {
    const anchor = document.createElement('a')
    anchor.href = href
    anchor.download = fileName
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
  }

  const downloadPng = () => {
    if (assets) downloadFile(assets.png, qrFileName(lot, 'png'))
  }

  const downloadSvg = () => {
    if (!assets) return
    const blob = new Blob([assets.svg], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    downloadFile(url, qrFileName(lot, 'svg'))
    URL.revokeObjectURL(url)
  }

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(publicUrl)
    } catch {
      copyFallback(publicUrl)
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section className="lot-qr" aria-label="Sinh mã QR cho lô hàng">
      <p className="panel-sub lot-qr-intro">
        In tem dán lên bao bì khi đóng gói. Người tiêu dùng quét mã để mở trang tra cứu
        công khai của lô, không cần đăng nhập.
      </p>

      {!lot.lot_code && (
        <div className="chip-warning lot-qr-warning" role="status">
          Lô chưa có mã công khai nên mã QR có thể không tra cứu được. Hãy lưu lô để hệ thống
          sinh mã lô trước khi in tem.
        </div>
      )}

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}

      <div className="lot-qr-layout">
        <div className="lot-qr-preview">
          <div className="lot-qr-label" aria-hidden={loading || undefined}>
            {loading ? (
              <div className="lot-qr-placeholder" aria-busy="true" aria-live="polite">
                Đang tạo mã QR…
              </div>
            ) : assets ? (
              <>
                <img
                  className="lot-qr-label-image"
                  src={assets.png}
                  alt={`Mã QR tra cứu lô ${lotCode}`}
                  width={QR_PNG_SIZE_PX}
                  height={QR_PNG_SIZE_PX}
                />
                <span className="lot-qr-label-code">{lotCode}</span>
              </>
            ) : null}
          </div>
          <p className="lot-qr-caption">
            Kích thước in: <strong>30 × 30 mm</strong> (ảnh xem trước được phóng to)
          </p>
        </div>

        <div className="lot-qr-info">
          <dl className="lot-detail-facts">
            <div>
              <dt>Nông sản</dt>
              <dd>{lot.product?.name ?? lot.name}</dd>
            </div>
            <div>
              <dt>Mã lô công khai</dt>
              <dd>
                <code>{lotCode}</code>
              </dd>
            </div>
          </dl>

          <p className="lot-qr-url-label">Đường dẫn công khai trên tem</p>
          <a className="lot-qr-url" href={publicUrl} target="_blank" rel="noopener noreferrer">
            {publicUrl}
          </a>

          <div className="action-row lot-qr-actions">
            <button
              type="button"
              className="ds-button ds-button-brand"
              onClick={downloadPng}
              disabled={loading || !assets}
              aria-label="Tải mã QR định dạng PNG"
            >
              Tải PNG
            </button>
            <button
              type="button"
              className="ds-button ds-button-secondary"
              onClick={downloadSvg}
              disabled={loading || !assets}
              aria-label="Tải mã QR định dạng SVG"
            >
              Tải SVG
            </button>
            <button
              type="button"
              className="ds-button ds-button-secondary"
              onClick={() => void copyUrl()}
              aria-label="Sao chép đường dẫn công khai của lô"
            >
              {copied ? 'Đã sao chép' : 'Sao chép liên kết'}
            </button>
          </div>

          <p className="panel-sub lot-qr-hint">
            PNG 1024px (~867 DPI ở khổ 3 cm) để in nhanh; SVG là vector, in lớn không vỡ hình.
            Mã dùng mức sửa lỗi Q và vùng trắng 4 module để camera điện thoại quét ổn định.
          </p>
        </div>
      </div>
    </section>
  )
}
