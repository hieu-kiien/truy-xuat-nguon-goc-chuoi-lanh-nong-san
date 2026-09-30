import type {
  Farm,
  FarmPayload,
  HealthResponse,
  LoginRequest,
  SessionUser,
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

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as {
      detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>
    }
    if (typeof body.detail === 'string') {
      return body.detail
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail
        .map((item) => item.msg || 'Dữ liệu không hợp lệ')
        .join('; ')
    }
  } catch {
    // Fallback to status text below
  }
  return `Lỗi HTTP ${response.status}: ${response.statusText || 'Yêu cầu thất bại'}`
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
    const message = await parseErrorMessage(response)
    throw new ApiError(response.status, message)
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

export const logout = () =>
  request<void>('/api/v1/auth/logout', { method: 'POST' })

export const getFarms = () => request<Farm[]>('/api/v1/farms/')

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
