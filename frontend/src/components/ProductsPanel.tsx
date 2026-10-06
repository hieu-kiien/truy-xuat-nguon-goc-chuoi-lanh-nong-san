import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, createProduct, getProducts } from '../services/api'
import type { Product, ProductUnit } from '../types'

const PRODUCT_UNITS: ProductUnit[] = ['kg', 'tấn', 'thùng']

interface ProductsPanelProps {
  canCreate: boolean
}

export function ProductsPanel({ canCreate }: ProductsPanelProps) {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const [name, setName] = useState('')
  const [unit, setUnit] = useState<ProductUnit>('kg')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      setProducts(await getProducts())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải danh mục sản phẩm.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    getProducts()
      .then((data) => { if (active) setProducts(data) })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải danh mục sản phẩm.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (savingRef.current) return

    savingRef.current = true
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const product = await createProduct({ name: name.trim(), unit })
      setProducts((current) => [...current, product].sort((a, b) => a.name.localeCompare(b.name, 'vi')))
      setName('')
      setNotice(`Đã thêm ${product.name} vào danh mục dùng chung.`)
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? 'Tên sản phẩm này đã có trong danh mục.'
          : err instanceof Error
            ? err.message
            : 'Không thể thêm sản phẩm.',
      )
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  return (
    <div className="info-stack">
      {canCreate && (
        <section className="panel-box panel-card" aria-labelledby="product-form-title">
          <div className="panel-head">
            <h2 id="product-form-title">Thêm sản phẩm dùng chung</h2>
            <span className="panel-sub">Quản trị hệ thống</span>
          </div>
          <form className="product-form" onSubmit={(event) => void handleSubmit(event)}>
            <div className="form-field">
              <label htmlFor="product-name">Tên sản phẩm</label>
              <input
                id="product-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                maxLength={200}
                required
                placeholder="Ví dụ: Xoài cát Hòa Lộc"
              />
            </div>
            <div className="form-field">
              <label htmlFor="product-unit">Đơn vị tính</label>
              <select id="product-unit" value={unit} onChange={(event) => setUnit(event.target.value as ProductUnit)}>
                {PRODUCT_UNITS.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </div>
            <button className="ds-button ds-button-brand ds-button-sm" type="submit" disabled={saving}>
              {saving ? 'Đang lưu...' : 'Thêm sản phẩm'}
            </button>
          </form>
          {error && <p className="alert-box alert-error" role="alert">{error}</p>}
          {notice && <p className="alert-box alert-success" role="status">{notice}</p>}
        </section>
      )}

      <section className="data-table-wrapper panel-card" aria-labelledby="products-title">
        <div className="data-table-header">
          <div>
            <h2 id="products-title" className="section-title">Danh mục sản phẩm ({products.length})</h2>
            <p className="panel-sub">Tên và đơn vị được dùng thống nhất giữa các tổ chức.</p>
          </div>
          <button type="button" className="ds-button ds-button-secondary ds-button-sm" onClick={() => void refresh()} disabled={loading}>
            {loading ? 'Đang tải...' : 'Làm mới'}
          </button>
        </div>
        {error && !canCreate && <p className="alert-box alert-error" role="alert">{error}</p>}
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th scope="col">Sản phẩm</th><th scope="col">Đơn vị tính</th></tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={2} className="cell-center" aria-busy="true">Đang tải danh mục...</td></tr>
              ) : products.length === 0 ? (
                <tr><td colSpan={2} className="cell-center">Danh mục chưa có sản phẩm.</td></tr>
              ) : products.map((product) => (
                <tr key={product.id}><th scope="row" className="cell-strong">{product.name}</th><td>{product.unit}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
