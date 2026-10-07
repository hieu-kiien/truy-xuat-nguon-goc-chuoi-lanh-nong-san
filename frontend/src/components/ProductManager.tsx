import { useEffect, useState, type FormEvent } from 'react'
import { hasPermission, type SessionUser } from '../types'
import {
  productService,
  type Product,
  type ProductInput,
  type ProductUnit,
} from '../services/productService'

const PRODUCT_UNITS: { value: ProductUnit; label: string }[] = [
  { value: 'kg', label: 'Kilôgam (kg)' },
  { value: 'tấn', label: 'Tấn' },
  { value: 'thùng', label: 'Thùng' },
]

interface ProductManagerProps {
  user: SessionUser
}

export function ProductManager({ user }: ProductManagerProps) {
  const canWriteProducts = hasPermission(user.role, 'products:write')
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [name, setName] = useState('')
  const [unit, setUnit] = useState<ProductUnit>('kg')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('0')
  const [quantity, setQuantity] = useState('0')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  useEffect(() => {
    let active = true
    productService
      .getProducts()
      .then((data) => {
        if (active) setProducts(data)
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(
            error instanceof Error
              ? error.message
              : 'Không thể tải danh mục sản phẩm'
          )
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const resetForm = () => {
    setEditingProduct(null)
    setName('')
    setUnit('kg')
    setDescription('')
    setPrice('0')
    setQuantity('0')
  }

  const startCreate = () => {
    resetForm()
    setFeedback(null)
    setFormOpen(true)
  }

  const startEdit = (product: Product) => {
    setEditingProduct(product)
    setName(product.name)
    setUnit(product.unit)
    setDescription(product.description ?? '')
    setPrice(String(product.price))
    setQuantity(String(product.quantity ?? 0))
    setFeedback(null)
    setFormOpen(true)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (saving) return

    setSaving(true)
    setFeedback(null)
    const payload: ProductInput = {
      name: name.trim(),
      unit,
      description: description.trim() || undefined,
      price: Number(price),
      quantity: quantity.trim() ? Number(quantity) : 0,
    }

    try {
      const saved = editingProduct
        ? await productService.updateProduct(editingProduct.id, payload)
        : await productService.createProduct(payload)
      setProducts((current) => {
        const next = editingProduct
          ? current.map((product) =>
              product.id === saved.id ? saved : product
            )
          : [...current, saved]
        return next.sort((left, right) => left.name.localeCompare(right.name))
      })
      setFeedback({
        type: 'success',
        message: editingProduct
          ? `Đã cập nhật sản phẩm "${saved.name}".`
          : `Đã thêm sản phẩm "${saved.name}" vào danh mục dùng chung.`,
      })
      resetForm()
      setFormOpen(false)
    } catch (error) {
      setFeedback({
        type: 'error',
        message:
          error instanceof Error ? error.message : 'Không thể lưu sản phẩm',
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="info-stack">
      {canWriteProducts && formOpen && (
        <section
          className="panel-box panel-card"
          aria-labelledby="product-form-title"
        >
          <div className="panel-head">
            <h2 id="product-form-title">
              {editingProduct ? 'Sửa sản phẩm' : 'Thêm sản phẩm'}
            </h2>
          </div>
          <form onSubmit={handleSubmit} className="form-stack">
            <div className="form-row-2">
              <div className="form-field">
                <label htmlFor="product-name">
                  Tên sản phẩm <span className="required-mark">*</span>
                </label>
                <input
                  id="product-name"
                  type="text"
                  required
                  maxLength={200}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="VD: Xoài cát Hòa Lộc"
                />
              </div>
              <div className="form-field">
                <label htmlFor="product-unit">
                  Đơn vị tính <span className="required-mark">*</span>
                </label>
                <select
                  id="product-unit"
                  required
                  value={unit}
                  onChange={(event) => setUnit(event.target.value as ProductUnit)}
                >
                  {PRODUCT_UNITS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-field">
              <label htmlFor="product-description">Mô tả</label>
              <input
                id="product-description"
                type="text"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Mô tả ngắn (không bắt buộc)"
              />
            </div>

            <div className="form-row-2">
              <div className="form-field">
                <label htmlFor="product-price">Giá mặc định</label>
                <input
                  id="product-price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={price}
                  onChange={(event) => setPrice(event.target.value)}
                />
              </div>
              <div className="form-field">
                <label htmlFor="product-quantity">Số lượng mặc định</label>
                <input
                  id="product-quantity"
                  type="number"
                  min="0"
                  step="1"
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                />
              </div>
            </div>

            <div className="action-row">
              <button
                type="submit"
                className="ds-button ds-button-brand ds-button-sm"
                disabled={saving}
              >
                {saving
                  ? 'Đang lưu...'
                  : editingProduct
                    ? 'Lưu cập nhật'
                    : 'Thêm vào danh mục'}
              </button>
              <button
                type="button"
                className="ds-button ds-button-secondary ds-button-sm"
                onClick={() => {
                  setFormOpen(false)
                  resetForm()
                  setFeedback(null)
                }}
              >
                Hủy
              </button>
            </div>
          </form>
        </section>
      )}

      <section
        className="data-table-wrapper panel-card"
        aria-labelledby="products-table-title"
      >
        <div className="data-table-header">
          <div>
            <h2 id="products-table-title" className="section-title">
              Danh mục sản phẩm dùng chung ({products.length})
            </h2>
            <p className="panel-sub">
              Mọi tổ chức cùng sử dụng tên và đơn vị tính chuẩn.
            </p>
          </div>
          {canWriteProducts && (
            <button
              type="button"
              className="ds-button ds-button-brand ds-button-sm"
              onClick={startCreate}
            >
              Thêm sản phẩm
            </button>
          )}
        </div>

        {feedback && (
          <div
            className={`alert-box ${feedback.type === 'success' ? 'alert-success' : 'alert-error'} table-alert`}
            role="status"
            aria-live="polite"
          >
            {feedback.message}
          </div>
        )}
        {loadError && (
          <div className="alert-box alert-error table-alert" role="alert">
            {loadError}
          </div>
        )}

        <div className="table-scroll">
          <table className="data-table product-table">
            <thead>
              <tr>
                <th scope="col">Tên sản phẩm</th>
                <th scope="col">Đơn vị</th>
                <th scope="col">Mô tả</th>
                <th scope="col">Giá</th>
                <th scope="col">Số lượng</th>
                {canWriteProducts && <th scope="col">Thao tác</th>}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={canWriteProducts ? 6 : 5}>
                    Đang tải danh mục...
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={canWriteProducts ? 6 : 5}>
                    Chưa có sản phẩm trong danh mục.
                  </td>
                </tr>
              ) : (
                products.map((product) => (
                  <tr key={product.id}>
                    <th scope="row" className="cell-strong">
                      {product.name}
                    </th>
                    <td>{product.unit}</td>
                    <td>{product.description || '—'}</td>
                    <td>{product.price.toFixed(2)}</td>
                    <td>{product.quantity ?? 0}</td>
                    {canWriteProducts && (
                      <td>
                        <button
                          type="button"
                          className="ds-button ds-button-secondary ds-button-xs"
                          aria-label={`Sửa ${product.name}`}
                          onClick={() => startEdit(product)}
                        >
                          Sửa
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}