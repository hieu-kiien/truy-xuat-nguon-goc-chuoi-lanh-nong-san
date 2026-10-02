import { useId } from 'react'
import { JOURNEY_STAGES } from '../domain/demoScenario'
import { inspectJourney } from '../domain/journeyModel'
import { Icon } from './Icons'

export function JourneyScrubber({ progress, excursion, onProgress, onSelect }: { progress: number; excursion: boolean; onProgress: (value: number) => void; onSelect: (index: number) => void }) {
  const id = useId()
  const view = inspectJourney(progress, excursion)
  const time = new Date(view.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })
  return <div className="journey-time-control"><div className="time-control-label"><label htmlFor={id}>Con trỏ thời gian</label><span>{time} UTC {view.interpolated ? '· Nội suy mô phỏng' : '· Mốc đã ghi'}</span></div><div className="time-control-track"><button type="button" aria-label="Tới sự kiện trước" disabled={progress === 0} onClick={() => onSelect(Math.max(0, view.nearest - 1))}><Icon name="arrow" size={16} /></button><input id={id} type="range" min="0" max="1000" step="1" value={Math.round(progress * 1000)} onChange={(event) => onProgress(Number(event.target.value) / 1000)} aria-valuetext={`${time} UTC, ${view.temperature.toFixed(1)} độ C, ${view.interpolated ? 'giá trị nội suy, gần' : 'mốc'} ${JOURNEY_STAGES[view.nearest].title}`} /><button type="button" aria-label="Tới sự kiện tiếp" disabled={progress === 1} onClick={() => onSelect(Math.min(3, view.nearest + 1))}><Icon name="arrow" size={16} /></button></div><div className="time-control-endpoints"><span>06:00 / THU HOẠCH</span><span>14:00 / NHẬP KHO</span></div></div>
}
