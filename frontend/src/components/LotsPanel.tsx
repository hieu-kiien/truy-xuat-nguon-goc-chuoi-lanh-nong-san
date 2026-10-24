import { useEffect, useState } from 'react'
import {
  clearApiCache,
  getFarms,
  getLots,
  getProducts,
  peekCachedFarms,
  peekCachedLots,
  peekCachedProducts,
} from '../services/api'
import type { Farm, Lot, Product } from '../types'
import { lotStatusLabel } from '../types'
import { EditDialog } from './EditDialog'
import { LotCreateForm } from './LotCreateForm'
import { LotTransformForm } from './LotTransformForm'
import { SquircleIcon } from './VietFarmVisuals'

interface Props {
  canReadLots: boolean
  canCreateLots: boolean
  canReadFarms?: boolean
  canReadEvents?: boolean
  canTransform?: boolean
  organizationId?: string
  onOpenLot: (id: string) => void
}

export function LotsPanel({
  canReadLots,
  canCreateLots,
  canReadFarms = true,
  canReadEvents = true,
  canTransform,
  organizationId,
  onOpenLot,
}: Props) {
  const task = new URLSearchParams(window.location.search).get('task')
  const [isCreateOpen, setIsCreateOpen] = useState(() => task === 'create')
  const [isMergeOpen, setIsMergeOpen] = useState(false)
  const initialLotsPage = canReadLots ? peekCachedLots({ page_size: 20 }) : null
  const initialProducts = peekCachedProducts()
  const initialFarms = canReadFarms ? peekCachedFarms() : null
  const [lots, setLots] = useState<Lot[]>(() => initialLotsPage?.items ?? [])
  const [products, setProducts] = useState<Product[]>(() => initialProducts ?? [])
  const [farms, setFarms] = useState<Farm[]>(() => initialFarms ?? [])
  const [loading, setLoading] = useState(() => canReadLots && !initialLotsPage)
  const [loadingProducts, setLoadingProducts] = useState(() => !initialProducts)
  const [loadingFarms, setLoadingFarms] = useState(() => Boolean(canReadFarms) && !initialFarms)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [productId, setProductId] = useState('')
  const [farmId, setFarmId] = useState('')
  const [harvestedFrom, setHarvestedFrom] = useState('')
  const [harvestedTo, setHarvestedTo] = useState('')
  const [cursor, setCursor] = useState<string | undefined>()
  const [previousCursors, setPreviousCursors] = useState<Array<string | undefined>>([])
  const [nextCursor, setNextCursor] = useState<string | null>(() => initialLotsPage?.next_cursor ?? null)
  const [refresh, setRefresh] = useState(0)
  const [selected, setSelected] = useState<Lot[]>([])

  useEffect(() => {
    let active = true
    getProducts()
      .then((data) => {
        if (active) setProducts(data)
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Không tải được sản phẩm.')
      })
      .finally(() => {
        if (active) setLoadingProducts(false)
      })
    if (canReadFarms) {
      getFarms()
        .then((data) => {
          if (active) setFarms(data)
        })
        .catch(() => {
          if (active) setFarms([])
        })
        .finally(() => {
          if (active) setLoadingFarms(false)
        })
    }
    return () => {
      active = false
    }
  }, [canReadFarms])

  useEffect(() => {
    if (!canReadLots) return
    let active = true
    const delayMs = query.trim() ? 200 : 0
    const timer = window.setTimeout(() => {
      getLots({
        q: query.trim(),
        product_id: productId || undefined,
        farm_id: farmId || undefined,
        harvested_from: harvestedFrom || undefined,
        harvested_to: harvestedTo || undefined,
        cursor,
        page_size: 20,
      })
        .then((page) => {
          if (active) {
            setLots(page.items)
            setNextCursor(page.next_cursor)
          }
        })
        .catch((err: unknown) => {
          if (active) setError(err instanceof Error ? err.message : 'Không tải được danh sách lô.')
        })
        .finally(() => {
          if (active) setLoading(false)
        })
    }, delayMs)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [canReadLots, query, productId, farmId, harvestedFrom, harvestedTo, cursor, refresh])

  const resetPage = () => {
    setLoading(true)
    setError(null)
    setCursor(undefined)
    setPreviousCursors([])
  }

  if (!canReadLots) return <p role="status">Tài khoản này không có quyền xem danh sách lô.</p>

  return (
    <section className="data-table-wrapper panel-card" aria-labelledby="lots-table-title">
      <div className="data-table-header">
        <div>
          <h2 id="lots-table-title">Danh sách lô</h2>
          <p className="panel-sub">Chọn nông sản để xem thông tin lô và nguồn gốc.</p>
        </div>
        <div className="action-row">
          {canCreateLots && (
            <a
              href="/lots?task=create"
              className="ds-button ds-button-brand"
              onClick={(event) => {
                event.preventDefault()
                setIsCreateOpen(true)
              }}
            >
              Tạo lô thu hoạch
            </a>
          )}
          <button
            className="ds-button ds-button-secondary"
            type="button"
            disabled={loading}
            onClick={() => {
              clearApiCache()
              setLoading(true)
              setError(null)
              setRefresh((value) => value + 1)
            }}
          >
            Làm mới
          </button>
        </div>
      </div>
      <div className="lot-filter-row">
        <label className="form-field">
          Tìm theo mã lô
          <input
            type="search"
            value={query}
            onChange={(event) => {
              resetPage()
              setQuery(event.target.value)
            }}
            placeholder="Nhập mã lô cần tìm"
          />
        </label>
        <label className="form-field">
          Sản phẩm
          <select
            value={productId}
            disabled={loadingProducts}
            onChange={(event) => {
              resetPage()
              setSelected([])
              setProductId(event.target.value)
            }}
          >
            <option value="">Tất cả sản phẩm</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          Vùng trồng
          <select
            value={farmId}
            disabled={loadingFarms}
            onChange={(event) => {
              resetPage()
              setSelected([])
              setFarmId(event.target.value)
            }}
          >
            <option value="">Tất cả vùng trồng</option>
            {farms.map((farm) => (
              <option key={farm.id} value={farm.id}>
                {farm.name}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          Thu hoạch từ
          <input
            type="date"
            value={harvestedFrom}
            onChange={(event) => {
              resetPage()
              setHarvestedFrom(event.target.value)
            }}
          />
        </label>
        <label className="form-field">
          đến
          <input
            type="date"
            value={harvestedTo}
            onChange={(event) => {
              resetPage()
              setHarvestedTo(event.target.value)
            }}
          />
        </label>
      </div>
      {canTransform && (
        <div className="selection-bar">
          <p>
            {selected.length
              ? `Đã chọn ${selected.length} lô. Chỉ gộp lô cùng sản phẩm do đơn vị của bạn đang giữ.`
              : 'Để gộp lô, tích chọn ít nhất hai lô cùng sản phẩm.'}
          </p>
          {selected.length >= 2 && (
            <a
              href={`/lots/${selected[0].id}?task=merge&parents=${selected.map((lot) => lot.id).join(',')}`}
              className="ds-button ds-button-brand"
              onClick={(event) => {
                event.preventDefault()
                window.history.replaceState(
                  {},
                  '',
                  `/lots/${selected[0].id}?task=merge&parents=${selected.map((lot) => lot.id).join(',')}`
                )
                setIsMergeOpen(true)
              }}
            >
              Gộp {selected.length} lô đã chọn
            </a>
          )}
          {selected.length > 0 && (
            <button type="button" className="ds-button ds-button-secondary" onClick={() => setSelected([])}>
              Bỏ chọn tất cả
            </button>
          )}
        </div>
      )}
      {error && <p className="alert-box alert-error table-alert" role="alert">{error}</p>}
      <div className="table-scroll">
        <table className="data-table lots-table">
          <thead>
            <tr>
              {canTransform && <th scope="col">Chọn</th>}
              <th scope="col">Nông sản</th>
              <th scope="col">Mã truy xuất</th>
              <th scope="col">Ngày thu hoạch</th>
              <th scope="col">Còn lại</th>
              <th scope="col">Trạng thái</th>
              <th scope="col">Địa điểm</th>
              {canReadEvents && <th scope="col">Lịch sử</th>}
            </tr>
          </thead>
          <tbody className={loading && lots.length > 0 ? 'table-body-reloading' : undefined}>
            {loading && lots.length === 0 ? (
              <tr>
                <td colSpan={8} aria-busy="true">
                  Đang tải danh sách lô…
                </td>
              </tr>
            ) : lots.length === 0 ? (
              <tr>
                <td colSpan={8}>Không có lô phù hợp. Thử đổi bộ lọc hoặc tạo lô thu hoạch mới.</td>
              </tr>
            ) : (
              <>
                {loading && (
                  <tr className="table-loading-progress-row" aria-hidden="true">
                    <td colSpan={8} aria-busy="true" className="table-loading-progress-cell">
                      <div className="table-reloading-bar" />
                    </td>
                  </tr>
                )}
                {lots.map((lot) => {
                  const code = lot.lot_code ?? lot.id.slice(0, 8)
                  const selectedHere = selected.some((item) => item.id === lot.id)
                  const displayName =
                    lot.name && lot.name !== lot.product?.name ? lot.name : (lot.product?.name ?? lot.name)
                  const reason =
                    lot.current_holder_organization_id !== organizationId
                      ? 'Đơn vị của bạn không giữ lô này'
                      : lot.status !== 'active' || Number(lot.remaining_quantity) <= 0
                      ? 'Lô không còn lượng khả dụng'
                      : selected.length && selected[0].product_id !== lot.product_id
                      ? 'Sản phẩm khác với lô đã chọn'
                      : selected.length >= 100 && !selectedHere
                      ? 'Tối đa 100 lô mỗi lần gộp'
                      : ''
                  return (
                    <tr key={lot.id}>
                      {canTransform && (
                        <td data-label="Chọn" title={reason}>
                          <input
                            type="checkbox"
                            aria-label={`Chọn ${code}${reason ? `: ${reason}` : ''}`}
                            checked={selectedHere}
                            disabled={!!reason && !selectedHere}
                            onChange={(event) => {
                              if (event.target.checked && selected.length === 0) {
                                const nextProductId = lot.product_id ?? ''
                                if (productId !== nextProductId || cursor !== undefined) {
                                  resetPage()
                                  setProductId(nextProductId)
                                }
                              }
                              setSelected((current) =>
                                event.target.checked
                                  ? [...current, lot]
                                  : current.filter((item) => item.id !== lot.id)
                              )
                            }}
                          />
                          {reason && !selectedHere && <small className="panel-sub">{reason}</small>}
                        </td>
                      )}
                      <th scope="row" data-label="Nông sản">
                        <div className="vf-lot-cell-brand">
                          <SquircleIcon nameHint={displayName} size="sm" />
                          <a
                            className="lot-code-link"
                            href={`/lots/${lot.id}`}
                            onClick={(event) => {
                              if (
                                !event.ctrlKey &&
                                !event.metaKey &&
                                !event.shiftKey &&
                                !event.button
                              ) {
                                event.preventDefault()
                                onOpenLot(lot.id)
                              }
                            }}
                          >
                            {displayName}
                          </a>
                        </div>
                      </th>
                      <td data-label="Mã truy xuất">
                        <code className="lot-code-tag">{code}</code>
                      </td>
                      <td data-label="Ngày thu hoạch">{lot.harvested_on ?? 'Lô dẫn xuất'}</td>
                      <td data-label="Còn lại">
                        <strong>
                          {lot.remaining_quantity} {lot.product?.unit}
                        </strong>
                      </td>
                      <td data-label="Trạng thái">
                        <span
                          className={`status-badge ${
                            lot.status === 'active' ? 'status-done' : 'status-neutral'
                          }`}
                        >
                          {lotStatusLabel(lot.status)}
                        </span>
                      </td>
                      <td data-label="Địa điểm">{lot.current_location?.name ?? 'Chưa gán địa điểm'}</td>
                      {canReadEvents && (
                        <td data-label="Lịch sử">
                          <a
                            href={`/lots/${lot.id}?view=history`}
                            className="ds-button ds-button-secondary"
                            onClick={(event) => {
                              if (
                                !event.ctrlKey &&
                                !event.metaKey &&
                                !event.shiftKey &&
                                !event.button
                              ) {
                                event.preventDefault()
                                window.history.pushState({}, '', `/lots/${lot.id}?view=history`)
                                window.dispatchEvent(new PopStateEvent('popstate'))
                              }
                            }}
                          >
                            Xem lịch sử
                          </a>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </>
            )}
          </tbody>
        </table>
      </div>
      <div className="lot-pagination">
        <span>
          Trang {previousCursors.length + 1} · {lots.length} lô trên trang
        </span>
        <button
          type="button"
          className="ds-button ds-button-secondary"
          disabled={loading || previousCursors.length === 0}
          onClick={() => {
            const previous = [...previousCursors]
            setCursor(previous.pop())
            setPreviousCursors(previous)
            setLoading(true)
            setError(null)
          }}
        >
          Trang trước
        </button>
        <button
          type="button"
          className="ds-button ds-button-secondary"
          disabled={loading || !nextCursor}
          onClick={() => {
            if (nextCursor) {
              setPreviousCursors((current) => [...current, cursor])
              setCursor(nextCursor)
              setLoading(true)
              setError(null)
            }
          }}
        >
          Trang sau
        </button>
      </div>

      {/* In-Place Creation Modal */}
      {(isCreateOpen || task === 'create') && (
        <EditDialog
          title="Ghi nhận lô thu hoạch"
          onClose={() => {
            setIsCreateOpen(false)
            if (window.location.search.includes('task=create')) {
              const params = new URLSearchParams(window.location.search)
              params.delete('task')
              const search = params.toString() ? `?${params.toString()}` : ''
              window.history.replaceState({}, '', `${window.location.pathname}${search}`)
            }
          }}
        >
          {canCreateLots ? (
            <LotCreateForm
              products={products}
              loadingProducts={loadingProducts}
              onClose={() => {
                setIsCreateOpen(false)
                if (window.location.search.includes('task=create')) {
                  const params = new URLSearchParams(window.location.search)
                  params.delete('task')
                  const search = params.toString() ? `?${params.toString()}` : ''
                  window.history.replaceState({}, '', `${window.location.pathname}${search}`)
                }
              }}
              onCreated={(lot) => {
                setIsCreateOpen(false)
                setRefresh((v) => v + 1)
                if (window.location.search.includes('task=create')) {
                  const params = new URLSearchParams(window.location.search)
                  params.delete('task')
                  const search = params.toString() ? `?${params.toString()}` : ''
                  window.history.replaceState({}, '', `${window.location.pathname}${search}`)
                }
                onOpenLot(lot.id)
              }}
            />
          ) : (
            <p role="status">Tài khoản này không có quyền tạo lô thu hoạch.</p>
          )}
        </EditDialog>
      )}

      {/* In-Place Merge Modal */}
      {isMergeOpen && selected.length >= 2 && (
        <EditDialog
          title="Gộp các lô nông sản đã chọn"
          onClose={() => {
            setIsMergeOpen(false)
            window.history.replaceState({}, '', '/lots')
          }}
        >
          <LotTransformForm
            key={`merge-${selected[0].id}`}
            lot={selected[0]}
            initialMode="merge"
            canManageDistribution={false}
            onClose={() => {
              setIsMergeOpen(false)
              setSelected([])
              window.history.replaceState({}, '', '/lots')
            }}
            onCompleted={(newLotId) => {
              setIsMergeOpen(false)
              setSelected([])
              window.history.replaceState({}, '', '/lots')
              onOpenLot(newLotId)
            }}
            onTransformed={async () => {
              setRefresh((v) => v + 1)
              setSelected([])
            }}
          />
        </EditDialog>
      )}
    </section>
  )
}
