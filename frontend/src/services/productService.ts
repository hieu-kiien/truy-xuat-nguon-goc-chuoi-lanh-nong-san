import { request } from './api'

export type ProductUnit = 'kg' | 'tấn' | 'thùng'

export interface Product {
  id: string
  name: string
  description: string | null
  price: number
  quantity: number | null
  unit: ProductUnit
}

export interface ProductInput {
  name: string
  unit: ProductUnit
  description?: string
  price?: number
  quantity?: number
}

export const productService = {
  getProducts: () => request<Product[]>('/api/v1/products/'),

  createProduct: (data: ProductInput) =>
    request<Product>('/api/v1/products/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateProduct: (id: string, data: Partial<ProductInput>) =>
    request<Product>(`/api/v1/products/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteProduct: (id: string) =>
    request<void>(`/api/v1/products/${id}`, {
      method: 'DELETE',
    }),
}