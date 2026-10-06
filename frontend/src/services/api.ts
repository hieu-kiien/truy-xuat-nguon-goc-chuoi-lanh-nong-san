import type {
  CreateEventRequest,
  Farm,
  FarmPayload,
  HealthResponse,
  LoginRequest,
  LotListParams,
  Lot,
  LotPage,
  LotPayload,
  LotEvent,
  Product,
  ProductPayload,
  SessionUser,
  IntegrityReport,
  EventHistory,
  Handover,
  HandoverPayload,
  OrganizationOption,
} from '../types'


function resolveBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL
  if (envUrl) {
    return envUrl.replace(/\/$/, '')
  }
  if (
    typeof window !== 'undefined' &&
    window.location.hostname.endsWith('.onrender.com')
  ) {
    return 'https://ttcs-backend-staging.onrender.com'
  }
  return 'http://localhost:8000'
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

async function parseApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as {
      detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>
    }
    if (typeof body.detail === 'string') {
      return new ApiError(response.status, body.detail)
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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })


  if (!response.ok) {
    if (
      response.status === 401 &&
      path !== '/api/v1/auth/login' &&
      path !== '/api/v1/auth/me' &&
      typeof window !== 'undefined' &&
      window.location.pathname !== '/login'
    ) {
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

  return response.json() as Promise<T>
}

export const checkHealth = () => request<HealthResponse>('/')

export const login = (payload: LoginRequest) =>
  request<SessionUser>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const getCurrentUser = () => request<SessionUser>('/api/v1/auth/me')

export const logout = async (): Promise<void> => {
  await request<void>('/api/v1/auth/logout', { method: 'POST' })
}

export const getFarms = () => request<Farm[]>('/api/v1/farms/')

export const getLots = (params: LotListParams = {}) => {
  const query = new URLSearchParams()
  if (params.q?.trim()) query.set('q', params.q.trim())
  if (params.product_id) query.set('product_id', params.product_id)
  if (params.cursor) query.set('cursor', params.cursor)
  query.set('page_size', String(params.page_size ?? 20))
  return request<LotPage>(`/api/v1/lots/?${query.toString()}`)
}

export const getProducts = () => request<Product[]>('/api/v1/products/')

export const createProduct = (payload: ProductPayload) =>
  request<Product>('/api/v1/products/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const updateProduct = (productId: string, payload: ProductPayload) =>
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

export const getFarm = (farmId: string) =>
  request<Farm>(`/api/v1/farms/${farmId}`)

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

export const getEvents = (lotId?: string) => {
  const query = lotId ? `?lot_id=${encodeURIComponent(lotId)}` : ''
  return request<LotEvent[]>(`/api/v1/events/${query}`)
}

export const verifyLotIntegrity = (lotId: string) =>
  request<IntegrityReport>(`/api/v1/events/lots/${lotId}/integrity`)

export const getLotHistory = (lotId: string) =>
  request<EventHistory>(`/api/v1/events/lots/${lotId}/history`)

export const getEvent = (eventId: string) =>
  request<LotEvent>(`/api/v1/events/${eventId}`)

export const createEvent = (payload: CreateEventRequest) =>
  request<LotEvent>('/api/v1/events/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

// ARCHITECTURAL GUARANTEE (N3-21):
// There are NO updateEvent or deleteEvent functions.
// Events are strictly append-only.

