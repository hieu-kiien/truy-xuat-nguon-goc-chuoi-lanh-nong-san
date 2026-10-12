export function grams(value: string): bigint | null {
  if (value.length > 32 || !/^\d+(\.\d{1,3})?$/.test(value)) return null
  const [whole, fraction = ''] = value.split('.')
  return BigInt(whole) * 1000n + BigInt(fraction.padEnd(3, '0'))
}

export function formatGrams(value: bigint): string {
  const absolute = value < 0n ? -value : value
  return `${value < 0n ? '-' : ''}${absolute / 1000n}.${String(absolute % 1000n).padStart(3, '0')}`
}

export function splitSummary(amounts: string[], available: string) {
  const values = amounts.map(grams)
  const total = values.reduce<bigint>((sum, value) => sum + (value ?? 0n), 0n)
  const remaining = (grams(available) ?? 0n) - total
  return { total, remaining, valid: amounts.length > 0 && values.every(value => value !== null && value > 0n) && remaining >= 0n }
}
