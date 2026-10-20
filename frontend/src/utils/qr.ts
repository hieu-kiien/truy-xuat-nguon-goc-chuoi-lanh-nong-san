import type { Lot } from '../types'

export function displayLotCode(lot: Pick<Lot, 'lot_code' | 'id'>): string {
  return lot.lot_code ?? lot.id.slice(0, 8)
}

export function getLotPublicUrl(lot: Pick<Lot, 'lot_code' | 'id'>): string {
  const code = displayLotCode(lot)
  const origin = typeof window !== 'undefined' && window.location?.origin
    ? window.location.origin
    : 'https://agrochain.local'
  return `${origin}/trace/${encodeURIComponent(code)}`
}
