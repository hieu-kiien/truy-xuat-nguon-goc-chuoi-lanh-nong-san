import { useId, useState } from 'react'
import { JOURNEY_STAGES } from '../domain/demoScenario'
import { GATEWAY_ROUTE, gatewayPosition, gatewayProgressPath } from '../domain/gatewayJourney'
import { inspectJourney } from '../domain/journeyModel'
import { Icon } from './Icons'

interface JourneyMapProps {
  selectedStage: number
  progress: number
  excursion: boolean
  onSelect: (index: number) => void
  compact?: boolean
}

export function JourneyMap({ selectedStage, progress, excursion, onSelect, compact = false }: JourneyMapProps) {
  const [focused, setFocused] = useState(false)
  const [zoom, setZoom] = useState(1)
  const gridId = useId()
  const gradientId = useId()
  const view = inspectJourney(progress, excursion)
  const point = gatewayPosition(view.routeProgress)
  const target = gatewayPosition(selectedStage / 3)
  const scale = focused ? 1.55 : zoom
  const dx = focused ? (50 - target.x / 640 * 100) * scale : 0
  const dy = focused ? (50 - target.y / 350 * 100) * scale : 0

  return <section className={`journey-map-canvas ${compact ? 'map-compact' : ''}`} aria-label="Sơ đồ chuỗi cung ứng tương tác">
    <div className="journey-map-topline"><span>CAU DAT → SAIGON / LOT 01</span><span>SƠ ĐỒ MINH HỌA</span></div>
    <div className="journey-map-window">
      <div className="journey-map-camera" style={{ transform: `translate(${dx}%, ${dy}%) scale(${scale})` }}>
        <svg viewBox="0 0 640 350" preserveAspectRatio="none" aria-hidden="true">
          <defs><pattern id={gridId} width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="currentColor" strokeOpacity=".08" /></pattern><linearGradient id={gradientId} x1="0" x2="1"><stop stopColor="var(--route-start)" /><stop offset="1" stopColor="var(--route-end)" /></linearGradient></defs>
          <rect width="640" height="350" fill={`url(#${gridId})`} />
          <g className="journey-landforms"><path d="M-15 160C70 210 97 83 204 83s172 56 237 15S551 57 665 132v74C541 139 524 250 413 250s-124-86-216-62S66 293-15 250z" /><path d="M-30 55C136 153 183-20 350 47s151 87 324 33M-30 81C136 179 183 6 350 73s151 87 324 33M-30 285C125 193 264 334 443 269s144-67 221-49M-30 309C125 217 264 358 443 293s144-67 221-49" /></g>
          <g className="journey-field-parcels"><path d="M30 127l69-30 21 48-69 31zM49 182l73-31 15 42-68 30zM151 55l62-13 6 39-59 17zM168 264l91-29 13 38-91 34zM448 28l48-9 12 44-52 13z" /></g>
          <path d={GATEWAY_ROUTE} className="journey-road-bed" />
          <path d={GATEWAY_ROUTE} className="journey-road-guide" />
          {excursion && <path d="M230 115C310 115 320 235 410 235" className="journey-thermal-excursion" />}
          <path d={gatewayProgressPath(view.routeProgress)} className="journey-road-progress" stroke={`url(#${gradientId})`} />
          {JOURNEY_STAGES.map((stage, index) => { const p = gatewayPosition(index / 3); return <g key={stage.id} transform={`translate(${p.x} ${p.y})`}><circle r={selectedStage === index ? 18 : 10} className={`journey-map-ring ${selectedStage === index ? 'ring-selected' : ''}`} /><circle r="4" className="journey-map-dot" /></g> })}
        </svg>
        <ol className="journey-map-markers" aria-label="Chọn chặng trên bản đồ">{JOURNEY_STAGES.map((stage, index) => { const p = gatewayPosition(index / 3); return <li key={stage.id} className={`journey-marker marker-${index}`} style={{ left: `${p.x / 640 * 100}%`, top: `${p.y / 350 * 100}%` }}><button type="button" aria-label={`Mốc ${index + 1}: ${stage.title}, ${stage.location}`} aria-pressed={selectedStage === index} onClick={() => onSelect(index)} onFocus={() => { if (focused || zoom > 1) onSelect(index) }} className={selectedStage === index ? 'is-selected' : ''}><span>0{index + 1}</span><Icon name={index === 0 ? 'agro' : index === 2 ? 'truck' : index === 3 ? 'layers' : 'thermometer'} size={17} /><strong>{stage.title}</strong></button></li> })}</ol>
        <div className="journey-vehicle-anchor" style={{ transform: `translate(${point.x / 640 * 100}%, ${point.y / 350 * 100}%)` }}><span className="journey-vehicle" aria-hidden="true"><Icon name={view.nearest === 0 ? 'agro' : 'truck'} size={23} /></span></div>
      </div>
      <span className="origin-context"><Icon name="agro" size={14} />Nguồn gốc: vùng trồng Cầu Đất</span>
      <div className="journey-map-controls" role="group" aria-label="Điều khiển góc nhìn bản đồ"><button type="button" aria-pressed={focused} onClick={() => { setFocused(!focused); setZoom(1) }}><Icon name="pin" size={16} />{focused ? 'Toàn tuyến' : 'Theo mốc'}</button><button type="button" aria-label="Phóng to sơ đồ" disabled={focused || zoom >= 1.6} onClick={() => setZoom(Math.min(1.6, zoom + .2))}><Icon name="zoom-in" size={17} /></button><button type="button" aria-label="Thu nhỏ sơ đồ" disabled={focused || zoom <= 1} onClick={() => setZoom(Math.max(1, zoom - .2))}><Icon name="zoom-out" size={17} /></button></div>
    </div>
    <div className="journey-map-caption"><span><i />{view.interpolated ? 'Vị trí nội suy mô phỏng' : `Mốc đã ghi 0${selectedStage + 1}`}</span><span>Nguồn gốc là ngữ cảnh; chuỗi gồm 4 sự kiện</span></div>
  </section>
}
