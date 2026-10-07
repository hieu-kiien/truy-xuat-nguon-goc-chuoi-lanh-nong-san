import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, createLot, getFarms } from '../services/api'
import type { Farm, Lot, LotPayload, Product } from '../types'

interface LotCreateFormProps {
  products: Product[]
  loadingProducts: boolean
  onCreated: (lot: Lot) => void
}

function localToday(): string {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

export function LotCreateForm({ products, loadingProducts, onCreated }: LotCreateFormProps) {
  const [farms, setFarms] = useState<Farm[]>([])
  const [loadingFarms, setLoadingFarms] = useState(true)
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const [farmId, setFarmId] = useState('')
  const [productId, setProductId] = useState('')
  const [harvestedOn, setHarvestedOn] = useState(localToday)
  const [quantity, setQuantity] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    let active = true
    getFarms()
      .then((data) => {
        if (active) {
          setFarms(data)
          setFarmId(data[0]?.id ?? '')
        }
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải vùng trồng.')
      })
      .finally(() => { if (active) setLoadingFarms(false) })
    return () => { active = false }
  }, [])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (savingRef.current) return

    savingRef.current = true
    setSaving(true)
    setError(null)
    setFieldErrors({})
    const payload: LotPayload = {
      farm_id: farmId,
      product_id: productId,
      harvested_on: harvestedOn,
      quantity,
    }
    try {
      const lot = await createLot(payload)
      setQuantity('')
      onCreated(lot)
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setFieldErrors(err.fieldErrors)
        setError(err.fieldErrors.farm_id || err.fieldErrors.product_id || err.fieldErrors.harvested_on || err.fieldErrors.quantity ? null : err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Không thể ghi nhận lô thu hoạch.')
      }
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  return (
    <section className="panel-box panel-card" aria-labelledby="lot-form-title">
      <div className="panel-head">
        <h2 id="lot-form-title">Ghi nhận lô thu hoạch</h2>
        <span className="panel-sub">Mã lô được sinh tự động</span>
      </div>
      {loadingFarms ? <p className="panel-sub">Đang tải vùng trồng...</p> : loadingProducts ? (
        <p className="panel-sub">Đang tải danh mục sản phẩm...</p>
      ) : farms.length === 0 ? (
        <p className="alert-box alert-error" role="status">Chưa có vùng trồng. Hãy khai báo vùng trồng trước khi tạo lô.</p>
      ) : products.length === 0 ? (
        <p className="alert-box alert-error" role="status">Danh mục chưa có sản phẩm. Vui lòng liên hệ quản trị hệ thống.</p>
      ) : (
        <form className="lot-create-form" onSubmit={(event) => void submit(event)}>
          <div className="form-field">
            <label htmlFor="lot-farm">Vùng trồng</label>
            <select id="lot-farm" value={farmId} aria-invalid={Boolean(fieldErrors.farm_id)} onChange={(event) => setFarmId(event.target.value)} required>
              {farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
            </select>
            {fieldErrors.farm_id && <small className="form-field-error">{fieldErrors.farm_id}</small>}
          </div>
          <div className="form-field">
            <label htmlFor="lot-product">Sản phẩm</label>
            <select id="lot-product" value={productId} onChange={(event) => setProductId(event.target.value)} required>
              <option value="" disabled>Chọn sản phẩm</option>
              {products.map((product) => <option key={product.id} value={product.id}>{product.name} ({product.unit})</option>)}
            </select>
            {fieldErrors.product_id && <small className="form-field-error">{fieldErrors.product_id}</small>}
          </div>
          <div className="form-field">
            <label htmlFor="lot-harvested-on">Ngày thu hoạch</label>
            <input id="lot-harvested-on" type="date" value={harvestedOn} max={localToday()} aria-invalid={Boolean(fieldErrors.harvested_on)} onChange={(event) => setHarvestedOn(event.target.value)} required />
            {fieldErrors.harvested_on && <small className="form-field-error">{fieldErrors.harvested_on}</small>}
          </div>
          <div className="form-field">
            <label htmlFor="lot-quantity">Khối lượng ({products.find((item) => item.id === productId)?.unit ?? 'đơn vị'})</label>
            <input id="lot-quantity" type="number" min="0.001" step="0.001" value={quantity} aria-invalid={Boolean(fieldErrors.quantity)} onChange={(event) => setQuantity(event.target.value)} required placeholder="Ví dụ: 125.5" />
            {fieldErrors.quantity && <small className="form-field-error">{fieldErrors.quantity}</small>}
          </div>
          <button className="ds-button ds-button-brand ds-button-sm" type="submit" disabled={saving || !farmId || !productId}>
            {saving ? 'Đang ghi nhận...' : 'Tạo lô thu hoạch'}
          </button>
        </form>
      )}
      {error && <p className="alert-box alert-error alert-spaced" role="alert">{error}</p>}
    </section>
  )
}
