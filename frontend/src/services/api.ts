/**
 * services/api.ts
 * Lớp trung gian gọi API backend; phiên đăng nhập dùng cookie HttpOnly.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
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
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // Keep the HTTP status text when the response has no JSON body.
    }
    throw new ApiError(response.status, `API ${response.status}: ${message}`)
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

// ─── Health ──────────────────────────────────────────────────────────────────
export const checkHealth = () => request<{ status: string; message: string }>('/')

// ─── Items (ví dụ minh họa — xóa khi có domain thật) ────────────────────────
export interface Item {
  id: number
  name: string
}

export const getItems = () => request<Item[]>('/api/v1/items/')
export const getItem = (id: number) => request<Item>(`/api/v1/items/${id}`)
