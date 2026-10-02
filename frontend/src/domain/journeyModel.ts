import { JOURNEY_STAGES } from './demoScenario.ts'

const TIMES = JOURNEY_STAGES.map((stage) => Date.parse(stage.timestamp))
export const JOURNEY_START = TIMES[0]
export const JOURNEY_END = TIMES.at(-1)!
export const stageProgress = (index: number) => (TIMES[index] - JOURNEY_START) / (JOURNEY_END - JOURNEY_START)

export function inspectJourney(progress: number, excursion: boolean) {
  const bounded = Math.max(0, Math.min(1, progress))
  const timestamp = JOURNEY_START + bounded * (JOURNEY_END - JOURNEY_START)
  let segment = 0
  while (segment < TIMES.length - 2 && timestamp > TIMES[segment + 1]) segment++
  const mix = (timestamp - TIMES[segment]) / (TIMES[segment + 1] - TIMES[segment])
  const nearest = mix <= .5 ? segment : segment + 1
  const readings = JOURNEY_STAGES.map((stage, index) => index === 2 && excursion ? 9.9 : stage.temperature)
  const interpolate = (a: number, b: number) => a + (b - a) * mix
  return {
    progress: bounded,
    timestamp,
    nearest,
    routeProgress: (segment + mix) / 3,
    temperature: interpolate(readings[segment], readings[segment + 1]),
    humidity: interpolate(JOURNEY_STAGES[segment].humidity, JOURNEY_STAGES[segment + 1].humidity),
    latitude: interpolate(JOURNEY_STAGES[segment].latitude, JOURNEY_STAGES[segment + 1].latitude),
    longitude: interpolate(JOURNEY_STAGES[segment].longitude, JOURNEY_STAGES[segment + 1].longitude),
    interpolated: Math.abs(timestamp - TIMES[nearest]) > 1000,
  }
}

export function thermalState(index: number, value: number) {
  return index === 0 ? 'pre-cold' : value > 8 ? 'excursion' : value >= 7.5 ? 'warning' : 'normal'
}
