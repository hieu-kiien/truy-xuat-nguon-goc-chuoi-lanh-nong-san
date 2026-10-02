import { JOURNEY_STAGES, type DemoHashBlock } from '../domain/demoScenario'
import { Icon } from './Icons'
import { JourneyMap } from './JourneyMap'
import { JourneyScrubber } from './JourneyScrubber'
import { inspectJourney, stageProgress } from '../domain/journeyModel'

interface ColdChainJourneyProps {
  selectedStage: number
  progress: number
  onProgress: (value: number) => void
  temperatureExcursion: boolean
  tampered: boolean
  chain: DemoHashBlock[]
  onSelectStage: (index: number) => void
  onToggleExcursion: () => void
  onOpenIntegrity: () => void
}

const CHART_HEIGHT = 224
const chartY = (value: number) => 204 - ((value - 0) / 16) * 170

export function ColdChainJourney({
  selectedStage,
  progress,
  onProgress,
  temperatureExcursion,
  tampered,
  chain,
  onSelectStage,
  onToggleExcursion,
  onOpenIntegrity,
}: ColdChainJourneyProps) {
  const readings = JOURNEY_STAGES.map((stage, index) =>
    index === 2 && temperatureExcursion ? 9.9 : stage.temperature
  )
  const view = inspectJourney(progress, temperatureExcursion)
  const selected = JOURNEY_STAGES[selectedStage]
  const reading = view.temperature
  const isPreCold = progress < stageProgress(1)
  const isExcursion = !isPreCold && reading > 8
  const isWarning = !isPreCold && reading >= 7.5 && reading <= 8
  const block = chain[selectedStage]
  const integrityOk = block?.hashMatches && block?.ancestryValid
  const points = readings
    .map((value, index) => `${60 + stageProgress(index) * 660},${chartY(value)}`)
    .join(' ')

  return (
    <section className="view-stack" data-demo-target="journey" aria-labelledby="journey-title">
      <div className="view-heading view-heading-spread">
        <div>
          <p className="eyebrow">Mission 02 / Cold chain</p>
          <h1 id="journey-title">Hành trình theo thời gian.</h1>
          <p className="view-intro">Chọn một mốc để đồng bộ vị trí, nhiệt độ, độ ẩm và event seal.</p>
        </div>
        <span className="demo-stamp"><span className="stamp-dot" />FIXTURE · 30 SEP 2026 UTC</span>
      </div>

      <div className="journey-summary-row">
        <div className="journey-route-name">
          <span className="route-glyph" aria-hidden="true"><Icon name="trace" size={22} /></span>
          <div><small>LOT / CAU DAT DEMO 01</small><strong>Cầu Đất <Icon name="arrow" size={15} /> Kho TP.HCM</strong></div>
        </div>
        <div className="journey-summary-cell"><small>Mốc đang xem</small><strong>{selectedStage + 1} <span>/ 4</span></strong></div>
        <div className="journey-summary-cell"><small>Độ toàn vẹn chuỗi</small><strong className={integrityOk ? 'ink-positive' : 'ink-danger'}>{block ? integrityOk ? 'Seal hợp lệ' : 'Chuỗi gián đoạn' : 'Đang tính'}</strong></div>
        <button type="button" className={`button ${temperatureExcursion ? 'button-warning-active' : 'button-quiet'}`} onClick={onToggleExcursion}>
          <Icon name="thermometer" size={16} />{temperatureExcursion ? 'Khôi phục fixture nhiệt' : 'Tạo ngoại lệ nhiệt cục bộ'}
        </button>
      </div>

      <JourneyMap compact selectedStage={selectedStage} progress={progress} excursion={temperatureExcursion} onSelect={onSelectStage} />
      <div className="journey-layout">
        <section className="surface chart-surface" aria-labelledby="thermal-chart-title">
          <div className="section-heading">
            <div><span className="micro-label">TELEMETRY / TEMPERATURE</span><h2 id="thermal-chart-title">Nhiệt độ theo mốc</h2></div>
            <span className={`state-pill state-${isExcursion ? 'excursion' : isWarning ? 'warning' : isPreCold ? 'pre-cold' : 'normal'}`}>
              {isPreCold ? 'Trước làm lạnh' : isExcursion ? 'Ngoại lệ mô phỏng' : isWarning ? 'Cảnh báo gần giới hạn' : 'Trong dải'}
            </span>
          </div>

          <div className="thermal-chart-wrap">
            <svg className="thermal-chart" viewBox={`0 0 760 ${CHART_HEIGHT}`} role="img" aria-label="Biểu đồ fixture nhiệt độ. Dải 2 đến 8 độ C áp dụng sau khi làm lạnh sơ bộ.">
              <rect x={60 + stageProgress(1) * 660} y={chartY(8)} width={720 - (60 + stageProgress(1) * 660)} height={chartY(2) - chartY(8)} rx="8" className="chart-safe-band" />
              <text x="246" y={chartY(8) + 16} className="chart-band-label">DẢI MINH HỌA 2–8°C · TỪ LÀM LẠNH</text>
              {[0, 4, 8, 12, 16].map((tick) => (
                <g key={tick}>
                  <line x1="53" x2="738" y1={chartY(tick)} y2={chartY(tick)} className="chart-gridline" />
                  <text x="15" y={chartY(tick) + 4} className="chart-axis-label">{tick}°</text>
                </g>
              ))}
              <polyline points={points} className="thermal-line" />
              <line x1={60 + progress * 660} x2={60 + progress * 660} y1="24" y2="205" className="thermal-cursor" />
              <circle cx={60 + progress * 660} cy={chartY(view.temperature)} r="7" className="thermal-cursor-point" />
              {readings.map((value, index) => {
                const current = index === selectedStage
                const pointTone = index === 0 ? 'pre-cold' : value > 8 ? 'excursion' : value >= 7.5 ? 'warning' : 'normal'
                return (
                  <g key={JOURNEY_STAGES[index].id} className={`thermal-point thermal-point-${pointTone} ${current ? 'thermal-point-current' : ''}`}>
                    <circle cx={60 + stageProgress(index) * 660} cy={chartY(value)} r={current ? 9 : 6} />
                    <text x={60 + stageProgress(index) * 660} y={chartY(value) - 16} textAnchor="middle" className="chart-value-label">{value.toFixed(1)}°C</text>
                  </g>
                )
              })}
              {JOURNEY_STAGES.map((stage, index) => (
                <text key={stage.id} x={60 + stageProgress(index) * 660} y="220" textAnchor="middle" className={`chart-stage-label ${index === selectedStage ? 'chart-stage-current' : ''}`}>{stage.label} · {stage.title}</text>
              ))}
            </svg>
          </div>

          <p className="chart-interpolation-note">Đường nối và con trỏ là nội suy mô phỏng giữa 4 mẫu đã ghi; không có nguồn sensor live.</p>
          <div className="chart-legend">
            <span><i className="legend-normal" />Normal</span>
            <span><i className="legend-warning" />Gần giới hạn (≥7.5°C)</span>
            <span><i className="legend-excursion" />Ngoại lệ (&gt;8°C)</span>
          </div>

          <JourneyScrubber progress={progress} excursion={temperatureExcursion} onProgress={onProgress} onSelect={onSelectStage} />
        </section>

        <aside className="surface journey-inspector" aria-label="Chi tiết event được chọn">
          <div className="inspector-topline"><span className="micro-label">EVENT / {selected.label}</span><Icon name="clock" size={17} /></div>
          <h2 className="event-inspection-anchor">{selected.title}</h2>
          <p className="inspector-location"><Icon name="pin" size={16} />{selected.location}</p>

          <div className={`journey-reading ${isExcursion ? 'journey-reading-danger' : isWarning ? 'journey-reading-warning' : ''}`}>
            <strong>{reading.toFixed(1)}<small>°C</small></strong>
            <span>{view.interpolated ? 'Nhiệt độ nội suy mô phỏng' : isPreCold ? 'Tiền làm lạnh' : isExcursion ? 'Ngoại lệ nhiệt độ' : isWarning ? 'Gần giới hạn trên' : 'Trong dải 2–8°C'}</span>
          </div>
          <dl className="detail-list detail-list-tight">
            <div><dt>Độ ẩm</dt><dd>{view.humidity.toFixed(0)}% RH</dd></div>
            <div><dt>GPS</dt><dd>{view.latitude.toFixed(6)}, {view.longitude.toFixed(6)}</dd></div>
            <div><dt>Event seal</dt><dd>{block ? `${block.recordedHash.slice(0, 10)}…` : 'Đang tính'}</dd></div>
          </dl>

          <div className={`integrity-separation ${tampered ? 'integrity-separation-alert' : ''}`}>
            <Icon name="shield" size={17} />
            <p>
              <strong>{tampered ? 'Có can thiệp vào payload minh họa' : 'Toàn vẹn được đánh giá riêng'}</strong>
              <span>{tampered ? 'Đây là mô phỏng sửa event; ngoại lệ nhiệt không tự tạo ra lỗi hash.' : 'Ngoại lệ nhiệt (nếu có) vẫn có thể được ghi nhận và niêm phong hợp lệ.'}</span>
            </p>
          </div>
          <button type="button" className="text-action text-action-block" onClick={onOpenIntegrity}>Mở phòng forensic <Icon name="arrow" size={15} /></button>
        </aside>
      </div>

      <div className="journey-event-strip" role="group" aria-label="Chọn event theo thứ tự thời gian">
        {JOURNEY_STAGES.map((stage, index) => {
          const temp = readings[index]
          const state = index === 0 ? 'pre-cold' : temp > 8 ? 'excursion' : temp >= 7.5 ? 'warning' : 'normal'
          return (
            <button key={stage.id} type="button" className={`journey-event-button ${selectedStage === index ? 'journey-event-selected' : ''}`} aria-pressed={selectedStage === index} onClick={() => onSelectStage(index)}>
              <span className={`event-dot event-dot-${state}`} />
              <span><small>{stage.label} / {new Date(stage.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })} UTC</small><strong>{stage.title}</strong></span>
              <b>{temp.toFixed(1)}°C</b>
            </button>
          )
        })}
      </div>
    </section>
  )
}
