import type { Lot } from '../types'
import { displayLotCode } from './qr'

/** Tên tệp hồ sơ truy xuất tải về, khớp định dạng backend sinh ra (N3-72). */
export function lotReportFileName(lot: Pick<Lot, 'lot_code' | 'id'>): string {
  const safeCode = displayLotCode(lot)
    .replace(/[^A-Za-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return `ho-so-truy-xuat-${safeCode || 'lo'}.pdf`
}
