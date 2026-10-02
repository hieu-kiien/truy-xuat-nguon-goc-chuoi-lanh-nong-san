import { useEffect, useState } from 'react'
import { sha256, type DemoHashBlock } from '../domain/demoScenario'
import { Icon } from './Icons'
import { HashCompare } from './HashCompare'

interface IntegrityLabProps {
  chain: DemoHashBlock[]
  chainError: string | null
  tampered: boolean
  temperatureExcursion: boolean
  selectedStage: number
  onSelectStage: (index: number) => void
  onToggleTamper: () => void
}

const compactHash = (hash: string) => `${hash.slice(0, 10)}…${hash.slice(-8)}`

function temperatureToken(payload: DemoHashBlock['payload']): string {
  return String(payload.temp_c)
}

export function IntegrityLab({
  chain,
  chainError,
  tampered,
  temperatureExcursion,
  selectedStage,
  onSelectStage,
  onToggleTamper,
}: IntegrityLabProps) {
  const [verificationStep, setVerificationStep] = useState(0)
  const [replaying, setReplaying] = useState(false)
  const [verificationError, setVerificationError] = useState<string | null>(null)
  const selected = chain[selectedStage]
  const overallValid = chain.length > 0 && chain.every((block) => block.hashMatches && block.ancestryValid)

  useEffect(() => {
    if (!replaying) return
    if (!chain.length || verificationStep >= chain.length) return
    let cancelled = false
    const delay = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 520
    const timer = window.setTimeout(() => {
      void sha256(chain[verificationStep].canonicalPayload).then((hash) => {
        if (cancelled) return
        if (hash !== chain[verificationStep].computedHash) throw new Error('Digest tính lại không khớp kết quả hiện tại.')
        if (verificationStep + 1 >= chain.length) setReplaying(false)
        setVerificationStep(verificationStep + 1)
        onSelectStage(verificationStep)
      }).catch((error: unknown) => {
        if (cancelled) return
        setVerificationError(error instanceof Error ? error.message : 'Không thể xác minh digest.')
        setReplaying(false)
      })
    }, delay)
    return () => { cancelled = true; window.clearTimeout(timer) }
  }, [replaying, verificationStep, chain, onSelectStage])

  const advanceVerification = () => {
    setReplaying(false)
    const nextStep = verificationStep >= chain.length ? 1 : verificationStep + 1
    setVerificationStep(nextStep)
    onSelectStage(Math.max(0, nextStep - 1))
  }

  const resetVerification = () => {
    setReplaying(false)
    setVerificationError(null)
    setVerificationStep(0)
    onSelectStage(0)
  }

  return (
    <section className={`view-stack forensic-view ${tampered ? 'forensic-tampered' : ''}`} data-demo-target="integrity" aria-labelledby="integrity-title">
      <div className="view-heading view-heading-spread">
        <div><p className="eyebrow">Mission 03 / Integrity forensics</p><h1 id="integrity-title">Mỗi event, một dấu niêm phong.</h1><p className="view-intro">Payload chuẩn hóa được băm thật bằng SHA-256 trong trình duyệt; chuỗi dưới đây là fixture cục bộ.</p></div>
        <div className="integrity-actions">
          <span className={`integrity-overview ${!chain.length ? 'integrity-overview-pending' : overallValid ? 'integrity-overview-valid' : 'integrity-overview-invalid'}`}><Icon name={overallValid ? 'check' : 'shield'} size={16} />{chain.length ? overallValid ? '4 / 4 liên kết hợp lệ' : 'Chuỗi có sai lệch' : 'Đang tính SHA-256'}</span>
          <button type="button" className={`button ${tampered ? 'button-danger-active' : 'button-quiet'}`} onClick={onToggleTamper} disabled={Boolean(chainError)}>{tampered ? 'Khôi phục fixture gốc' : 'Mô phỏng sửa trường temp_c'}</button>
        </div>
      </div>

      {(chainError || verificationError) && <div className="notice notice-error" role="alert"><strong>Không thể tính digest trong trình duyệt.</strong><span>{chainError || verificationError}</span></div>}
      {temperatureExcursion && !tampered && <div className="integrity-separation"><Icon name="thermometer" size={17} /><p><strong>Ngoại lệ nhiệt độ đang được mô phỏng độc lập.</strong><span>Fixture 9.9°C được niêm phong bằng digest mới; đây không phải lỗi toàn vẹn.</span></p><span className="state-pill state-excursion">Sensor event</span></div>}
      {tampered && <div className="notice notice-error forensic-alert" role="status"><strong>Payload nguồn đã đổi tại event #03.</strong><span>Digest thật khác dấu đã niêm phong; block sau mất liên kết tổ tiên. Chỉ dữ liệu cục bộ trong trình duyệt được đổi.</span></div>}

      <section className="surface chain-surface" aria-labelledby="chain-heading">
        <div className="section-heading"><div><span className="micro-label">HASH CHAIN / LOCAL FIXTURE</span><h2 id="chain-heading">Chuỗi event có thể kiểm chứng</h2></div><span className="chain-method">canonical payload <b>→</b> previous hash <b>→</b> SHA-256 <b>→</b> event seal</span></div>

        {chain.length > 0 && <div className="chain-rail" role="group" aria-label="Chọn block hash để xem bằng chứng">
          <svg className="chain-connectors" viewBox="0 0 1000 74" preserveAspectRatio="none" aria-hidden="true">
            {chain.slice(0, -1).map((block, index) => {
              const next = chain[index + 1]
              const start = 125 + index * 250
              const end = start + 250
              const isBroken = next.previousHash !== block.computedHash
              const verified = verificationStep >= index + 2
              const gap = (start + end) / 2
              const path = isBroken
                ? `M${start} 36H${gap - 13} M${gap + 13} 36H${end}`
                : `M${start} 36H${end}`
              return <g key={block.stage.id}>
                <path d={path} className={isBroken ? 'chain-link-fractured' : 'chain-link-line'} />
                {!isBroken && verified && <path d={path} pathLength="250" className="chain-link-beam chain-link-beam-verified" />}
                {isBroken && <path d={`M${gap - 7} 26l6 10-6 10 13-10-5-8 11 8`} className="chain-fracture-mark" />}
              </g>
            })}
          </svg>
          {chain.map((block, index) => {
            const status = !block.hashMatches ? 'mismatch' : block.ancestryValid ? 'valid' : 'broken'
            return (
              <button key={block.stage.id} type="button" className={`chain-block chain-block-${status} ${selectedStage === index ? 'chain-block-selected' : ''} ${verificationStep === index + 1 ? 'chain-block-checking' : ''}`} aria-pressed={selectedStage === index} onClick={() => { setReplaying(false); onSelectStage(index); setVerificationStep(index + 1) }}>
                <span className="chain-block-index">BLOCK / 0{index + 1}</span>
                <span className="chain-block-seal"><Icon name={status === 'valid' ? 'check' : status === 'mismatch' ? 'close' : 'layers'} size={18} /></span>
                <strong>{block.stage.title}</strong>
                <code title={block.recordedHash}>{compactHash(block.recordedHash)}</code>
                <span className={`chain-status chain-status-${status}`}>{status === 'valid' ? 'Digest + ancestry OK' : status === 'mismatch' ? 'Digest mismatch' : 'Ancestry broken'}</span>
              </button>
            )
          })}
        </div>}

        <div className="verification-controls">
          <div className="verification-progress"><span className="micro-label">REPLAY / STEP {Math.min(verificationStep, chain.length)} OF {chain.length}</span><div className="verification-progress-track"><span style={{ width: `${chain.length ? (Math.min(verificationStep, chain.length) / chain.length) * 100 : 0}%` }} /></div></div>
          <p>{verificationStep === 0 ? 'Chạy lại để kiểm tra lần lượt từng dấu event.' : verificationStep >= chain.length ? overallValid ? 'Đã xác minh hết chuỗi; các digest và liên kết đều khớp.' : `Đã xác minh đến block ${verificationStep}; phát hiện sai lệch hoặc mất tổ tiên.` : `Đang đối chiếu block ${verificationStep} với event seal đã ghi.`}</p>
          <div className="verification-buttons"><button type="button" className="button button-quiet" onClick={resetVerification}>Chạy lại từ đầu</button><button type="button" className="button button-quiet" disabled={!chain.length} onClick={() => { setVerificationError(null); if (!replaying) setVerificationStep(0); setReplaying(!replaying) }}>{replaying ? 'Dừng xác minh' : 'Phát toàn bộ xác minh'}</button><button type="button" className="button button-primary" onClick={advanceVerification} disabled={!chain.length}>{verificationStep >= chain.length ? 'Phát lại' : 'Kiểm tra bước kế'} <Icon name="arrow" size={15} /></button></div>
        </div>
      </section>

      {selected && <div className="forensic-grid">
        <section className="surface payload-panel" aria-labelledby="payload-heading">
          <div className="section-heading"><div><span className="micro-label">EVENT / 0{selected.index + 1}</span><h2 id="payload-heading">Payload canonical</h2></div><span className="format-tag">JSON · UTF-8 · key-sorted</span></div>
          <p className="forensic-explainer">Các khóa và giá trị fixture được tuần tự hóa nhất quán trước khi băm. Event seal tính bằng Web Crypto API trong phiên trình duyệt này.</p>
          <h3 className="event-inspection-anchor">{selected.stage.title} / event 0{selected.index + 1}</h3>
          <ol className="payload-pipeline" aria-label="Cách tính event seal"><li><b>01</b><span>Payload canonical + prev_hash</span></li><li><b>02</b><span>UTF-8 · {new TextEncoder().encode(selected.canonicalPayload).length} byte</span></li><li><b>03</b><span>SHA-256 → 256 bit → event seal</span></li></ol>
          <pre className="payload-code"><code>{JSON.stringify(selected.payload, null, 2)}</code></pre>
          <details className="canonical-details"><summary>Xem đúng chuỗi canonical được băm</summary><code>{selected.canonicalPayload}</code></details>
          <HashCompare recorded={selected.recordedHash} computed={selected.computedHash} />
          {tampered && selected.index === 2 && <div className="json-diff" aria-label="So sánh trường trước và sau khi sửa"><div className="diff-row diff-before"><span>− source trước</span><code>"temp_c": {temperatureToken({ ...selected.payload, temp_c: selected.sourceTemperature })}</code></div><div className="diff-row diff-after"><span>+ source sau</span><code>"temp_c": {temperatureToken(selected.payload)}</code></div></div>}
          <div className="hash-calculation"><div><span>previous hash</span><code title={selected.previousHash}>{compactHash(selected.previousHash)}</code></div><div className="hash-arrow"><Icon name="arrow" size={17} /><span>SHA-256</span><Icon name="arrow" size={17} /></div><div><span>computed digest</span><code title={selected.computedHash}>{compactHash(selected.computedHash)}</code></div><div className="hash-outcome"><span>recorded event seal</span><code title={selected.recordedHash}>{compactHash(selected.recordedHash)}</code><strong className={selected.hashMatches ? 'ink-positive' : 'ink-danger'}>{selected.hashMatches ? 'DIGEST KHỚP' : 'DIGEST KHÔNG KHỚP'}</strong></div></div>
        </section>

        <aside className="surface ancestry-panel" aria-labelledby="ancestry-heading">
          <div className="section-heading"><div><span className="micro-label">LINK AUDIT</span><h2 id="ancestry-heading">Liên kết trước / sau</h2></div><Icon name="layers" size={19} /></div>
          <ol className="ancestry-list">
            {chain.map((block, index) => {
              const localState = block.hashMatches ? 'ok' : 'mismatch'
              const linkState = block.ancestryValid ? 'ok' : 'broken'
              return <li key={block.stage.id} className={`ancestry-row ancestry-${block.ancestryValid ? 'valid' : !block.hashMatches ? 'fracture' : 'downstream'}`}><span className="ancestry-number">0{index + 1}</span><div className="ancestry-content"><strong>{block.stage.title}</strong><code title={block.previousHash}>prev {compactHash(block.previousHash)}</code><span className={`ancestry-seal ancestry-seal-${localState}`}>Seal {block.hashMatches ? 'match' : 'mismatch'}</span></div><span className={`ancestry-link-state ancestry-link-${linkState}`}>{block.ancestryValid ? 'LINKED' : !block.hashMatches ? 'FRACTURED' : 'NO ANCESTOR'}</span></li>
            })}
          </ol>
          <div className="ancestry-note"><Icon name="shield" size={16} /><p><strong>Digest và nhiệt độ là hai câu hỏi khác nhau.</strong><span>Một phép đo ngoài dải vẫn có thể được niêm phong hợp lệ. Sửa payload sau khi đã niêm phong làm digest và nguồn gốc downstream sai lệch.</span></p></div>
        </aside>
      </div>}
    </section>
  )
}
