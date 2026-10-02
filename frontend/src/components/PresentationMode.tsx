import { DEMO_CHAPTERS } from '../domain/demoScenario'
import { Icon } from './Icons'

interface PresentationModeProps {
  onStart: (chapter: number) => void
}

export function PresentationMode({ onStart }: PresentationModeProps) {
  return (
    <section className="presentation-view" data-demo-target="presentation" aria-labelledby="presentation-title">
      <div className="presentation-masthead"><span className="micro-label">AGROCHAIN / FIELD PRESENTATION</span><span className="presentation-no">FIELD GUIDE&nbsp;&nbsp;·&nbsp;&nbsp;04 CHAPTERS</span></div>
      <div className="presentation-intro"><span className="presentation-kicker">A product can tell its own story.</span><h1 id="presentation-title">Trace a harvest.<br /><em>Keep the evidence.</em></h1><p>Hành trình, cảm biến, dấu mật mã và quyền truy cập — được giải thích qua bốn chương ngắn, có thể thoát bất cứ lúc nào.</p><button type="button" className="button button-primary button-large" onClick={() => onStart(0)}><Icon name="play" size={17} />Bắt đầu dẫn chuyện <Icon name="arrow" size={16} /></button></div>
      <div className="presentation-route" aria-hidden="true"><svg viewBox="0 0 820 180"><path d="M50 118C171 12 247 164 367 78s158 68 269 9 101-23 143-52" className="presentation-route-line" /><circle cx="50" cy="118" r="8" /><circle cx="367" cy="78" r="8" /><circle cx="636" cy="87" r="8" /><circle cx="779" cy="35" r="8" /></svg><div><span>FIELD</span><span>THERMAL</span><span>SEAL</span><span>ACCESS</span></div></div>
      <div className="chapter-grid">
        {DEMO_CHAPTERS.map((chapter, index) => <article className="chapter-card" key={chapter.title}><span className="chapter-no">0{index + 1}</span><div><p className="micro-label">{['TRACE / ORIGIN', 'COLD CHAIN / TELEMETRY', 'INTEGRITY / SHA-256', 'SECURITY / RBAC + RLS'][index]}</p><h2>{chapter.title}</h2><p>{chapter.description}</p></div><button type="button" className="chapter-open" aria-label={`Bắt đầu chương ${index + 1}: ${chapter.title}`} onClick={() => onStart(index)}><Icon name="arrow" size={18} /></button></article>)}
      </div>
      <p className="presentation-footnote"><Icon name="shield" size={15} />Chương 1–3 dùng fixture cục bộ. Chương 4 chỉ gửi request GET /api/v1/farms/; không tạo hay sửa dữ liệu.</p>
    </section>
  )
}
