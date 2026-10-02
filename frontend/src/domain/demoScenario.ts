export interface JourneyStage {
  id: string
  label: string
  title: string
  location: string
  timestamp: string
  latitude: number
  longitude: number
  temperature: number
  humidity: number
  stageCode: string
}

export const JOURNEY_STAGES: JourneyStage[] = [
  {
    id: 'harvest',
    label: '01',
    title: 'Thu hoạch',
    location: 'Cầu Đất · Lâm Đồng',
    timestamp: '2026-09-30T06:00:00Z',
    latitude: 11.92485,
    longitude: 108.49721,
    temperature: 14.2,
    humidity: 78,
    stageCode: 'harvest',
  },
  {
    id: 'pre-cooling',
    label: '02',
    title: 'Sơ chế & làm lạnh',
    location: 'Trạm sơ chế · Đà Lạt',
    timestamp: '2026-09-30T08:15:00Z',
    latitude: 11.9423,
    longitude: 108.438,
    temperature: 7.6,
    humidity: 85,
    stageCode: 'pre_cooling',
  },
  {
    id: 'transport',
    label: '03',
    title: 'Vận chuyển lạnh',
    location: 'Quốc lộ 20 · Lâm Đồng',
    timestamp: '2026-09-30T10:30:00Z',
    latitude: 11.9291,
    longitude: 108.507,
    temperature: 3.5,
    humidity: 82,
    stageCode: 'transport',
  },
  {
    id: 'warehouse',
    label: '04',
    title: 'Nhập kho',
    location: 'Trung tâm phân phối · TP.HCM',
    timestamp: '2026-09-30T14:00:00Z',
    latitude: 10.8231,
    longitude: 106.6297,
    temperature: 4,
    humidity: 80,
    stageCode: 'warehouse',
  },
]

export interface DemoHashBlock {
  index: number
  stage: JourneyStage
  sourceTemperature: number
  payload: Record<string, string | number>
  canonicalPayload: string
  originalCanonicalPayload: string
  previousHash: string
  recordedHash: string
  computedHash: string
  hashMatches: boolean
  ancestryValid: boolean
}

function canonicalize(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value)
  }

  if (Array.isArray(value)) {
    return `[${value.map(canonicalize).join(',')}]`
  }

  const entries = Object.entries(value as Record<string, unknown>).sort(
    ([left], [right]) => (left < right ? -1 : left > right ? 1 : 0)
  )
  return `{${entries
    .map(([key, item]) => `${JSON.stringify(key)}:${canonicalize(item)}`)
    .join(',')}}`
}

export async function sha256(value: string): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error('Web Crypto không khả dụng trong ngữ cảnh hiện tại.')
  }

  const digest = await globalThis.crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(value)
  )
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0')
  ).join('')
}

export async function calculateDemoHashChain(options: {
  tampered: boolean
  temperatureExcursion: boolean
}): Promise<DemoHashBlock[]> {
  const sealedPayloads: Array<{
    stage: JourneyStage
    sourceTemperature: number
    payload: Record<string, string | number>
    canonicalPayload: string
    previousHash: string
    recordedHash: string
  }> = []
  let previousHash = '0'.repeat(64)

  for (const [index, stage] of JOURNEY_STAGES.entries()) {
    const sourceTemperature =
      options.temperatureExcursion && index === 2 ? 9.9 : stage.temperature
    const payload = {
      event_seq: index + 1,
      humidity_pct: stage.humidity,
      lot_id: 'lot-caudat-demo-01',
      prev_hash: previousHash,
      stage: stage.stageCode,
      temp_c: sourceTemperature,
      timestamp: stage.timestamp,
    }
    const canonicalPayload = canonicalize(payload)
    const recordedHash = await sha256(canonicalPayload)
    sealedPayloads.push({
      stage,
      sourceTemperature,
      payload,
      canonicalPayload,
      previousHash,
      recordedHash,
    })
    previousHash = recordedHash
  }

  const blocks: DemoHashBlock[] = []
  for (const [index, sealed] of sealedPayloads.entries()) {
    const payload =
      options.tampered && index === 2
        ? { ...sealed.payload, temp_c: 99.9 }
        : sealed.payload
    const canonicalPayload = canonicalize(payload)
    const computedHash = await sha256(canonicalPayload)
    const hashMatches = computedHash === sealed.recordedHash
    const ancestryValid =
      index === 0
        ? sealed.previousHash === '0'.repeat(64) && hashMatches
        : sealed.previousHash === blocks[index - 1].computedHash &&
          blocks[index - 1].ancestryValid &&
          hashMatches

    blocks.push({
      index,
      stage: sealed.stage,
      sourceTemperature: sealed.sourceTemperature,
      payload,
      canonicalPayload,
      originalCanonicalPayload: sealed.canonicalPayload,
      previousHash: sealed.previousHash,
      recordedHash: sealed.recordedHash,
      computedHash,
      hashMatches,
      ancestryValid,
    })
  }

  return blocks
}

export const DEMO_CHAPTERS = [
  {
    title: 'Truy dấu nông sản',
    description:
      'Theo một lô minh họa từ vùng thu hoạch qua sơ chế, vận chuyển lạnh đến kho.',
    tab: 'overview',
    target: 'trace',
  },
  {
    title: 'Đọc hành trình lạnh',
    description:
      'Chọn mốc thời gian để đối chiếu nhiệt độ, độ ẩm và vị trí trong kịch bản.',
    tab: 'journey',
    target: 'journey',
  },
  {
    title: 'Mô phỏng kiểm tra toàn vẹn',
    description:
      'Sửa một trường trong fixture cục bộ, tính SHA-256 thật và xem liên kết sau đó mất tổ tiên.',
    tab: 'integrity',
    target: 'integrity',
  },
  {
    title: 'Theo dõi RBAC và RLS',
    description:
      'Gửi GET /api/v1/farms/ để xem request thực được cho phép hoặc dừng tại lớp RBAC.',
    tab: 'security',
    target: 'security',
  },
] as const
