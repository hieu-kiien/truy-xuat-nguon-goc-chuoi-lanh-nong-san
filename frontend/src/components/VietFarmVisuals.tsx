import { useState } from 'react'

export type SquircleAssetKey =
  | 'bokchoy'
  | 'carrot'
  | 'rice'
  | 'strawberry'
  | 'seedling'
  | 'basket'
  | 'truck'
  | 'frost'

const ASSET_MAP: Record<SquircleAssetKey, { src: string; bg: string; border: string; accent: string; label: string }> = {
  bokchoy: {
    src: '/assets/vietfarm/bokchoy3d.png',
    bg: '#EDF3EB',
    border: '#D5E4D0',
    accent: '#2F6F3E',
    label: 'Rau hữu cơ',
  },
  carrot: {
    src: '/assets/vietfarm/carrot3d.png',
    bg: '#FBECE6',
    border: '#F2D0C2',
    accent: '#C85A32',
    label: 'Củ quả tươi',
  },
  rice: {
    src: '/assets/vietfarm/rice3d.png',
    bg: '#FAF5E8',
    border: '#EADBC0',
    accent: '#B7791F',
    label: 'Lúa gạo & Ngũ cốc',
  },
  strawberry: {
    src: '/assets/vietfarm/strawberry.png',
    bg: '#FCEEEB',
    border: '#F3CEC7',
    accent: '#C53030',
    label: 'Trái cây tươi',
  },
  seedling: {
    src: '/assets/vietfarm/seedling.png',
    bg: '#EDF3EB',
    border: '#D5E4D0',
    accent: '#2F6F3E',
    label: 'Vùng trồng VietGAP',
  },
  basket: {
    src: '/assets/vietfarm/basket3d.png',
    bg: '#FDF3E7',
    border: '#EED6B8',
    accent: '#B76E22',
    label: 'Giỏ thu hoạch',
  },
  truck: {
    src: '/assets/vietfarm/truck3d.png',
    bg: '#E3F5EE',
    border: '#BFE6D7',
    accent: '#1F7A5C',
    label: 'Vận chuyển lạnh',
  },
  frost: {
    src: '/assets/vietfarm/frost3d.png',
    bg: '#E3F5EE',
    border: '#BFE6D7',
    accent: '#1F7A5C',
    label: 'Bảo quản kho lạnh',
  },
}

function FallbackVectorGlyph({ kind, color }: { kind: SquircleAssetKey; color: string }) {
  switch (kind) {
    case 'truck':
      return (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="1" y="3" width="15" height="13" rx="2" />
          <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
          <circle cx="5.5" cy="18.5" r="2.5" />
          <circle cx="18.5" cy="18.5" r="2.5" />
        </svg>
      )
    case 'frost':
      return (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="2" x2="12" y2="22" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
          <line x1="19.07" y1="4.93" x2="4.93" y2="19.07" />
        </svg>
      )
    case 'basket':
      return (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m5 11 4-7" />
          <path d="m19 11-4-7" />
          <path d="M2 11h20" />
          <path d="m3.5 11 1.6 7.4a2 2 0 0 0 2 1.6h9.8c.9 0 1.8-.7 2-1.6l1.7-7.4" />
        </svg>
      )
    default:
      return (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
        </svg>
      )
  }
}

function resolveProduceKey(text?: string | null): SquircleAssetKey {
  if (!text) return 'bokchoy'
  const lower = text.toLowerCase()
  if (lower.includes('cà rốt') || lower.includes('khoai') || lower.includes('củ') || lower.includes('hành') || lower.includes('tỏi')) {
    return 'carrot'
  }
  if (lower.includes('gạo') || lower.includes('lúa') || lower.includes('ngô') || lower.includes('đậu') || lower.includes('hạt')) {
    return 'rice'
  }
  if (
    lower.includes('dâu') ||
    lower.includes('xoài') ||
    lower.includes('cam') ||
    lower.includes('táo') ||
    lower.includes('nho') ||
    lower.includes('sầu riêng') ||
    lower.includes('trái') ||
    lower.includes('quả') ||
    lower.includes('cà chua')
  ) {
    return 'strawberry'
  }
  if (lower.includes('bắp cải') || lower.includes('cải') || lower.includes('rau') || lower.includes('xà lách') || lower.includes('chè')) {
    return 'bokchoy'
  }
  if (lower.includes('lạnh') || lower.includes('đông') || lower.includes('sữa') || lower.includes('thịt') || lower.includes('cá')) {
    return 'frost'
  }
  if (lower.includes('xe') || lower.includes('vận chuyển') || lower.includes('container')) {
    return 'truck'
  }
  if (lower.includes('gieo') || lower.includes('vùng trồng') || lower.includes('nông trại')) {
    return 'seedling'
  }
  if (lower.includes('thu hoạch') || lower.includes('lô')) {
    return 'bokchoy'
  }
  return 'bokchoy'
}

