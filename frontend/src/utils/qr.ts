import type { Lot } from '../types'

/** Trang tra cứu công khai, không yêu cầu đăng nhập (S-48). */
export const PUBLIC_TRACE_PATH = '/truy-xuat'

/** Kích thước in tiêu chuẩn của tem QR (mm). */
export const QR_PRINT_SIZE_MM = 30

/** Ảnh PNG 1024px in trên 30mm tương đương ~867 DPI, dư chuẩn in ấn 300 DPI. */
export const QR_PNG_SIZE_PX = 1024

/** Vùng trắng bao quanh mã (quiet zone) theo chuẩn QR: tối thiểu 4 module. */
export const QR_QUIET_ZONE_MODULES = 4

/** Mức sửa lỗi Q (~25%) để tem vẫn quét được khi bị xước hoặc mờ. */
export const QR_ERROR_CORRECTION = 'Q'

type LotIdentity = Pick<Lot, 'lot_code' | 'id'>

/**
 * Mã hiển thị của lô: ưu tiên mã công khai do backend sinh (8 ký tự),
 * chỉ dùng 8 ký tự đầu UUID làm phương án dự phòng khi bản ghi cũ chưa có mã.
 */
export function displayLotCode(lot: LotIdentity): string {
  return lot.lot_code ?? lot.id.slice(0, 8)
}

/**
 * URL công khai của lô. Dùng đúng trang `/truy-xuat` và truyền mã lô qua
 * `?code=` để trang tra cứu tự động tra cứu khi người tiêu dùng quét tem.
 * Không dùng ID tự tăng của cơ sở dữ liệu.
 */
export function getLotPublicUrl(lot: LotIdentity): string {
  const code = displayLotCode(lot)
  const origin =
    typeof window !== 'undefined' && window.location?.origin
      ? window.location.origin
      : 'https://agrochain.local'
  return `${origin}${PUBLIC_TRACE_PATH}?code=${encodeURIComponent(code)}`
}

/**
 * Gắn kích thước vật lý (mm) vào SVG do thư viện qrcode sinh ra.
 * Nhờ vậy phần mềm in/xem SVG in ra đúng 3 cm thay vì phóng to hết khổ giấy.
 */
export function applyPrintSize(svg: string, sizeMm: number = QR_PRINT_SIZE_MM): string {
  return svg.replace(/^<svg\b([^>]*)>/, (_match, attributes: string) => {
    const withoutSize = attributes
      .replace(/\s(?:width|height)="[^"]*"/g, '')
      .replace(/\s+xmlns="[^"]*"/g, '')
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${sizeMm}mm" height="${sizeMm}mm"${withoutSize}>`
  })
}

/** Bỏ ký tự không hợp lệ trên tên tệp tải về. */
export function qrFileName(lot: LotIdentity, extension: 'png' | 'svg'): string {
  const safeCode = displayLotCode(lot).replace(/[^A-Za-z0-9_-]+/g, '-')
  return `qr-${safeCode}.${extension}`
}
