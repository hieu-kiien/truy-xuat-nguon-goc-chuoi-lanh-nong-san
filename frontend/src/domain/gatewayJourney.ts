// Local schematic geometry, not a surveyed road or farm boundary.
export const GATEWAY_ROUTE = 'M60 234C110 230 110 115 230 115C310 115 320 235 410 235C490 235 485 82 580 70'
const CURVES = [
  [[60, 234], [110, 230], [110, 115], [230, 115]],
  [[230, 115], [310, 115], [320, 235], [410, 235]],
  [[410, 235], [490, 235], [485, 82], [580, 70]],
] as const

export function gatewayPosition(progress: number) {
  const bounded = Math.max(0, Math.min(1, progress)) * 3
  const segment = Math.min(2, Math.floor(bounded))
  const t = bounded - segment
  const points = CURVES[segment]
  const weights = [(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3]
  return {
    x: points.reduce((sum, point, index) => sum + point[0] * weights[index], 0),
    y: points.reduce((sum, point, index) => sum + point[1] * weights[index], 0),
  }
}

// De Casteljau's split keeps the drawn prefix exactly at the parcel position.
export function gatewayProgressPath(progress: number): string {
  const bounded = Math.max(0, Math.min(1, progress)) * 3
  let path = 'M60 234'
  for (const [index, points] of CURVES.entries()) {
    const t = Math.max(0, Math.min(1, bounded - index))
    if (t === 0) break
    const lerp = (a: readonly number[], b: readonly number[]) => a.map((value, axis) => value + (b[axis] - value) * t)
    const a = lerp(points[0], points[1])
    const b = lerp(points[1], points[2])
    const c = lerp(points[2], points[3])
    const d = lerp(a, b)
    const end = lerp(d, lerp(b, c))
    path += `C${a.join(' ')} ${d.join(' ')} ${end.join(' ')}`
  }
  return path
}

const ROUTE_SAMPLES = Array.from({ length: 241 }, (_, index) => ({
  progress: index / 240,
  ...gatewayPosition(index / 240),
}))

export function gatewayProgressAt(x: number, y: number): number {
  let best = ROUTE_SAMPLES[0]
  let distance = Infinity
  for (const point of ROUTE_SAMPLES) {
    const candidate = (point.x - x) ** 2 + (point.y - y) ** 2
    if (candidate < distance) {
      best = point
      distance = candidate
    }
  }
  return best.progress
}

export function gatewayTemperature(progress: number, excursion: boolean): number {
  const values = [14.2, 7.6, excursion ? 9.9 : 3.5, 4]
  const bounded = Math.max(0, Math.min(1, progress)) * 3
  const segment = Math.min(2, Math.floor(bounded))
  return values[segment] + (values[segment + 1] - values[segment]) * (bounded - segment)
}
