import { useEffect, useState, type FormEvent } from 'react'
import { getLotHistory, getLots, getProducts } from '../services/api'
import type { EventHistory, Lot, Product } from '../types'
import { EventTimeline } from './EventTimeline'
import { LotCreateForm } from './LotCreateForm'

const PAGE_SIZE = 20

interface LotsPanelProps {
  canReadLots: boolean
  canCreateLots: boolean
  canReadEvents?: boolean
  onOpenLot: (lotId: string) => void
}

function displayLotCode(lot: Lot): string {
  return lot.lot_code ?? lot.id.slice(0, 8)
}

function statusLabel(status: Lot['status']): string {
  if (status === 'pending_handover') return 'Chờ bàn giao'
  if (status === 'closed') return 'Đã đóng'
  return 'Đang lưu hành'
}

export function LotsPanel({
  canReadLots,
  canCreateLots,
  canReadEvents = true,
  onOpenLot,
}: LotsPanelProps) {
  const [lots, setLots] = useState<Lot[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(canReadLots)
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [queryInput, setQueryInput] = useState('')
  const [query, setQuery] = useState('')
  const [productId, setProductId] = useState('')
  const [cursor, setCursor] = useState<string | undefined>()
  const [cursorHistory, setCursorHistory] = useState<Array<string | undefined>>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [refreshToken, setRefreshToken] = useState(0)
  const [selectedLot, setSelectedLot] = useState<Lot | null>(null)
  const [history, setHistory] = useState<EventHistory | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)

  useEffect(() => {
    let active = true
    getProducts()
      .then((data) => { if (active) setProducts(data) })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải danh mục sản phẩm.')
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
      cursor,
      page_size: PAGE_SIZE,
    })
      .then((page) => {
        if (!active) return
        setLots(page.items)
        setNextCursor(page.next_cursor)
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải danh sách lô.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [canReadLots, query, productId, cursor, refreshToken])

  useEffect(() => {
    if (!selectedLot || !canReadEvents) return
    let active = true
    getLotHistory(selectedLot.id)
      .then((result) => { if (active) setHistory(result) })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không thể tải lịch sử lô.')
      })
      .finally(() => { if (active) setHistoryLoading(false) })
    return () => { active = false }
  }, [selectedLot, canReadEvents])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const nextQuery = queryInput.trim()
      if (nextQuery === query) return
      setLoading(true)
      setError(null)
      setCursor(undefined)
      setCursorHistory([])
      setSelectedLot(null)
      setHistory(null)
      setQuery(nextQuery)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [queryInput, query])

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setQuery(queryInput.trim())
    setCursor(undefined)
    setCursorHistory([])
  }

  const changeProduct = (value: string) => {
    setProductId(value)
    setLoading(true)
    setError(null)
    setCursor(undefined)
    setCursorHistory([])
    setSelectedLot(null)
    setHistory(null)
  }

  const handleCreated = (lot: Lot) => {
    setQueryInput('')
    setError(null)
    setQuery('')
    setProductId(lot.product_id ?? '')
    setCursor(undefined)
    setCursorHistory([])
    setSelectedLot(lot)
    setHistoryLoading(canReadEvents)
    setShowCreate(false)
    setRefreshToken((token) => token + 1)
  }

  if (!canReadLots) {
    return <section className="panel-card panel-box" role="status">Tài khoản này không có quyền xem danh sách lô.</section>
  }

  return (
    <div className="lots-page">
      {showCreate && canCreateLots && (
        <div id="lot-create-panel">
          <LotCreateForm
            products={products}
            loadingProducts={loadingProducts}
            onCreated={handleCreated}
          />
        </div>
      )}

      <section className="data-table-wrapper panel-card" aria-labelledby="lots-table-title">
        <div className="data-table-header">
          <div>
            <h2 id="lots-table-title" className="section-title">Danh sách lô</h2>
            <p className="panel-sub">Tra cứu lô thu hoạch và xem lịch sử truy xuất.</p>
          </div>
          <div className="lots-toolbar-actions">
            {canCreateLots && (
              <button
                type="button"
                className="ds-button ds-button-brand"
                aria-expanded={showCreate}
                aria-controls="lot-create-panel"
                onClick={() => setShowCreate((visible) => !visible)}
              >
                {showCreate ? 'Đóng biểu mẫu' : 'Tạo lô'}
              </button>
            )}
            <button
              type="button"
              className="ds-button ds-button-secondary"
              onClick={() => { setLoading(true); setError(null); setRefreshToken((token) => token + 1) }}
              disabled={loading}
            >
              Làm mới
            </button>
          </div>
        </div>

        <form className="lot-filter-row" onSubmit={submitSearch}>
          <div className="form-field lot-search-field">
            <label htmlFor="lot-search">Mã lô</label>
            <input
              id="lot-search"
              type="search"
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
              placeholder="Tìm theo mã lô"
            />
          </div>
          <div className="form-field lot-product-filter">
            <label htmlFor="lot-product-filter">Sản phẩm</label>
            <select id="lot-product-filter" value={productId} onChange={(event) => changeProduct(event.target.value)} disabled={loadingProducts}>
              <option value="">Tất cả sản phẩm</option>
              {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
            </select>
          </div>
        </form>

        {error && <div className="alert-box alert-error table-alert" role="alert">{error}</div>}
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Mã lô</th>
                <th scope="col">Sản phẩm</th>
                <th scope="col">Ngày thu hoạch</th>
                <th scope="col">Còn lại</th>
                <th scope="col">Trạng thái</th>
                {canReadEvents && <th scope="col">Lịch sử</th>}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={canReadEvents ? 6 : 5} className="cell-center" aria-busy="true">Đang tải danh sách lô…</td></tr>
              ) : lots.length === 0 ? (
                <tr>
                  <td colSpan={canReadEvents ? 6 : 5} className="cell-center">
                    {query || productId
                      ? 'Không có lô khớp bộ lọc.'
                      : 'Chưa có lô hàng. Ghi nhận lô thu hoạch đầu tiên để bắt đầu truy xuất.'}
                  </td>
                </tr>
              ) : lots.map((lot) => (
                <tr key={lot.id} className={selectedLot?.id === lot.id ? 'lot-row-selected' : undefined}>
                  <th scope="row" className="cell-strong">
                    <a
                      className="lot-code-link"
                      href={`/lots/${lot.id}`}
                      onClick={(event) => {
                        event.preventDefault()
                        onOpenLot(lot.id)
                      }}
                    >
                      <code>{displayLotCode(lot)}</code>
                    </a>
                  </th>
                  <td>{lot.product?.name ?? lot.name}</td>
                  <td>{lot.harvested_on ?? '—'}</td>
                  <td>{lot.remaining_quantity} {lot.product?.unit ?? ''}</td>
                  <td>{statusLabel(lot.status)}</td>
                  {canReadEvents && (
                    <td>
                      <button
                        type="button"
                        className="ds-button ds-button-secondary ds-button-sm"
                        aria-expanded={selectedLot?.id === lot.id}
                        onClick={() => {
                          setSelectedLot((current) => current?.id === lot.id ? null : lot)
                          setHistory(null)
                          setHistoryLoading(true)
                          setError(null)
                        }}
                      >
                        {selectedLot?.id === lot.id ? 'Ẩn' : 'Xem lịch sử'}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="lot-pagination">
          <button
            type="button"
            className="ds-button ds-button-secondary ds-button-sm"
            onClick={() => {
              setLoading(true)
              setError(null)
              setSelectedLot(null)
              setHistory(null)
              const previous = [...cursorHistory]
              const previousCursor = previous.pop()
              setCursorHistory(previous)
              setCursor(previousCursor)
            }}
            disabled={cursorHistory.length === 0 || loading}
          >
            Trước
          </button>
          <button
            type="button"
            className="ds-button ds-button-secondary ds-button-sm"
            onClick={() => {
              if (!nextCursor) return
              setLoading(true)
              setError(null)
              setSelectedLot(null)
              setHistory(null)
              setCursorHistory((history) => [...history, cursor])
              setCursor(nextCursor)
            }}
            disabled={!nextCursor || loading}
          >
            Tiếp
          </button>
        </div>
      </section>

      {selectedLot && canReadEvents && (
        <section className="panel-card panel-box" aria-label={`Lịch sử lô ${displayLotCode(selectedLot)}`}>
          <EventTimeline
            events={history?.events ?? []}
            lotName={selectedLot.lot_code ?? selectedLot.name}
            loading={historyLoading}
            integrity={history?.integrity}
          />
        </section>
      )}
    </div>
  )
}
