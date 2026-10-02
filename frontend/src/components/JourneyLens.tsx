import { JOURNEY_STAGES, type DemoHashBlock } from '../domain/demoScenario'
import type { WorkspaceTab } from './FarmWorkspace'
import { Icon } from './Icons'

const LENSES = [{ tab: 'overview', label: 'Không gian', icon: 'atlas' }, { tab: 'journey', label: 'Thời gian', icon: 'clock' }, { tab: 'integrity', label: 'Bằng chứng', icon: 'integrity' }] as const

export function JourneyLens({ tab, selected, block, onNavigate }: { tab: WorkspaceTab; selected: number; block?: DemoHashBlock; onNavigate: (tab: WorkspaceTab) => void }) {
  const stage = JOURNEY_STAGES[selected]
  return <div className="journey-lens"><div className="lens-identity"><span className="lens-event-number" key={stage.id}>0{selected + 1}</span><div><small>ĐỐI TƯỢNG ĐANG KHÁM PHÁ</small><strong>{stage.title}</strong></div><span className={`lens-seal ${block && !block.ancestryValid ? 'lens-seal-broken' : ''}`}><Icon name={block && !block.ancestryValid ? 'close' : 'shield'} size={15} />{block ? !block.hashMatches ? 'Hash lệch' : !block.ancestryValid ? 'Đứt tổ tiên' : 'Seal hợp lệ' : 'Đang tính'}</span></div><div className="lens-navigation" role="group" aria-label="Đổi góc nhìn cùng một sự kiện">{LENSES.map((lens) => <button type="button" key={lens.tab} aria-pressed={lens.tab === tab} onClick={() => onNavigate(lens.tab)}><Icon name={lens.icon} size={17} /><span>{lens.label}</span></button>)}</div></div>
}
