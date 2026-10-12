import type { Lot } from '../types'
import { grams } from './mass'

export function eligibleMergeCandidates(items: Lot[], source: Lot): Lot[] {
  return [...new Map(items.filter(item => source.product_id && item.id !== source.id
    && item.product_id === source.product_id
    && item.current_holder_organization_id === source.current_holder_organization_id
    && item.status === 'active' && (grams(item.remaining_quantity) ?? 0n) > 0n
  ).map(item => [item.id, item])).values()]
}
