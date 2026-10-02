import { useEffect, useRef } from 'react'
import { DEMO_CHAPTERS } from '../domain/demoScenario'
import type { AccessProbeState } from './SecurityXray'
import { Icon } from './Icons'

interface DemoGuideProps {
  chapterIndex: number
  tampered: boolean
  temperatureExcursion: boolean
  probe: AccessProbeState
  onClose: () => void
  onSelectChapter: (index: number) => void
  onToggleTamper: () => void
  onToggleExcursion: () => void
  onProbe: () => void
}

export function DemoGuide({
  chapterIndex,
  tampered,
  temperatureExcursion,
  probe,
  onClose,
  onSelectChapter,
  onToggleTamper,
  onToggleExcursion,
  onProbe,
}: DemoGuideProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const actionRef = useRef<HTMLButtonElement>(null)
  const chapter = DEMO_CHAPTERS[chapterIndex]
  const finalChapter = chapterIndex === DEMO_CHAPTERS.length - 1

  useEffect(() => {
    const shell = document.querySelector<HTMLElement>('.workspace-shell')
    const previousOverflow = document.body.style.overflow
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    if (shell) shell.inert = true
    document.body.style.overflow = 'hidden'
    dialogRef.current?.focus()

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
      if (event.key !== 'Tab' || !dialogRef.current) return
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], [tabindex="0"]'))
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      if (shell) shell.inert = false
      if (previousFocus?.isConnected && previousFocus !== document.body) previousFocus.focus()
      else { const heading = shell?.querySelector<HTMLElement>('main h1'); heading?.setAttribute('tabindex', '-1'); heading?.focus({ preventScroll: true }) }
    }
  }, [onClose])

  useEffect(() => {
    const root = document.documentElement
    const selectors: Record<string, string> = {
      trace: '.trace-map-panel',
      atlas: '.atlas-map-panel',
      journey: '.chart-surface',
      integrity: '.chain-surface',
      security: '.xray-surface',
      presentation: '.presentation-intro',
    }
    root.dataset.guideTarget = chapter.target
    const target = document.querySelector<HTMLElement>(selectors[chapter.target] ?? `[data-demo-target="${chapter.target}"]`)
    let spotFrame: number | null = null
    const updateSpotlight = () => {
      if (!target) return
      const rect = target.getBoundingClientRect()
      root.style.setProperty('--spot-x', `${rect.left + rect.width / 2}px`)
      root.style.setProperty('--spot-y', `${rect.top + rect.height / 2}px`)
      root.style.setProperty('--spot-rx', `${Math.min(380, Math.max(125, rect.width / 2 + 18))}px`)
      root.style.setProperty('--spot-ry', `${Math.min(260, Math.max(90, rect.height / 2 + 18))}px`)
    }
    const scheduleSpotlightUpdate = () => {
      if (spotFrame !== null) return
      spotFrame = window.requestAnimationFrame(() => {
        spotFrame = null
        updateSpotlight()
      })
    }
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    target?.scrollIntoView({ block: 'center', inline: 'center', behavior: reduceMotion ? 'auto' : 'smooth' })
    scheduleSpotlightUpdate()
    const observer = target ? new ResizeObserver(scheduleSpotlightUpdate) : null
    if (target && observer) observer.observe(target)
    window.addEventListener('resize', scheduleSpotlightUpdate)
    window.addEventListener('scroll', scheduleSpotlightUpdate, { passive: true })
    return () => {
      if (spotFrame !== null) window.cancelAnimationFrame(spotFrame)
      observer?.disconnect()
      window.removeEventListener('resize', scheduleSpotlightUpdate)
      window.removeEventListener('scroll', scheduleSpotlightUpdate)
      delete root.dataset.guideTarget
      root.style.removeProperty('--spot-x')
      root.style.removeProperty('--spot-y')
      root.style.removeProperty('--spot-rx')
      root.style.removeProperty('--spot-ry')
    }
  }, [chapter.target])

  return (
    <div className="guide-layer">
      <div className="guide-backdrop" aria-hidden="true" />
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="guide-title" aria-describedby="guide-description" className="guide-dialog" tabIndex={-1}>
        <div className="guide-dialog-top"><div><span className="micro-label">GUIDED DEMO / LOCAL PRESENTATION</span><span className="guide-chapter-count">CHAPTER 0{chapterIndex + 1} / 04</span></div><button type="button" className="icon-button" aria-label="Thoát chế độ dẫn chuyện" onClick={onClose}><Icon name="close" size={18} /></button></div>
        <div className="guide-progress" aria-label={`Chương ${chapterIndex + 1} trên 4`}>{DEMO_CHAPTERS.map((item, index) => <button key={item.title} type="button" aria-label={`Mở chương ${index + 1}: ${item.title}`} aria-current={chapterIndex === index ? 'step' : undefined} className={chapterIndex === index ? 'guide-progress-current' : chapterIndex > index ? 'guide-progress-done' : ''} onClick={() => onSelectChapter(index)}><span />0{index + 1}</button>)}</div>
        <div className="guide-copy" aria-live="polite"><span className="guide-illustration"><Icon name={chapterIndex === 0 ? 'trace' : chapterIndex === 1 ? 'thermometer' : chapterIndex === 2 ? 'integrity' : 'security'} size={26} /></span><p className="eyebrow">{['TRACE / ORIGIN', 'COLD CHAIN / TELEMETRY', 'INTEGRITY / SHA-256', 'SECURITY / RBAC + RLS'][chapterIndex]}</p><h2 id="guide-title">{chapter.title}</h2><p id="guide-description">{chapter.description}</p></div>
        {chapterIndex === 1 && <div className="guide-action-note"><Icon name="thermometer" size={16} /><span>{temperatureExcursion ? 'Ngoại lệ nhiệt fixture đang bật; hash vẫn được niêm phong hợp lệ.' : 'Nhiệt độ gần giới hạn được gắn cảnh báo riêng với lỗi toàn vẹn.'}</span><button type="button" className="text-action" onClick={onToggleExcursion}>{temperatureExcursion ? 'Khôi phục' : 'Tạo ngoại lệ'}</button></div>}
        {chapterIndex === 2 && <div className={`guide-action-note ${tampered ? 'guide-action-note-danger' : ''}`}><Icon name="shield" size={16} /><span>{tampered ? 'Đã băm lại fixture và làm đứt liên kết downstream.' : 'Phép sửa chỉ chạy trong trình duyệt; không ghi vào backend.'}</span><button ref={actionRef} type="button" className={tampered ? 'text-action' : 'button button-danger'} onClick={onToggleTamper}>{tampered ? 'Khôi phục fixture' : 'Mô phỏng sửa event #03'}</button></div>}
        {finalChapter && <div className="guide-action-note"><Icon name="shield" size={16} /><span>{probe.status === 'idle' ? 'Gửi một GET thực để xem tầng RBAC và RLS.' : probe.status === 'allowed' ? `200 OK · ${probe.visibleRows} bản ghi API trả về; sơ đồ RLS là mô hình kiến trúc.` : probe.status === 'blocked' ? '403 Forbidden · request dừng ở RBAC.' : probe.status === 'pending' ? 'Đang đợi response từ backend…' : `${probe.httpStatus ?? 'Network'} · ${probe.message}`}</span><button ref={actionRef} type="button" className="button button-primary" onClick={onProbe} disabled={probe.status === 'pending'}>{probe.status === 'pending' ? 'Đang kiểm tra…' : 'Gửi GET thực'}</button></div>}
        <div className="guide-footer"><button type="button" className="button button-quiet" onClick={onClose}>Thoát bất cứ lúc nào</button><div><button type="button" className="button button-quiet" disabled={chapterIndex === 0} onClick={() => onSelectChapter(chapterIndex - 1)}>Trước</button><button type="button" className="button button-primary" onClick={() => finalChapter ? onClose() : onSelectChapter(chapterIndex + 1)}>{finalChapter ? 'Hoàn tất' : 'Tiếp theo'} <Icon name="arrow" size={15} /></button></div></div>
      </div>
    </div>
  )
}
