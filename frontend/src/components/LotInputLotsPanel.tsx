import { useCallback, useEffect, useState } from 'react'
import { createLotInputLots, getLotInputLots, getProducts } from '../services/api'
import type { LotInputLot, Product } from '../types'

interface LotInputLotsPanelProps {
  lotId: string
  canDeclare: boolean
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function LotInputLotsPanel({ lotId, canDeclare }: LotInputLotsPanelProps) {
  const [items, setItems] = useState<LotInputLot[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [usedOn, setUsedOn] = useState(today())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [declared, catalogue] = await Promise.all([
        getLotInputLots(lotId),
        getProducts(),
      ])
      setItems(declared)
      setProducts(catalogue)
      setProductId((current) => current || catalogue[0]?.id || '')
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải danh sách vật tư.',
      )
    } finally {
      setLoading(false)
    }
  }, [lotId])

  useEffect(() => {
    let active = true
    const timer = window.setTimeout(() => {
      void load().finally(() => {
        if (!active) return
      })
    }, 150)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [load])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!productId || !quantity || saving) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      await createLotInputLots(lotId, [
        { product_id: productId, quantity, used_on: usedOn },
      ])
      setQuantity('')
      setNotice('Đã ghi nhận vật tư vào hồ sơ lô.')
      await load()
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể ghi nhận vật tư.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="panel-card panel-box" aria-label="Vật tư đã dùng cho lô">
      <header className="panel-head">
        <div>
          <h2>Vật tư đã dùng cho lô</h2>
          <p className="panel-sub">
            Khai phân bón và thuốc bảo vệ thực vật đã dùng cho lô này. Mỗi lần
            khai được ghi thành một sự kiện trong chuỗi của lô.
          </p>
        </div>
      </header>

      {error && (
        <div className="alert-box alert-error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert-box alert-success" role="status">
          {notice}
        </div>
      )}

      {loading && items.length === 0 && <p role="status">Đang tải danh sách vật tư…</p>}
      {!loading && items.length === 0 && (
        <p>Chưa có vật tư nào được khai cho lô này.</p>
      )}

      {items.length > 0 && (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Vật tư</th>
                <th scope="col">Liều lượng</th>
                <th scope="col">Ngày dùng</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.product_name}</td>
                  <td>{item.quantity}</td>
                  <td>{item.used_on}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {canDeclare && (
        <form onSubmit={submit} className="integrity-check-controls">
          <div className="form-field">
            <label htmlFor="input-lot-product">Vật tư</label>
            <select
              id="input-lot-product"
              value={productId}
              onChange={(event) => setProductId(event.target.value)}
              disabled={products.length === 0}
            >
              {products.length === 0 && <option value="">Danh mục trống</option>}
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="input-lot-quantity">Liều lượng</label>
            <input
              id="input-lot-quantity"
              type="text"
              inputMode="decimal"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              placeholder="Ví dụ 12.5"
            />
          </div>
          <div className="form-field">
            <label htmlFor="input-lot-used-on">Ngày dùng</label>
            <input
              id="input-lot-used-on"
              type="date"
              value={usedOn}
              onChange={(event) => setUsedOn(event.target.value)}
            />
          </div>
          <button
            type="submit"
            className="ds-button ds-button-brand"
            disabled={saving || !productId || !quantity}
          >
            {saving ? 'Đang ghi…' : 'Ghi nhận'}
          </button>
        </form>
      )}
    </section>
  )
}