interface SquircleIconProps {
  kind?: SquircleAssetKey
  nameHint?: string | null
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function SquircleIcon({ kind, nameHint, size = 'md', className = '' }: SquircleIconProps) {
  const key = kind ?? resolveProduceKey(nameHint)
  const meta = ASSET_MAP[key]
  const [imgFailed, setImgFailed] = useState(false)
  const px = size === 'sm' ? 40 : size === 'lg' ? 60 : 48
  const radius = size === 'sm' ? 12 : size === 'lg' ? 18 : 14

  return (
    <span
      className={`vf-squircle-icon vf-squircle-${size} ${className}`.trim()}
      style={{
        width: `${px}px`,
        height: `${px}px`,
        borderRadius: `${radius}px`,
        background: meta.bg,
        border: `1px solid ${meta.border}`,
      }}
      aria-hidden="true"
    >
      {imgFailed ? (
        <FallbackVectorGlyph kind={key} color={meta.accent} />
      ) : (
        <img
          src={meta.src}
          alt=""
          onError={() => setImgFailed(true)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            borderRadius: `${radius - 2}px`,
          }}
        />
      )}
    </span>
  )
}

export function VietFarmJourneyStepper({ compact = false }: { compact?: boolean }) {
  const [failedKeys, setFailedKeys] = useState<Record<string, boolean>>({})
  const steps: Array<{ key: SquircleAssetKey; title: string; sub: string; border: string }> = [
    { key: 'seedling', title: '1. Gieo hạt', sub: 'Vùng trồng VietGAP', border: '#4B6F44' },
    { key: 'basket', title: '2. Thu hoạch', sub: 'Ghi nhận lô gốc', border: '#D9822B' },
    { key: 'truck', title: '3. Xe lạnh', sub: 'Giám sát 2–8°C', border: '#33A881' },
    { key: 'frost', title: '4. Phân phối', sub: 'Truy xuất tem QR', border: '#C85A32' },
  ]

  return (
    <div className={`vf-journey-stepper ${compact ? 'vf-journey-compact' : ''}`} aria-label="Nhật ký hành trình từ trang trại đến bàn ăn">
      <div className="vf-journey-header">
        <span className="vf-journey-kicker">NHẬT KÝ HÀNH TRÌNH TỪ TRANG TRẠI ĐẾN BÀN ĂN</span>
        <span className="vf-journey-badge">4/4 Chặng bảo vệ SHA-256</span>
      </div>
      <div className="vf-journey-grid">
        <div className="vf-journey-line" aria-hidden="true" />
        {steps.map((step) => (
          <div key={step.key} className="vf-journey-node">
            <div className="vf-journey-icon-box" style={{ borderColor: step.border }}>
              {failedKeys[step.key] ? (
                <FallbackVectorGlyph kind={step.key} color={step.border} />
              ) : (
                <img
                  src={ASSET_MAP[step.key].src}
                  alt=""
                  loading="lazy"
                  onError={() => setFailedKeys((prev) => ({ ...prev, [step.key]: true }))}
                />
              )}
            </div>
            <span className="vf-journey-title">{step.title}</span>
            {!compact && <span className="vf-journey-sub">{step.sub}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

export function ColdChainWaveMiniChart({
  thresholdLabel = '2.0–8.0°C',
  statusLabel = 'Chuẩn VietGAP',
  violationCount = 0,
  integrityLabel = '✓ Hợp lệ',
  title = 'GIÁM SÁT NGƯỠNG NHIỆT ĐỘ CHUỖI LẠNH',
}: {
  thresholdLabel?: string
  statusLabel?: string
  violationCount?: number
  integrityLabel?: string
  title?: string
}) {
  return (
    <div className="vf-cold-wave-card">
      <div className="vf-cold-wave-header">
        <span className="vf-cold-wave-title">❄ {title}</span>
        <span className="vf-cold-wave-pill">{statusLabel} ({thresholdLabel})</span>
      </div>
      <svg viewBox="0 0 360 76" className="vf-cold-wave-svg" role="img" aria-label={`Biểu đồ ngưỡng bảo quản ${thresholdLabel}`}>
        <defs>
          <linearGradient id="vfColdMintGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#33A881" stopOpacity="0.42" />
            <stop offset="100%" stopColor="#33A881" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <line x1="0" y1="18" x2="360" y2="18" stroke="#D5EAE2" strokeDasharray="4 4" strokeWidth="1" />
        <line x1="0" y1="58" x2="360" y2="58" stroke="#D5EAE2" strokeDasharray="4 4" strokeWidth="1" />
        <path
          d="M0,48 C40,42 75,24 115,30 C155,36 190,16 235,26 C280,36 315,18 360,24 L360,74 L0,74 Z"
          fill="url(#vfColdMintGrad)"
        />
        <path
          d="M0,48 C40,42 75,24 115,30 C155,36 190,16 235,26 C280,36 315,18 360,24"
          fill="none"
          stroke="#28926E"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="115" cy="30" r="4" fill="#FFFFFF" stroke="#28926E" strokeWidth="2.2" />
        <circle cx="235" cy="26" r="4" fill="#FFFFFF" stroke="#28926E" strokeWidth="2.2" />
        <circle cx="315" cy="20" r="4.5" fill="#C85A32" stroke="#FFFFFF" strokeWidth="2" />
      </svg>
      <div className="vf-cold-wave-footer">
        <span>Ngưỡng chuẩn: <strong>{thresholdLabel}</strong></span>
        <span>Vi phạm: <strong className={violationCount > 0 ? 'vf-terracotta-text' : 'vf-ok-text'}>{violationCount} sự cố</strong></span>
        <span>Chuỗi băm: <strong className="vf-ok-text">{integrityLabel}</strong></span>
      </div>
    </div>
  )
}
