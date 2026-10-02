import { useEffect, useId, useRef, useState, type PointerEvent, type KeyboardEvent } from 'react'
import { calculateDemoHashChain, JOURNEY_STAGES, type DemoHashBlock } from '../domain/demoScenario'
import { GATEWAY_ROUTE, gatewayPosition, gatewayProgressPath, gatewayProgressAt, gatewayTemperature } from '../domain/gatewayJourney'
import { Icon } from './Icons'

const LABELS = ['Vùng trồng', 'Làm lạnh', 'Xe lạnh', 'Nhập kho']
const CLOCK = new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Ho_Chi_Minh' })
type Calculation = { state: 'pending' } | { state: 'ready'; blocks: DemoHashBlock[] } | { state: 'error'; message: string }

interface GatewayJourneyProps {
  passport: string
  onToggleTheme: () => void
  isDark: boolean
}

export function GatewayJourney({ passport, onToggleTheme, isDark }: GatewayJourneyProps) {
  const [progress, setProgress] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [excursion, setExcursion] = useState(false)
  const [tampered, setTampered] = useState(false)
  const [calculation, setCalculation] = useState<Calculation>({ state: 'pending' })
  const svgRef = useRef<SVGSVGElement>(null)
  const frameRef = useRef<number | null>(null)
  const dragRef = useRef<{ pointerId: number; rect: DOMRect; start: number; last: number; x: number; y: number; moved: boolean } | null>(null)
  const ignoreClick = useRef(false)
  const helpId = useId()
  const rangeId = useId()
  const gradientId = useId()
  const active = Math.round(progress * 3)
  const stage = JOURNEY_STAGES[active]
  const position = gatewayPosition(progress)
  const temperature = gatewayTemperature(progress, excursion)
  const interpolated = Math.abs(progress * 3 - active) > 0.01
  const segment = Math.min(2, Math.floor(progress * 3))
  const time = Date.parse(JOURNEY_STAGES[segment].timestamp) + (Date.parse(JOURNEY_STAGES[segment + 1].timestamp) - Date.parse(JOURNEY_STAGES[segment].timestamp)) * (progress * 3 - segment)
  const block = calculation.state === 'ready' ? calculation.blocks[active] : undefined
  const compromised = block ? !block.ancestryValid : false
  const caption = calculation.state === 'error' ? 'Chưa xác minh' : !block ? 'Đang tính SHA-256…' : !block.hashMatches ? 'Hash không khớp' : compromised ? 'Liên kết trước đã đứt' : 'Bằng chứng hợp lệ'

  useEffect(() => {
    let cancelled = false
    calculateDemoHashChain({ tampered, temperatureExcursion: excursion }).then(
      (blocks) => { if (!cancelled) setCalculation({ state: 'ready', blocks }) },
      (error: unknown) => { if (!cancelled) setCalculation({ state: 'error', message: error instanceof Error ? error.message : 'Không thể tính SHA-256.' }) },
    )
    return () => { cancelled = true }
  }, [tampered, excursion])

  useEffect(() => () => { if (frameRef.current !== null) cancelAnimationFrame(frameRef.current) }, [])

  const selectStage = (index: number) => setProgress(Math.max(0, Math.min(3, index)) / 3)
  const startDrag = (event: PointerEvent<HTMLButtonElement>) => {
    if (!event.isPrimary || event.button !== 0 || dragRef.current || !svgRef.current) return
    ignoreClick.current = false
    const rect = svgRef.current.getBoundingClientRect()
    if (!rect.width || !rect.height) return
    dragRef.current = { pointerId: event.pointerId, rect, start: progress, last: progress, x: event.clientX, y: event.clientY, moved: false }
    event.currentTarget.setPointerCapture(event.pointerId)
    setDragging(true)
  }
  const moveDrag = (event: PointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    if (Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 4) drag.moved = true
    drag.last = gatewayProgressAt((event.clientX - drag.rect.left) / drag.rect.width * 640, (event.clientY - drag.rect.top) / drag.rect.height * 350)
    if (frameRef.current === null) frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null
      if (dragRef.current) setProgress(dragRef.current.last)
    })
  }
  const endDrag = (event: PointerEvent<HTMLButtonElement>, cancelled = false) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    frameRef.current = null
    ignoreClick.current = cancelled || drag.moved
    setProgress(cancelled ? drag.start : Math.round(drag.last * 3) / 3)
    dragRef.current = null
    setDragging(false)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const packageKeys = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    selectStage(event.key === 'Home' ? 0 : event.key === 'End' ? 3 : active + (['ArrowLeft', 'ArrowDown'].includes(event.key) ? -1 : 1))
  }
  const changeScenario = (kind: 'heat' | 'tamper') => {
    setCalculation({ state: 'pending' })
    if (kind === 'heat') setExcursion(!excursion)
    else setTampered(!tampered)
    selectStage(2)
  }
  const reset = () => {
    if (excursion || tampered) setCalculation({ state: 'pending' })
    setExcursion(false)
    setTampered(false)
    selectStage(0)
  }

  return (
    <section className={`gateway-playground ${dragging ? 'is-dragging' : ''} ${excursion ? 'has-excursion' : ''} ${tampered ? 'has-tamper' : ''}`} aria-labelledby="gateway-journey-title">
      <div className="playground-header"><div><span className="playground-kicker">01 / CHẠM THỬ HÀNH TRÌNH</span><h2 id="gateway-journey-title">Một kiện hàng. <em>Bốn dấu vết.</em></h2></div><button type="button" className="playground-theme" onClick={onToggleTheme} aria-label={isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}><Icon name={isDark ? 'sun' : 'moon'} /></button></div>
      <p id={helpId} className="playground-help">Kéo kiện hàng theo tuyến, chạm một chặng hoặc dùng phím mũi tên.</p>
      <div className="playground-map">
        <svg ref={svgRef} viewBox="0 0 640 350" preserveAspectRatio="none" aria-hidden="true">
          <defs><linearGradient id={gradientId} x1="0" y1="1" x2="1" y2="0"><stop offset="0%" stopColor="#b8c793" /><stop offset="100%" stopColor="#9fcbd4" /></linearGradient></defs>
          <g className="playground-terrain"><path d="M0 66C150 162 245-12 408 53S578 178 654 117M-22 98C157 195 223 9 411 91S533 202 664 165M-40 133C136 226 204 65 394 124S559 236 667 202M-30 190C92 282 252 124 414 177S538 277 674 245M-30 277C105 345 295 214 448 271S614 351 681 311" /><path d="M92-16C51 128 196 154 146 350M301-20C227 142 348 176 282 368M509-15C414 97 537 264 472 367" /></g>
          <g className="playground-fields"><path d="M34 138l78-32 20 53-74 33zM58 197l77-34 16 54-75 30zM147 60l66-15 8 40-61 22zM167 265l92-33 14 39-91 34zM448 32l47-9 10 45-51 11z" /></g>
          <path d={GATEWAY_ROUTE} className="playground-route-bed" />
          <path d={GATEWAY_ROUTE} className="playground-route-guide" />
          <path d={gatewayProgressPath(progress)} className="playground-route-progress" stroke={`url(#${gradientId})`} />
          {JOURNEY_STAGES.map((item, index) => { const point = gatewayPosition(index / 3); return <g key={item.id} transform={`translate(${point.x} ${point.y})`}><circle className={`playground-waypoint-halo ${active === index ? 'waypoint-active' : ''}`} r={active === index ? 22 : 13} /><circle className="playground-waypoint" r="5" /></g> })}
        </svg>
        <span className="playground-cartography">CAU DAT / SOUTHERN CORRIDOR</span>
        <span className="playground-map-note">TUYẾN SƠ ĐỒ · DỮ LIỆU MÔ PHỎNG</span>
        {LABELS.map((label, index) => { const point = gatewayPosition(index / 3); return <button type="button" key={label} className={`playground-map-stop stop-${index} ${active === index ? 'is-selected' : ''}`} style={{ left: `${point.x / 640 * 100}%`, top: `${point.y / 350 * 100}%` }} aria-pressed={active === index} onClick={() => selectStage(index)}><span>0{index + 1}</span>{label}</button> })}
        <div className="parcel-anchor" style={{ transform: `translate(${position.x / 640 * 100}%, ${position.y / 350 * 100}%)` }}><button type="button" className="playground-parcel" aria-label={`Kiện hàng tại ${LABELS[active]}. Nhấn để tới chặng kế tiếp.`} aria-describedby={helpId} onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={(event) => endDrag(event, true)} onLostPointerCapture={(event) => endDrag(event, true)} onKeyDown={packageKeys} onClick={(event) => { if (ignoreClick.current && event.detail > 0) { ignoreClick.current = false; return }; selectStage((active + 1) % 4) }}><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 3 29 10v13l-13 7L3 23V10zM3 10l13 7 13-7M16 17v13M10 6l13 7v7" /></svg><span className="parcel-grip" aria-hidden="true"><Icon name="arrow" size={13} /></span></button></div>
      </div>

      <div className="playground-telemetry"><div className="playground-place"><span className="playground-kicker">{CLOCK.format(new Date(time))} ICT / {interpolated ? 'GẦN MỐC' : 'MỐC'} 0{active + 1}</span><h3>{stage.title}</h3><p>{stage.location}</p></div><div className={`playground-temperature ${excursion && active === 2 && temperature > 8 ? 'is-hot' : ''}`}><span><Icon name="thermometer" size={15} />{interpolated ? 'Nhiệt độ nội suy' : 'Nhiệt độ cảm biến mô phỏng'}</span><strong>{temperature.toFixed(1)}<small>°C</small></strong><p>{interpolated ? 'Nội suy mô phỏng giữa hai mốc' : active === 0 ? 'Trước làm lạnh' : active === 1 ? 'Đang làm lạnh' : excursion && active === 2 ? 'Vượt ngưỡng lạnh 8°C' : 'Trong ngưỡng lạnh 2–8°C'}</p></div></div>

      <div className="playground-scrubber"><label htmlFor={rangeId} className="sr-only">Chọn chặng trong hành trình mô phỏng</label><input id={rangeId} type="range" min="0" max="3" step="1" value={active} onChange={(event) => selectStage(Number(event.target.value))} aria-valuetext={`${LABELS[active]}, ${stage.location}, ${temperature.toFixed(1)} độ C`} /><div aria-hidden="true">{LABELS.map((label) => <span key={label}>{label}</span>)}</div></div>

      <div className="playground-experiments"><span className="playground-kicker">THỬ THAY ĐỔI</span><div><button type="button" aria-pressed={excursion} className={excursion ? 'experiment-heat is-active' : 'experiment-heat'} onClick={() => changeScenario('heat')}><Icon name="thermometer" size={16} />{excursion ? 'Khôi phục nhiệt độ' : 'Cho nhiệt độ tăng'}</button><button type="button" aria-pressed={tampered} className={tampered ? 'experiment-tamper is-active' : 'experiment-tamper'} onClick={() => changeScenario('tamper')}><Icon name="integrity" size={16} />{tampered ? 'Khôi phục dữ liệu' : 'Thử sửa dữ liệu'}</button><button type="button" className="experiment-reset" onClick={reset} aria-label="Đặt lại toàn bộ hành trình mô phỏng"><Icon name="refresh" size={16} /></button></div></div>

      <div className={`playground-evidence ${compromised ? 'is-compromised' : ''}`}><div className="playground-evidence-heading"><span><Icon name={compromised ? 'close' : 'shield'} size={17} />{caption}</span><span>SHA-256 / LOCAL</span></div><ol className="playground-seals" aria-label="Tình trạng bốn sự kiện trong chuỗi hash">{JOURNEY_STAGES.map((item, index) => { const seal = calculation.state === 'ready' ? calculation.blocks[index] : undefined; const state = !seal ? 'pending' : !seal.hashMatches ? 'mismatch' : !seal.ancestryValid ? 'ancestry' : 'valid'; return <li key={item.id} className={`seal-${state} ${active === index ? 'seal-selected' : ''}`}><button type="button" aria-label={`Sự kiện ${index + 1}, ${LABELS[index]}: ${state === 'pending' ? 'chưa xác minh' : state === 'mismatch' ? 'hash không khớp' : state === 'ancestry' ? 'tổ tiên không hợp lệ' : 'hash hợp lệ'}`} aria-pressed={active === index} onClick={() => selectStage(index)}><span>0{index + 1}</span><Icon name={state === 'mismatch' || state === 'ancestry' ? 'close' : state === 'valid' ? 'check' : 'clock'} size={14} /></button></li> })}</ol><p className="playground-evidence-copy" role="status">{calculation.state === 'error' ? calculation.message : !block ? 'Đang tính bằng Web Crypto; chưa kết luận toàn vẹn.' : tampered ? 'Trường temp_c ở sự kiện 03 bị sửa sau khi niêm phong. Hash không khớp; sự kiện 04 mất liên kết tổ tiên.' : excursion ? 'Nhiệt độ tăng được ghi nhận và niêm phong đúng. Vượt ngưỡng nhiệt không làm hash sai.' : 'Mỗi dấu vết được nối với hash trước đó. Thử thay đổi để nhìn thấy điều gì còn nguyên, điều gì đứt.'}</p>{block && <details className="playground-hash-detail"><summary>Xem bằng chứng tại mốc 0{active + 1}<Icon name="chevron" size={14} /></summary><div><p><span>temp_c đã niêm phong</span><code>{block.sourceTemperature}</code></p><p><span>temp_c đang kiểm tra</span><code>{String(block.payload.temp_c)}</code></p><div className="hash-reading"><span>HASH ĐÃ GHI</span><code>{block.recordedHash}</code></div><div className="hash-reading"><span>HASH TÍNH LẠI</span><code>{block.computedHash}</code></div><p className="hash-ancestry-caption">{!block.hashMatches ? 'Payload thay đổi: digest không khớp.' : !block.ancestryValid ? 'Digest riêng khớp, nhưng liên kết với tổ tiên không còn hợp lệ.' : 'Digest và liên kết tổ tiên đều hợp lệ.'}</p></div></details>}</div>
      <div className="playground-footer"><span key={passport}><Icon name="pin" size={14} />Passport: {passport}</span><span>Khám phá tự do · Không ghi dữ liệu lên máy chủ</span></div>
    </section>
  )
}
