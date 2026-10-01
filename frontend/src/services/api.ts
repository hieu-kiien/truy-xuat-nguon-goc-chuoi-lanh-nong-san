import type {
  DemoLoginRequest,
  Farm,
  FarmPayload,
  HealthResponse,
  LoginRequest,
  SessionUser,
} from '../types'

const SESSION_STORAGE_KEY = 'ttcs_session_token'

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
export const DEMO_LOGIN_ENABLED = import.meta.env.VITE_ENABLE_DEMO_LOGIN === 'true'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function getStoredToken(): string | null {
  try {
    return sessionStorage.getItem(SESSION_STORAGE_KEY)
  } catch {
    return null
  }
}

function setStoredToken(token: string | null): void {
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

  const token = getStoredToken()
  if (token) {
    headers.set('X-Session-Token', token)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  const sessionHeader = response.headers.get('X-Session-Token')
  if (sessionHeader) {
    setStoredToken(sessionHeader)
  }

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

export const demoLogin = (payload: DemoLoginRequest) =>
  request<SessionUser>('/api/v1/auth/demo-login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const getCurrentUser = () => request<SessionUser>('/api/v1/auth/me')

export const logout = async (): Promise<void> => {
  try {
    await request<void>('/api/v1/auth/logout', { method: 'POST' })
  } finally {
    setStoredToken(null)
  }
}

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
