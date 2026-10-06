import { useEffect, useState, type FormEvent } from 'react'
import { getEvents, getLots, getProducts } from '../services/api'
import type { Lot, LotEvent, Product } from '../types'
import { EventTimeline } from './EventTimeline'
import { LotCreateForm } from './LotCreateForm'

const PAGE_SIZE = 20

interface LotsPanelProps {
  canReadLots: boolean
  canCreateLots: boolean
  canReadEvents?: boolean
}

function displayLotCode(lot: Lot): string {
  return lot.lot_code ?? `${lot.id.slice(0, 8)}…${lot.id.slice(-6)}`
}

export function LotsPanel({
  canReadLots,
  canCreateLots,
  canReadEvents = true,
}: LotsPanelProps) {
  const [lots, setLots] = useState<Lot[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(canReadLots)
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [productError, setProductError] = useState<string | null>(null)
  const [queryInput, setQueryInput] = useState('')
  const [query, setQuery] = useState('')
  const [productId, setProductId] = useState('')
  const [page, setPage] = useState(1)
  const [hasNextPage, setHasNextPage] = useState(false)
  const [refreshToken, setRefreshToken] = useState(0)
  const [selectedLot, setSelectedLot] = useState<Lot | null>(null)
  const [eventResult, setEventResult] = useState<{
    lotId: string
    events: LotEvent[]
  } | null>(null)

  useEffect(() => {
    let active = true
    getProducts()
      .then((data) => { if (active) setProducts(data) })
      .catch((err: unknown) => {
        if (active) setProductError(err instanceof Error ? err.message : 'Không thể tải sản phẩm.')
      })
      .finally(() => { if (active) setLoadingProducts(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!canReadLots) return
    let active = true
    getLots({
      q: query,
      product_id: productId || undefined,
      offset: (page - 1) * PAGE_SIZE,
      page_size: PAGE_SIZE + 1,
    })
      .then((data) => {
        if (!active) return
        setHasNextPage(data.length > PAGE_SIZE)
        setLots(data.slice(0, PAGE_SIZE))
        setSelectedLot((current) =>
          current && data.some((lot) => lot.id === current.id)
            ? current
            : data[0] ?? null,
        )
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải danh sách lô.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [canReadLots, query, productId, page, refreshToken])

  useEffect(() => {
    if (!selectedLot || !canReadEvents) {
      return
    }
    let active = true
    getEvents(selectedLot.id)
      .then((allEvents) => {
        if (active) {
          setEventResult({
            lotId: selectedLot.id,
            events: allEvents
              .filter((event) => event.lot_id === selectedLot.id)
              .sort((a, b) => a.sequence_number - b.sequence_number),
          })
        }
      })
      .catch(() => {
        if (active) setEventResult({ lotId: selectedLot.id, events: [] })
      })
    return () => { active = false }
  }, [selectedLot, canReadEvents])

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setSelectedLot(null)
    setPage(1)
    setQuery(queryInput.trim())
    setRefreshToken((token) => token + 1)
  }

  const handleCreated = (lot: Lot) => {
    setLoading(true)
    setError(null)
    setQueryInput('')
    setQuery('')
    setProductId(lot.product_id ?? '')
    setPage(1)
    setSelectedLot(lot)
    setRefreshToken((token) => token + 1)
  }

  const refreshLots = () => {
    setLoading(true)
    setError(null)
    setRefreshToken((token) => token + 1)
  }

  if (!canReadLots) {
    return <section className="panel-card panel-box" role="status">Tài khoản này không có quyền xem danh sách lô.</section>
  }

  const lotEvents =
    eventResult && selectedLot && eventResult.lotId === selectedLot.id
      ? eventResult.events
      : []
  const loadingEvents = Boolean(
    selectedLot && canReadEvents && eventResult?.lotId !== selectedLot.id,
  )

  return (
    <div className="info-stack">
      {canCreateLots && (
        <LotCreateForm
          products={products}
          loadingProducts={loadingProducts}
          onCreated={handleCreated}
        />
      )}

      <section className="data-table-wrapper panel-card" aria-labelledby="lots-table-title">
        <div className="data-table-header">
          <div>
            <h2 id="lots-table-title" className="section-title">Lô tổ chức đang giữ</h2>
            <p className="panel-sub">20 lô mỗi trang, sắp theo ngày thu hoạch mới nhất.</p>
          </div>
          <button type="button" className="ds-button ds-button-secondary ds-button-sm" onClick={refreshLots} disabled={loading}>
            {loading ? 'Đang tải...' : 'Làm mới'}
          </button>
        </div>

        <form className="lot-filter-row" onSubmit={submitSearch}>
          <div className="form-field lot-search-field">
            <label htmlFor="lot-search">Tìm theo mã lô</label>
            <input id="lot-search" type="search" value={queryInput} onChange={(event) => setQueryInput(event.target.value)} placeholder="Nhập một phần mã lô" />
          </div>
          <div className="form-field lot-product-filter">
            <label htmlFor="lot-product-filter">Lọc sản phẩm</label>
            <select id="lot-product-filter" value={productId} onChange={(event) => { setLoading(true); setError(null); setSelectedLot(null); setProductId(event.target.value); setPage(1) }} disabled={loadingProducts}>
              <option value="">Tất cả sản phẩm</option>
              {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
            </select>
          </div>
          <button className="ds-button ds-button-brand ds-button-sm" type="submit">Tìm lô</button>
        </form>

        {productError && <div className="alert-box alert-error table-alert" role="alert">{productError}</div>}
        {error && <div className="alert-box alert-error table-alert" role="alert">{error}</div>}
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr><th scope="col">Mã lô</th><th scope="col">Sản phẩm</th><th scope="col">Thu hoạch</th><th scope="col">Khối lượng</th><th scope="col">Vùng trồng</th><th scope="col">Thao tác</th></tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="cell-center" aria-busy="true">Đang tải danh sách lô...</td></tr>
              ) : lots.length === 0 ? (
                <tr><td colSpan={6} className="cell-center">Không tìm thấy lô phù hợp.</td></tr>
              ) : lots.map((lot) => {
                const isSelected = selectedLot?.id === lot.id
                return (
                  <tr key={lot.id} className={isSelected ? 'lot-row-selected' : undefined}>
                    <td><code title={lot.id}>{displayLotCode(lot)}</code></td>
                    <th scope="row" className="cell-strong">{lot.product?.name ?? lot.name}</th>
                    <td>{lot.harvested_on ?? '—'}</td>
                    <td>{lot.quantity ? `${lot.quantity} ${lot.product?.unit ?? ''}` : '—'}</td>
                    <td><code title={lot.farm_id}>{lot.farm_id.slice(0, 8)}…</code></td>
                    <td>
                      <button type="button" className="ds-button ds-button-secondary ds-button-sm" aria-pressed={isSelected} onClick={() => setSelectedLot(lot)}>
                        {isSelected ? 'Đang chọn' : 'Xem sự kiện'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="lot-pagination" aria-label="Phân trang danh sách lô">
          <span>Trang {page}</span>
          <div className="action-row">
            <button type="button" className="ds-button ds-button-secondary ds-button-sm" onClick={() => { setLoading(true); setError(null); setPage((current) => Math.max(1, current - 1)) }} disabled={page === 1 || loading}>Trước</button>
            <button type="button" className="ds-button ds-button-secondary ds-button-sm" onClick={() => { setLoading(true); setError(null); setPage((current) => current + 1) }} disabled={!hasNextPage || loading}>Tiếp</button>
          </div>
        </div>
      </section>

      {selectedLot && canReadEvents && (
        <section className="panel-card panel-box">
          <EventTimeline events={lotEvents} lotName={selectedLot.name} loading={loadingEvents} />
        </section>
      )}
    </div>
  )
}
