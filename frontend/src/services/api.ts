/**
 * services/api.ts
 * Lớp trung gian gọi API backend; phiên đăng nhập dùng cookie HttpOnly.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  signalUnauthorized = true,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    if (response.status === 401 && signalUnauthorized) {
      window.dispatchEvent(new Event('auth:expired'))
    }
    let message = response.statusText
    let detail: unknown
    try {
      const body = (await response.json()) as { detail?: unknown }
      detail = body.detail
      if (typeof body.detail === 'string') message = body.detail
      else if (body.detail) message = 'Dữ liệu gửi lên chưa hợp lệ.'
    } catch {
      // Keep the HTTP status text when the response has no JSON body.
    }
    throw new ApiError(response.status, `API ${response.status}: ${message}`, detail)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export interface SessionUser {
  id: string
  email: string
  full_name: string
  organization_id: string
  organization_name: string
  organization_type: string
  role: string
}

export const login = (credentials: { email: string; password: string }) =>
  request<SessionUser>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  }, false)

export const getSessionUser = () =>
  request<SessionUser>('/api/v1/auth/me', {}, false)

export const logout = () =>
  request<void>('/api/v1/auth/logout', { method: 'POST' })

export interface Farm {
  id: string
  organization_id: string
  name: string
  area_ha: string | number
  latitude: string | number
  longitude: string | number
}

export type FarmInput = Omit<Farm, 'id' | 'organization_id'>

export const getFarms = () => request<Farm[]>('/api/v1/farms/')
export const createFarm = (farm: FarmInput) =>
  request<Farm>('/api/v1/farms/', { method: 'POST', body: JSON.stringify(farm) })
export const updateFarm = (id: string, farm: FarmInput) =>
  request<Farm>(`/api/v1/farms/${id}`, { method: 'PUT', body: JSON.stringify(farm) })

// ─── Health ──────────────────────────────────────────────────────────────────
export const checkHealth = () => request<{ status: string; message: string }>('/')

// ─── Items (ví dụ minh họa — xóa khi có domain thật) ────────────────────────
export interface Item {
  id: number
  name: string
}

export const getItems = () => request<Item[]>('/api/v1/items/')
export const getItem = (id: number) => request<Item>(`/api/v1/items/${id}`)
