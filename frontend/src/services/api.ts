import type {
  CreateEventRequest,
  Farm,
  FarmPayload,
  HealthResponse,
  LoginRequest,
  LotListParams,
  Lot,
  LotDetail,
  Lineage,
  LotPage,
  LotPayload,
  LotEvent,
  Product,
  ProductPayload,
  SessionUser,
  IntegrityCheckRecord,
  IntegrityScanSummary,
  EventHistory,
  Handover,
  HandoverPayload,
  OrganizationOption,
  DistributionLocation,
  RecallReport,
  RecallOrder,
  RecallNotification,
  PublicTraceResponse,
  ColdChainViolationStats,
  LotInputLot,
  LotInputLotPayload,
  NotificationList,
  NotificationItem,
  PublicRoute,
  ProcessingStep,
  ProcessingStepRecord,
  Shipment,
  ShipmentHourlyAggregate,
  ShipmentTemperatureReading,
  OrganizationProfile,
  OrganizationInvitation,
  OrganizationInvitationCreated,
  OrganizationMember,
  ShipmentColdChainLimits,
  ProductColdChainConfig,
  ShipmentViolation,
  TelemetryIngestResult,
} from '../types'


function resolveBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL
  if (envUrl) {
    return envUrl.replace(/\/$/, '')
  }
  if (import.meta.env.DEV) {
    return ''
  }
  return 'https://ttcs-backend-staging.onrender.com'
}

export const API_BASE_URL = resolveBaseUrl()

export class ApiError extends Error {
  status: number
  fieldErrors: Record<string, string>

