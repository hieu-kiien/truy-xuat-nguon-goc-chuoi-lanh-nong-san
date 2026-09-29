/**
 * services/api.ts
 * Lớp trung gian gọi API backend.
 * Mọi fetch/axios đều đi qua đây — không gọi trực tiếp trong component.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

// ─── Health ──────────────────────────────────────────────────────────────────
export const checkHealth = () => request<{ status: string; message: string }>('/')

// ─── Items (ví dụ minh họa — xóa khi có domain thật) ────────────────────────
export interface Item {
  id: number
  name: string
}

export const getItems = () => request<Item[]>('/api/v1/items/')
export const getItem = (id: number) => request<Item>(`/api/v1/items/${id}`)
