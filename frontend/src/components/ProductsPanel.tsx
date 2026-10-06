import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { ApiError, createProduct, getProducts, updateProduct } from '../services/api'
import type { Product, ProductUnit } from '../types'

const PRODUCT_UNITS: ProductUnit[] = ['kg', 'tấn', 'thùng']

interface ProductsPanelProps {
  canManage: boolean
}

export function ProductsPanel({ canManage }: ProductsPanelProps) {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const [search, setSearch] = useState('')
  const [name, setName] = useState('')
  const [unit, setUnit] = useState<ProductUnit>('kg')
  const [editing, setEditing] = useState<Product | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

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

  const visibleProducts = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('vi')
    return query ? products.filter((product) => product.name.toLocaleLowerCase('vi').includes(query)) : products
  }, [products, search])

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

  const startCreate = () => {
    setEditing(null)
    setName('')
    setUnit('kg')
    setError(null)
    setNotice(null)
    setFormOpen(true)
  }

  const startEdit = (product: Product) => {
    setEditing(product)
    setName(product.name)
    setUnit(product.unit)
    setError(null)
    setNotice(null)
    setFormOpen(true)
  }

  const closeForm = () => {
    setFormOpen(false)
    setEditing(null)
    setError(null)
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (savingRef.current) return
    savingRef.current = true
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const payload = { name: name.trim(), unit }
      const saved = editing
        ? await updateProduct(editing.id, payload)
        : await createProduct(payload)
      setProducts((current) => {
        const next = editing
          ? current.map((product) => product.id === saved.id ? saved : product)
          : [...current, saved]
        return next.sort((a, b) => a.name.localeCompare(b.name, 'vi'))
      })
      setNotice(editing ? 'Đã cập nhật sản phẩm.' : 'Đã thêm sản phẩm.')
      setFormOpen(false)
      setEditing(null)
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? 'Tên sản phẩm này đã được sử dụng.'
          : err instanceof Error ? err.message : 'Không thể lưu sản phẩm.',
      )
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  return (
    <div className="info-stack">
      <section className="data-table-wrapper panel-card" aria-labelledby="products-title">
        <div className="data-table-header">
          <div>
            <h2 id="products-title" className="section-title">Danh mục sản phẩm</h2>
            <p className="panel-sub">Tên và đơn vị tính dùng chung cho các lô hàng.</p>
          </div>
          <div className="action-row">
            <button type="button" className="ds-button ds-button-secondary" onClick={() => void refresh()} disabled={loading}>Làm mới</button>
            {canManage && (
              <button type="button" className="ds-button ds-button-brand" aria-expanded={formOpen} onClick={formOpen ? closeForm : startCreate}>
                {formOpen ? 'Đóng' : 'Thêm sản phẩm'}
              </button>
            )}
          </div>
        </div>

        {formOpen && canManage && (
          <form className="product-form product-form-editor" onSubmit={(event) => void submit(event)}>
            <div className="form-field">
              <label htmlFor="product-name">Tên sản phẩm</label>
              <input id="product-name" value={name} onChange={(event) => setName(event.target.value)} maxLength={200} required placeholder="Ví dụ: Xoài cát Hòa Lộc" />
            </div>
            <div className="form-field">
              <label htmlFor="product-unit">Đơn vị tính</label>
              <select id="product-unit" value={unit} onChange={(event) => setUnit(event.target.value as ProductUnit)}>
                {PRODUCT_UNITS.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </div>
            <div className="action-row">
              <button className="ds-button ds-button-brand" type="submit" disabled={saving}>{saving ? 'Đang lưu…' : editing ? 'Lưu thay đổi' : 'Thêm sản phẩm'}</button>
              <button className="ds-button ds-button-secondary" type="button" onClick={closeForm} disabled={saving}>Hủy</button>
            </div>
          </form>
        )}

        {error && <p className="alert-box alert-error table-alert" role="alert">{error}</p>}
        {notice && <p className="alert-box alert-success table-alert" role="status">{notice}</p>}

        <div className="product-list-filter form-field">
          <label htmlFor="product-search">Tìm sản phẩm</label>
          <input id="product-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nhập tên sản phẩm" />
        </div>

        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th scope="col">Sản phẩm</th><th scope="col">Đơn vị tính</th>{canManage && <th scope="col">Thao tác</th>}</tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={canManage ? 3 : 2} className="cell-center" aria-busy="true">Đang tải danh mục…</td></tr>
              ) : visibleProducts.length === 0 ? (
                <tr><td colSpan={canManage ? 3 : 2} className="cell-center">Không tìm thấy sản phẩm.</td></tr>
              ) : visibleProducts.map((product) => (
                <tr key={product.id}>
                  <th scope="row" className="cell-strong">{product.name}</th>
                  <td>{product.unit}</td>
                  {canManage && <td><button type="button" className="ds-button ds-button-secondary ds-button-sm" onClick={() => startEdit(product)}>Sửa</button></td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
