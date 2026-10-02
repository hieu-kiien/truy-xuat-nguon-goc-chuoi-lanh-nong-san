import { JOURNEY_STAGES, type DemoHashBlock } from '../domain/demoScenario'
import { Icon } from './Icons'
import { JourneyMap } from './JourneyMap'
import { JourneyScrubber } from './JourneyScrubber'
import { inspectJourney, stageProgress } from '../domain/journeyModel'

interface TraceCommandCenterProps {
  selectedStage: number
  progress: number
  onProgress: (value: number) => void
  temperatureExcursion: boolean
  chain: DemoHashBlock[]
  onSelectStage: (index: number) => void
  onOpenJourney: () => void
  onOpenIntegrity: () => void
}

export function TraceCommandCenter({
  selectedStage,
  progress,
  onProgress,
  temperatureExcursion,
  chain,
  onSelectStage,
  onOpenJourney,
  onOpenIntegrity,
}: TraceCommandCenterProps) {
  const view = inspectJourney(progress, temperatureExcursion)
  const stage = JOURNEY_STAGES[selectedStage]
  const temperature = view.temperature
  const block = chain[selectedStage]
  const thermalState =
    progress < stageProgress(1)
      ? 'pre-cold'
      : temperature > 8
        ? 'excursion'
        : temperature >= 7.5
          ? 'warning'
          : 'normal'
  const integrityState = block
    ? !block.hashMatches
      ? 'mismatch'
      : block.ancestryValid
        ? 'verified'
        : 'ancestry'
    : 'computing'

  return (
    <section className="view-stack" data-demo-target="trace" aria-labelledby="trace-title">
      <div className="view-heading view-heading-spread">
        <div>
          <p className="eyebrow">KHÔNG GIAN / TRUY XUẤT</p>
          <h1 id="trace-title">Một hành trình.<br />Mọi dấu vết.</h1>
          <p className="view-intro">
            Khám phá một lô hàng qua địa điểm, thời gian và bằng chứng. Kéo con trỏ để nhìn thấy cùng một hành trình chuyển động.
          </p>
        </div>
        <span className="demo-stamp"><span className="stamp-dot" />KỊCH BẢN MINH HỌA</span>
      </div>

      <div className="trace-layout">
        <section className="spatial-panel trace-map-panel" aria-label="Sơ đồ hành trình chuỗi cung ứng">
          <div className="canvas-heading">
            <div>
              <span className="micro-label">LOT / CAU DAT DEMO 01</span>
              <h2>Dâu tây Đà Lạt <span>→</span> TP. Hồ Chí Minh</h2>
            </div>
            <span className="map-scale-label">SƠ ĐỒ · KHÔNG THEO TỶ LỆ</span>
          </div>

          <JourneyMap selectedStage={selectedStage} progress={progress} excursion={temperatureExcursion} onSelect={onSelectStage} />
          <JourneyScrubber progress={progress} excursion={temperatureExcursion} onProgress={onProgress} onSelect={onSelectStage} />
          <div className="trace-map-footer">
            <span><i className="legend-route" /> Hành trình minh họa</span>
            <span><i className="legend-point" /> {selectedStage + 1} / 4 mốc đang chọn</span>
            <button type="button" className="text-action" onClick={onOpenJourney}>
              Mở timeline <Icon name="arrow" size={15} />
            </button>
          </div>
        </section>

        <aside className="trace-inspector" aria-label="Chi tiết mốc hành trình">
          <div className="inspector-topline">
            <span className="micro-label">EVENT / {stage.label}</span>
            <span className={`state-pill state-${thermalState}`}>
              {thermalState === 'normal' ? 'Trong dải' : thermalState === 'warning' ? 'Gần giới hạn' : thermalState === 'excursion' ? 'Ngoại lệ nhiệt' : 'Trước làm lạnh'}
            </span>
          </div>
          <h2 className="event-inspection-anchor">{stage.title}</h2>
          <p className="inspector-location"><Icon name="pin" size={16} />{stage.location}</p>

          <div className="telemetry-readout">
            <div className="reading-primary">
              <span>{view.interpolated ? 'Nhiệt độ nội suy' : 'Nhiệt độ tại mốc'}</span>
              <strong className={`temperature-value temperature-${thermalState}`}>{temperature.toFixed(1)}<small>°C</small></strong>
            </div>
            <div className="reading-secondary">
              <span>Độ ẩm</span>
              <strong>{view.humidity.toFixed(0)}<small>%</small></strong>
            </div>
          </div>

          <p className="inspector-note">
            {thermalState === 'pre-cold'
              ? 'Mốc thu hoạch nằm trước dải nhiệt áp dụng cho vận chuyển lạnh.'
              : thermalState === 'excursion'
                ? 'Ngoại lệ nhiệt độ là sự kiện vật lý trong fixture; trạng thái hash được kiểm tra riêng.'
                : thermalState === 'warning'
                  ? 'Đo gần giới hạn trên của dải minh họa 2–8°C; chưa phải ngoại lệ.'
                  : 'Đọc cảm biến nằm trong dải minh họa 2–8°C cho hành trình lạnh.'}
          </p>

          <div className="inspector-divider" />
          <dl className="detail-list">
            <div><dt>GPS / WGS84</dt><dd>{view.latitude.toFixed(6)}, {view.longitude.toFixed(6)}</dd></div>
            <div><dt>Thời điểm / UTC</dt><dd>{new Date(view.timestamp).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' })}</dd></div>
            <div><dt>Ghi nhận</dt><dd>{view.interpolated ? 'Nội suy từ fixture · không phải mẫu sensor' : 'Fixture cục bộ · không phải sensor live'}</dd></div>
          </dl>

          <button type="button" className={`seal-summary seal-${integrityState}`} onClick={onOpenIntegrity}>
            <span className="seal-icon"><Icon name="shield" size={18} /></span>
            <span><small>EVENT SEAL / SHA-256</small><strong>{block ? `${block.recordedHash.slice(0, 12)}…${block.recordedHash.slice(-8)}` : 'Đang tính digest…'}</strong></span>
            <span className="seal-status">{integrityState === 'verified' ? 'Hợp lệ' : integrityState === 'mismatch' ? 'Sai digest' : integrityState === 'ancestry' ? 'Đứt tổ tiên' : 'Đang tính'}</span>
          </button>
        </aside>
      </div>
    </section>
  )
}