  constructor(
    status: number,
    message: string,
    fieldErrors: Record<string, string> = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}


const SESSION_STORAGE_KEY = 'agrochain_session_token'

export function getStoredSessionToken(): string | null {
  try {
    return sessionStorage.getItem(SESSION_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setStoredSessionToken(token: string | null): void {
  try {
    if (token) {
      sessionStorage.setItem(SESSION_STORAGE_KEY, token)
    } else {
      sessionStorage.removeItem(SESSION_STORAGE_KEY)
    }
  } catch {
    // Ignore storage errors in restricted contexts
  }
}

async function parseApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as {
      detail?: string | { message?: string } | Array<{ msg?: string; loc?: Array<string | number> }>
    }
    if (typeof body.detail === 'string') {
      return new ApiError(response.status, body.detail)
    }
    if (body.detail && typeof body.detail === 'object' && !Array.isArray(body.detail) && typeof body.detail.message === 'string') {
      return new ApiError(response.status, body.detail.message)
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const fieldErrors: Record<string, string> = {}
      for (const item of body.detail) {
        const field = item.loc?.find(
          (part) => typeof part === 'string' && part !== 'body',
        )
        if (field) fieldErrors[String(field)] = item.msg || 'Dữ liệu không hợp lệ'
      }
      const message = body.detail
        .map((item) => item.msg || 'Dữ liệu không hợp lệ')
        .join('; ')
      return new ApiError(response.status, message, fieldErrors)
    }
  } catch {
    // Fallback to status text below
  }
  return new ApiError(
    response.status,
    `Lỗi HTTP ${response.status}: ${response.statusText || 'Yêu cầu thất bại'}`,
  )
}

export const getPublicRoute = (code: string): Promise<PublicRoute> => {
  const normalized = code.trim().toUpperCase()
  return request<PublicRoute>(
    `/api/v1/public/trace/${encodeURIComponent(normalized)}/route`
  )
}

export const getProcessingStepCatalogue = () =>
  request<ProcessingStep[]>('/api/v1/processing-steps/')

export const getLotProcessingSteps = (lotId: string) =>
  request<ProcessingStepRecord[]>(`/api/v1/lots/${lotId}/processing-steps`)

export const recordLotProcessingStep = (
  lotId: string,
  payload: { processing_step_id: string; parameters: Record<string, unknown> },
) =>
  request<ProcessingStepRecord>(`/api/v1/lots/${lotId}/processing-steps`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export async function getPublicTrace(code: string): Promise<PublicTraceResponse> {
  const normalized = code.trim().toUpperCase()
  return request<PublicTraceResponse>(
    `/api/v1/public/trace/${encodeURIComponent(normalized)}`
  )
}

function buildHeaders(options: RequestInit = {}): Headers {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  headers.set('X-Client-Type', 'web-spa')

  const storedToken = getStoredSessionToken()
  if (storedToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${storedToken}`)
  }
  return headers
}

export async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = buildHeaders(options)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      credentials: 'include',
    })
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw err
    }
    const isOffline = typeof navigator !== 'undefined' && !navigator.onLine
    const msg = isOffline
      ? 'Mất kết nối Internet. Vui lòng kiểm tra lại kết nối mạng của bạn.'
      : 'Không thể kết nối đến máy chủ API. Vui lòng thử lại sau vài giây (máy chủ có thể đang khởi động).'
    throw new ApiError(0, msg)
  }

  const authHeader = response.headers.get('Authorization')
  if (authHeader && authHeader.startsWith('Bearer ')) {
    setStoredSessionToken(authHeader.substring(7).trim())
  }

  if (!response.ok) {
    if (
      response.status === 401 &&
      path !== '/api/v1/auth/login' &&
      path !== '/api/v1/auth/me' &&
      typeof window !== 'undefined' &&
      window.location.pathname !== '/login'
    ) {
      setStoredSessionToken(null)
      const protectedPaths = new Set([
        '/lots',
        '/handovers',
        '/products',
        '/farms',
        '/security',
        '/integrity',
      ])
      const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`
      const returnPath = protectedPaths.has(window.location.pathname)
        ? currentPath
        : '/lots'
      window.location.replace(
        `/login?next=${encodeURIComponent(returnPath)}`
      )
    }
    throw await parseApiError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError(
      response.status,
      'Dữ liệu phản hồi từ máy chủ không hợp lệ.'
    )
  }
}

export const checkHealth = () =>
  request<HealthResponse>('/health')

export const login = (payload: LoginRequest) =>
  request<SessionUser>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const getCurrentUser = () => request<SessionUser>('/api/v1/auth/me')

export const logout = async (): Promise<void> => {
  try {
    await request<void>('/api/v1/auth/logout', { method: 'POST' })
  } finally {
    setStoredSessionToken(null)
  }
}

export const getFarms = () => request<Farm[]>('/api/v1/farms/')

function normalizeLotPage(response: unknown): LotPage {
  if (Array.isArray(response)) {
    // Older staging API versions return the first page as a bare list.
    return { items: response as Lot[], next_cursor: null }
  }

  if (response && typeof response === 'object') {
    const page = response as Partial<LotPage>
    if (Array.isArray(page.items)) {
      return {
        items: page.items,
        next_cursor: typeof page.next_cursor === 'string' ? page.next_cursor : null,
      }
    }
  }

  throw new ApiError(
    502,
    'Máy chủ trả về danh sách lô không đúng định dạng. Vui lòng tải lại sau khi đồng bộ API.',
  )
}

export const getLots = async (params: LotListParams = {}): Promise<LotPage> => {
  const query = new URLSearchParams()
  if (params.q?.trim()) query.set('q', params.q.trim())
  if (params.product_id) query.set('product_id', params.product_id)
  if (params.farm_id) query.set('farm_id', params.farm_id)
  if (params.harvested_from) query.set('harvested_from', params.harvested_from)
  if (params.harvested_to) query.set('harvested_to', params.harvested_to)
  if (params.cursor) query.set('cursor', params.cursor)
  query.set('page_size', String(params.page_size ?? 20))
  const response = await request<unknown>(`/api/v1/lots/?${query.toString()}`)
  return normalizeLotPage(response)
}

export const getLot = (lotId: string) =>
  request<LotDetail>(`/api/v1/lots/${lotId}`)

export const getLineage = (lotId: string, direction: 'ancestors' | 'descendants') =>
  request<Lineage>(`/api/v1/lots/${lotId}/lineage?direction=${direction}`)

export const getLotRecall = (lotId: string) =>
  request<RecallReport>(`/api/v1/lots/${lotId}/recall`)

export const getRecalls = (statusFilter?: 'open' | 'completed') =>
  request<RecallOrder[]>(`/api/v1/recalls/${statusFilter ? `?status_filter=${statusFilter}` : ''}`)

export const getRecallOrder = (recallId: string) =>
  request<RecallOrder>(`/api/v1/recalls/${recallId}`)

export const getRecallNotifications = (includeCompleted = false) =>
  request<RecallNotification[]>(`/api/v1/recalls/notifications?include_completed=${String(includeCompleted)}`)

export const openRecallOrder = (lotId: string, reason: string) =>
  request<RecallOrder>('/api/v1/recalls/', {
    method: 'POST',
    body: JSON.stringify({ lot_id: lotId, reason }),
  })

export const confirmRecallHandling = (recallId: string, note: string) =>
  request<RecallOrder>(`/api/v1/recalls/${recallId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  })

export const splitLot = (lotId: string, children: Array<{name: string; quantity: string; location_id?: string | null}>) =>
  request<{parent: Lot; children: Lot[]}>(`/api/v1/lots/${lotId}/split`, {
    method: 'POST', body: JSON.stringify({children}),
  })

export const getLocations = () => request<DistributionLocation[]>('/api/v1/locations/')

export const createLocation = (name: string, address: string) =>
  request<DistributionLocation>('/api/v1/locations/', {method: 'POST', body: JSON.stringify({name, address})})

export const moveLot = (id: string, location_id: string) =>
  request<Lot>(`/api/v1/lots/${id}/move`, {method: 'POST', body: JSON.stringify({location_id})})

export const consumeLot = (id: string, note?: string) =>
  request<Lot>(`/api/v1/lots/${id}/consume`, {method: 'POST', body: JSON.stringify({note})})

export const mergeLots = (name: string, parents: Array<{lot_id: string; quantity: string}>) =>
  request<Lot>('/api/v1/lots/merge', {
    method: 'POST', body: JSON.stringify({name, parents}),
  })

export const getProducts = () => request<Product[]>('/api/v1/products/')

export const createProduct = (payload: ProductPayload) =>
  request<Product>('/api/v1/products/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const updateProduct = (productId: string, payload: Partial<ProductPayload>) =>
  request<Product>(`/api/v1/products/${productId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })

export const getHandoverOrganizations = () =>
  request<OrganizationOption[]>('/api/v1/handovers/organizations')

export const getIncomingHandovers = () =>
  request<Handover[]>('/api/v1/handovers/incoming')

export const getOutgoingHandovers = () =>
  request<Handover[]>('/api/v1/handovers/outgoing')

export const createHandover = (payload: HandoverPayload) =>
  request<Handover>('/api/v1/handovers/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const acceptHandover = (handoverId: string) =>
  request<{ id: string; status: 'accepted' }>(`/api/v1/handovers/${handoverId}/accept`, { method: 'POST' })

export const rejectHandover = (handoverId: string, reason: string) =>
  request<{ id: string; status: 'rejected' }>(`/api/v1/handovers/${handoverId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })

export const createLot = (payload: LotPayload) =>
  request<Lot>('/api/v1/lots/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const createFarm = (payload: FarmPayload) =>
  request<Farm>('/api/v1/farms/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const updateFarm = (farmId: string, payload: FarmPayload) =>
  request<Farm>(`/api/v1/farms/${farmId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })

export const verifyLotIntegrity = (lotId: string) =>
  request<IntegrityCheckRecord>(`/api/v1/events/lots/${lotId}/integrity-checks`, {
    method: 'POST',
  })

export const getIntegrityCheckHistory = (lotId: string) =>
  request<IntegrityCheckRecord[]>(`/api/v1/events/lots/${lotId}/integrity-checks`)

export const getIntegrityScanSummary = () =>
  request<IntegrityScanSummary>('/api/v1/events/integrity/summary')

export const getLotInputLots = (lotId: string) =>
  request<LotInputLot[]>(`/api/v1/lots/${lotId}/input-lots`)

export const createLotInputLots = (
  lotId: string,
  items: LotInputLotPayload[],
) =>
  request<LotInputLot[]>(`/api/v1/lots/${lotId}/input-lots`, {
    method: 'POST',
    body: JSON.stringify({ items }),
  })

export const getColdChainViolationStats = (
  params: { from?: string; to?: string } = {},
): Promise<ColdChainViolationStats> => {
  const query = new URLSearchParams()
  if (params.from) query.set('from', params.from)
  if (params.to) query.set('to', params.to)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request<ColdChainViolationStats>(
    `/api/v1/telemetry/violations/stats${suffix}`,
  )
}

export const getNotifications = () =>
  request<NotificationList>('/api/v1/notifications')
export const markNotificationRead = (notificationId: string) =>
  request<NotificationItem>(
    `/api/v1/notifications/${notificationId}/read`,
    { method: 'POST' },
  )

export const markAllNotificationsRead = () =>
  request<{ updated: number }>('/api/v1/notifications/read-all', {
    method: 'POST',
  })

export const getLotHistory = (lotId: string, after = 0) =>
  request<EventHistory>(`/api/v1/events/lots/${lotId}/history?page_size=10&after=${after}`)

export const createEvent = (payload: CreateEventRequest) =>
  request<LotEvent>('/api/v1/events/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

/**
 * Tải hồ sơ truy xuất PDF của lô kèm kết quả kiểm toàn vẹn (N3-72).
 * Endpoint trả tệp nhị phân nên không dùng `request<T>` (hàm này parse JSON).
 */
export async function downloadLotReport(lotId: string): Promise<Blob> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/lots/${lotId}/report.pdf`, {
      headers: buildHeaders(),
      credentials: 'include',
    })
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw err
    }
    throw new ApiError(
      0,
      'Không thể kết nối đến máy chủ API. Vui lòng thử lại sau vài giây.',
    )
  }

  if (response.status === 401 && typeof window !== 'undefined') {
    setStoredSessionToken(null)
    window.location.replace(`/login?next=${encodeURIComponent('/lots')}`)
  }
  if (!response.ok) {
    throw await parseApiError(response)
  }
  return response.blob()
}

// ARCHITECTURAL GUARANTEE (N3-21):
// There are NO updateEvent or deleteEvent functions.
// Events are strictly append-only.

export const getShipments = () => request<Shipment[]>('/api/v1/shipments')

export const getShipmentReadings = (
  shipmentId: string,
  params: { from?: string; to?: string } = {},
) => {
  const query = new URLSearchParams()
  if (params.from) query.set('from', params.from)
  if (params.to) query.set('to', params.to)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request<ShipmentTemperatureReading[]>(
    `/api/v1/telemetry/shipments/${shipmentId}/readings${suffix}`,
  )
}

export const getShipmentColdChainLimits = (shipmentId: string) =>
  request<ShipmentColdChainLimits>(
    `/api/v1/telemetry/shipments/${shipmentId}/cold-chain-limits`,
  )

export const getShipmentViolations = (shipmentId: string) =>
  request<ShipmentViolation[]>(
    `/api/v1/telemetry/shipments/${shipmentId}/violations`,
  )

export const createShipment = (payload: {
  container_code: string
  lot_ids: string[]
  notes?: string | null
  shipment_code?: string | null
}) =>
  request<Shipment>('/api/v1/shipments', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const ingestTelemetryReadings = (payload: {
  container_code: string
  readings: { recorded_at: string; temperature_celsius: string }[]
}) =>
  request<TelemetryIngestResult>('/api/v1/telemetry/readings', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const getShipmentHourlyAggregates = (shipmentId: string) =>
  request<ShipmentHourlyAggregate[]>(
    `/api/v1/telemetry/shipments/${shipmentId}/readings/hourly`,
  )

export const getMyOrganization = () =>
  request<OrganizationProfile>('/api/v1/organizations/me')

export const updateContactEmail = (contactEmail: string) =>
  request<OrganizationProfile>('/api/v1/organizations/me/contact-email', {
    method: 'PUT',
    body: JSON.stringify({ contact_email: contactEmail }),
  })

export const getOrganizationInvitations = () =>
  request<OrganizationInvitation[]>('/api/v1/organizations/invitations')

export const createOrganizationInvitation = (payload: {
  email: string
  role_code: string
}) =>
  request<OrganizationInvitationCreated>('/api/v1/organizations/invitations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const revokeOrganizationInvitation = (invitationId: string) =>
  request<OrganizationInvitation>(
    `/api/v1/organizations/invitations/${invitationId}/revoke`,
    { method: 'POST' },
  )

export const getOrganizationMembers = () =>
  request<OrganizationMember[]>('/api/v1/organizations/members')

export const deactivateOrganizationMember = (userId: string) =>
  request<OrganizationMember>(
    `/api/v1/organizations/members/${userId}/deactivate`,
    { method: 'POST' },
  )

export const getProductColdChainConfig = (productId: string) =>
  request<ProductColdChainConfig>(
    `/api/v1/products/${productId}/cold-chain-config`,
  )

export const updateProductColdChainConfig = (
  productId: string,
  payload: { min_temp_celsius: string; max_temp_celsius: string; delay_minutes: number },
) =>
  request<ProductColdChainConfig>(
    `/api/v1/products/${productId}/cold-chain-config`,
    { method: 'PUT', body: JSON.stringify(payload) },
  )
