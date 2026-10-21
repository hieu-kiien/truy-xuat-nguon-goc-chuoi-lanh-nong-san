import { useCallback, useEffect, useState } from 'react'
import {
  getProductColdChainConfig,
  getProducts,
  updateProductColdChainConfig,
} from '../services/api'
import { ApiError } from '../services/api'
import { validateColdChainConfig } from '../utils/validation'
import type { Product, ProductColdChainConfig } from '../types'

/** Check the three thresholds before sending them to the server. */
export function ColdChainConfigPanel({
  canWrite,
}: {
  canWrite: boolean
}) {
  const [products, setProducts] = useState<Product[]>([])
  const [productId, setProductId] = useState('')
  const [config, setConfig] = useState<ProductColdChainConfig | null>(null)
  const [minTemp, setMinTemp] = useState('2')
  const [maxTemp, setMaxTemp] = useState('8')
  const [delay, setDelay] = useState('30')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const loadProducts = useCallback(async () => {
    setLoading(true)
    try {
      const list = await getProducts()
      setProducts(list)
      setProductId((current) => current || list[0]?.id || '')
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải danh mục nông sản.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadProducts()
    }, 150)
    return () => {
      window.clearTimeout(timer)
    }
  }, [loadProducts])

  const loadConfig = useCallback(async (id: string) => {
    if (!id) return
    try {
      const payload = await getProductColdChainConfig(id)
      setConfig(payload)
      setMinTemp(String(payload.min_temp_celsius))
      setMaxTemp(String(payload.max_temp_celsius))
      setDelay(String(payload.delay_minutes))
      setError(null)
    } catch (err) {
      setConfig(null)
      setMinTemp('2')
      setMaxTemp('8')
      setDelay('30')
      if (!(err instanceof ApiError && err.status === 404)) {
        setError(
          err instanceof Error
            ? err.message
            : 'Không thể tải cấu hình chuỗi lạnh.',
        )
      }
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadConfig(productId)
    }, 150)
    return () => {
      window.clearTimeout(timer)
    }
  }, [productId, loadConfig])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (saving || !productId) return
    const problem = validateColdChainConfig(minTemp, maxTemp, delay)
    if (problem) {
      setError(problem)
      return
    }
    const min = Number(minTemp)
    const max = Number(maxTemp)
    const minutes = Number(delay)
    if (min >= max) {
      setError('Ngưỡng dưới phải nhỏ hơn ngưỡng trên.')
      return
    }
    if (minutes < 1 || minutes > 1440) {
      setError('Độ trễ phải từ 1 đến 1440 phút.')
      return
    }
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const saved = await updateProductColdChainConfig(productId, {
        min_temp_celsius: String(min),
        max_temp_celsius: String(max),
        delay_minutes: minutes,
      })
      setConfig(saved)
      setNotice(
        `Đã lưu ngưỡng của ${saved.product_name}: ${saved.min_temp_celsius}°C đến ${saved.max_temp_celsius}°C, phát hiện sau ${saved.delay_minutes} phút.`,
      )
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể lưu cấu hình chuỗi lạnh.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section
      className="panel-card panel-box"
      aria-label="Cấu hình ngưỡng chuỗi lạnh theo loại nông sản"
    >
      <header className="panel-head">
        <div>
          <h2>Ngưỡng chuỗi lạnh theo nông sản</h2>
          <p className="panel-sub">
            Khi mở chuyến, hệ thống chốt ngưỡng chặt nhất của mọi loại hàng trên
            chuyến. Đổi cấu hình sau này không tính lại vi phạm của chuyến đang
            chạy.
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

      <div className="integrity-check-controls">
        <div className="form-field">
          <label htmlFor="cold-chain-product">Nông sản</label>
          <select
            id="cold-chain-product"
            value={productId}
            onChange={(event) => setProductId(event.target.value)}
            disabled={products.length === 0}
          >
            {products.length === 0 && (
              <option value="">Chưa có nông sản trong danh mục</option>
            )}
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && products.length === 0 && <p role="status">Đang tải danh mục…</p>}

      {productId && !config && !loading && (
        <div className="alert-box alert-info" role="status">
          Nông sản này chưa có cấu hình. Nếu không cấu hình thì chuyến dùng mặc
          định 2–8°C và 30 phút.
        </div>
      )}

      <form onSubmit={submit} className="integrity-check-controls">
        <div className="form-field">
          <label htmlFor="cold-chain-min">Ngưỡng dưới (°C)</label>
          <input
            id="cold-chain-min"
            type="number"
            step="0.1"
            disabled={!canWrite}
            value={minTemp}
            onChange={(event) => setMinTemp(event.target.value)}
          />
        </div>
        <div className="form-field">
          <label htmlFor="cold-chain-max">Ngưỡng trên (°C)</label>
          <input
            id="cold-chain-max"
            type="number"
            step="0.1"
            disabled={!canWrite}
            value={maxTemp}
            onChange={(event) => setMaxTemp(event.target.value)}
          />
        </div>
        <div className="form-field">
          <label htmlFor="cold-chain-delay">Độ trễ (phút)</label>
          <input
            id="cold-chain-delay"
            type="number"
            step="1"
            disabled={!canWrite}
            value={delay}
            onChange={(event) => setDelay(event.target.value)}
          />
        </div>
        {canWrite && (
          <button
            type="submit"
            className="ds-button ds-button-brand"
            disabled={saving}
          >
            {saving ? 'Đang lưu…' : 'Lưu ngưỡng'}
          </button>
        )}
      </form>

      {!canWrite && (
        <p role="status">
          Tài khoản này chỉ xem được cấu hình, không sửa được.
        </p>
      )}
    </section>
  )
}
