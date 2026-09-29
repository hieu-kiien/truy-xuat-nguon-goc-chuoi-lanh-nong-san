/**
 * types/index.ts
 * Tập trung tất cả TypeScript interfaces & types dùng chung toàn dự án.
 * Mỗi domain nên có file riêng (ví dụ: types/user.ts, types/product.ts).
 */

// ─── API Response chung ───────────────────────────────────────────────────────
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

// ─── Thêm types của dự án vào đây ─────────────────────────────────────────────
// export interface User { ... }
// export interface Product { ... }
