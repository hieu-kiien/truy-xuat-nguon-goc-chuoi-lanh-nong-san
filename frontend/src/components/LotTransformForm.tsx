import { useEffect, useRef, useState, type FormEvent } from 'react'
import { getLocations, getLots, getLot, mergeLots, splitLot } from '../services/api'
import type { DistributionLocation, Lot } from '../types'
import { grams, formatGrams, splitSummary } from '../utils/mass'
import { eligibleMergeCandidates } from '../utils/merge'

interface Props {
  lot: Lot
  initialMode?: 'split' | 'merge'
  canManageDistribution: boolean
  onCompleted: (id: string) => void
  onTransformed?: () => Promise<void>
  onClose?: () => void
  onNotify?: (message: string) => void
  onSuccess?: (lot: Lot) => void
}

export function LotTransformForm({
  lot,
  initialMode = 'split',
  canManageDistribution,
  onCompleted,
  onTransformed,
  onClose,
  onNotify,
  onSuccess,
}: Props) {
  const [mode, setMode] = useState<'split' | 'merge'>(initialMode)
  const unit = lot.product?.unit ?? 'kg'
  const [children, setChildren] = useState([
    { name: `${lot.product?.name ?? 'Nông sản'} — phần 1`, quantity: '', location_id: '' },
    { name: `${lot.product?.name ?? 'Nông sản'} — phần 2`, quantity: '', location_id: '' },
  ])
  const [locations, setLocations] = useState<DistributionLocation[]>([])
  const [locationsLoading, setLocationsLoading] = useState(canManageDistribution)
  const [candidates, setCandidates] = useState<Lot[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState(`${lot.product?.name ?? 'Nông sản'} — lô gộp`)
  const [quantities, setQuantities] = useState<Record<string, string>>({ [lot.id]: lot.remaining_quantity })
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const busy = useRef(false)
  const loadingMore = useRef(false)
  const [resultLots, setResultLots] = useState<Lot[]>([])
  const [candidatePage, setCandidatePage] = useState(0)

  const unselectedCandidates = candidates.filter((item) => !quantities[item.id])
  const candidatePages = Math.max(1, Math.ceil(unselectedCandidates.length / 10))
  const currentCandidatePage = Math.min(candidatePage, candidatePages - 1)
  const displayedMergeLots = [
    lot,
    ...candidates.filter((item) => !!quantities[item.id]),
    ...unselectedCandidates.slice(currentCandidatePage * 10, currentCandidatePage * 10 + 10),
  ]

  const summary = splitSummary(children.map((child) => child.quantity), lot.remaining_quantity)
  const mergeSelection = [lot, ...candidates].filter((item) => !!quantities[item.id])
  const mergeValid =
    !!name.trim() &&
    mergeSelection.length >= 2 &&
    mergeSelection.every((item) => {
      const value = grams(quantities[item.id])
      return value !== null && value > 0n && value <= (grams(item.remaining_quantity) ?? 0n)
    })
  const mergeTotal = mergeSelection.reduce((sum, item) => sum + (grams(quantities[item.id]) ?? 0n), 0n)

  useEffect(() => {
    if (!canManageDistribution) return
    let active = true
    getLocations()
      .then((result) => { if (active) setLocations(result) })
      .catch((err: unknown) => { if (active) setError(err instanceof Error ? err.message : 'Không thể tải địa điểm.') })
      .finally(() => { if (active) setLocationsLoading(false) })
    return () => { active = false }
  }, [canManageDistribution])

  useEffect(() => {
    let active = true
    const selectedIds = [
      ...new Set(
        (new URLSearchParams(window.location.search).get('parents') ?? '')
          .split(',')
          .filter((id) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id) && id !== lot.id)
      ),
    ].slice(0, 99)

    Promise.all([
      getLots({ product_id: lot.product_id ?? undefined, page_size: 100 }),
      Promise.all(selectedIds.map(getLot)),
    ])
      .then(([page, selected]) => {
        if (!active) return
        const eligible = eligibleMergeCandidates([...selected, ...page.items], lot)
        setCandidates(eligible)
        setQuantities((current) => ({
          ...current,
          ...Object.fromEntries(
            eligible.filter((item) => selectedIds.includes(item.id)).map((item) => [item.id, item.remaining_quantity])
          ),
        }))
        setCursor(page.next_cursor)
        if (selectedIds.some((id) => !eligible.some((item) => item.id === id))) {
          setError('Một số lô đã chọn không còn khả dụng hoặc không cùng sản phẩm/chủ giữ. Kiểm tra lại các lô trước khi gộp.')
        }
      })
      .catch((err: unknown) => { if (active) setError(err instanceof Error ? err.message : 'Không thể tải lô để gộp.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [lot])

  const loadMore = async () => {
    if (!cursor || loadingMore.current) return
    loadingMore.current = true
    setLoading(true)
    try {
      const page = await getLots({ product_id: lot.product_id ?? undefined, page_size: 100, cursor })
      setCandidates((current) => eligibleMergeCandidates([...current, ...page.items], lot))
      setCursor(page.next_cursor)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải thêm lô.')
    } finally {
      loadingMore.current = false
      setLoading(false)
    }
  }

  // Tiện ích gợi ý chia đều khối lượng khả dụng
  const applyEvenSplit = () => {
    const totalGrams = grams(lot.remaining_quantity) ?? 0n
    if (totalGrams <= 0n || children.length === 0) return
    const base = totalGrams / BigInt(children.length)
    const remainder = totalGrams % BigInt(children.length)
    setChildren((current) =>
      current.map((item, idx) => ({
        ...item,
        quantity: formatGrams(base + (idx === 0 ? remainder : 0n)),
      }))
    )
  }

  // Tiện ích chọn tất cả ứng viên đủ điều kiện gộp
  const selectAllCandidates = () => {
    setQuantities((current) => ({
      ...current,
      ...Object.fromEntries(candidates.map((item) => [item.id, item.remaining_quantity])),
    }))
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy.current) return
    setError(null)
    if (mode === 'split') {
      const values = children.map((child) => grams(child.quantity))
      if (values.some((value) => value === null || value <= 0n) || children.some((child) => !child.name.trim())) {
        setError('Nhập tên và khối lượng lớn hơn 0, tối đa 3 chữ số thập phân.')
        return
      }
      if (values.reduce<bigint>((sum, value) => sum + (value ?? 0n), 0n) > (grams(lot.remaining_quantity) ?? 0n)) {
        setError('Tổng khối lượng con vượt khối lượng còn lại.')
        return
      }
    } else {
      const selected = [lot, ...candidates].filter((item) => !!quantities[item.id])
      if (
        !name.trim() ||
        selected.length < 2 ||
        selected.some((item) => {
          const value = grams(quantities[item.id])
          return value === null || value <= 0n || value > (grams(item.remaining_quantity) ?? 0n)
        })
      ) {
        setError('Chọn ít nhất hai lô; nhập khối lượng hợp lệ trong giới hạn từng lô.')
        return
      }
    }
    busy.current = true
    setSaving(true)
    try {
      if (mode === 'split') {
        const result = await splitLot(
          lot.id,
          children.map((child) => ({ ...child, location_id: child.location_id || null, name: child.name.trim() }))
        )
        setResultLots(result.children)
        onNotify?.(`Tách lô thành công! Đã tạo ${result.children.length} lô con mới.`)
        onSuccess?.(result.children[0])
      } else {
        const result = await mergeLots(
          name.trim(),
          [lot, ...candidates]
            .filter((item) => !!quantities[item.id])
            .map((item) => ({ lot_id: item.id, quantity: quantities[item.id] }))
        )
        setResultLots([result])
        onNotify?.(`Gộp lô thành công! Mã lô mới: ${result.lot_code ?? result.name}`)
        onSuccess?.(result)
      }
      await onTransformed?.()
      if (onClose) {
        onClose()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể xử lý lô.')
    } finally {
      busy.current = false
      setSaving(false)
    }
  }

  if (resultLots.length && !onClose) {
    return (
      <section className="panel-card panel-box" role="status">
        <h2>{mode === 'split' ? 'Đã tách lô thành công' : 'Đã gộp lô thành công'}</h2>
        <p>Các lô mới đã được lưu cùng lịch sử nguồn gốc. Chọn mã lô để kiểm tra.</p>
        <ul className="result-lots">
          {resultLots.map((item) => (
            <li key={item.id}>
              <button className="lot-code-link" type="button" onClick={() => onCompleted(item.id)}>
                {item.lot_code ?? item.id}
              </button>{' '}
              · {item.quantity} {item.product?.unit ?? unit}
            </li>
          ))}
        </ul>
        <a className="ds-button ds-button-secondary" href={`/lots/${lot.id}`}>
          Xem lại lô nguồn
        </a>
      </section>
    )
  }

  return (
    <section className="panel-card panel-box" aria-labelledby="lot-transform-title">
      <h2 id="lot-transform-title">{mode === 'split' ? 'Tách lô' : 'Gộp lô cùng nông sản'}</h2>
      <p className="panel-sub">
        Còn {lot.remaining_quantity} {unit}. Mỗi lô mới được cấp mã riêng và giữ liên kết với tất cả lô nguồn.
      </p>
      <div className="transform-actions">
        <button
          type="button"
          className="ds-button ds-button-secondary"
          aria-pressed={mode === 'split'}
          disabled={saving}
          onClick={() => {
            setMode('split')
            setError(null)
          }}
        >
          Tách lô
        </button>
        <button
          type="button"
          className="ds-button ds-button-secondary"
          aria-pressed={mode === 'merge'}
          disabled={saving}
          onClick={() => {
            setMode('merge')
            setError(null)
          }}
        >
          Gộp cùng sản phẩm
        </button>
      </div>
      {error && <p className="alert-box alert-error" role="alert">{error}</p>}
      <form onSubmit={(event) => void submit(event)}>
        <fieldset disabled={saving} className="transform-fields">
          <legend>{mode === 'split' ? 'Các lô con' : 'Các lô mẹ và phần khối lượng lấy ra'}</legend>
          {mode === 'split' ? (
            <>
              {children.map((child, index) => (
                <div className="transform-row" key={index}>
                  <label>
                    Tên lô con {index + 1}
                    <input
                      required
                      maxLength={200}
                      value={child.name}
                      onChange={(event) =>
                        setChildren((current) =>
                          current.map((item, i) => (i === index ? { ...item, name: event.target.value } : item))
                        )
                      }
                    />
                  </label>
                  <label>
                    Khối lượng con {index + 1} ({unit})
                    <input
                      required
                      inputMode="decimal"
                      value={child.quantity}
                      onChange={(event) =>
                        setChildren((current) =>
                          current.map((item, i) => (i === index ? { ...item, quantity: event.target.value } : item))
                        )
                      }
                      placeholder={`Ví dụ: 10.5 (${unit})`}
                    />
                  </label>
                  {canManageDistribution && (
                    <label className="form-field">
                      Địa điểm lô con {index + 1}
                      <select
                        disabled={locationsLoading}
                        value={child.location_id}
                        onChange={(event) =>
                          setChildren((current) =>
                            current.map((item, i) => (i === index ? { ...item, location_id: event.target.value } : item))
                          )
                        }
                      >
                        <option value="">{locationsLoading ? 'Đang tải…' : 'Chưa gán địa điểm'}</option>
                        {locations.map((location) => (
                          <option key={location.id} value={location.id}>
                            {location.name} · {location.address}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  <button
                    type="button"
                    className="ds-button ds-button-secondary"
                    disabled={children.length === 1}
                    onClick={() => setChildren((current) => current.filter((_, i) => i !== index))}
                  >
                    Bỏ lô con {index + 1}
                  </button>
                </div>
              ))}
              <div className="action-row" style={{ marginTop: '0.25rem', marginBottom: '0.5rem' }}>
                <button type="button" className="ds-button ds-button-secondary ds-button-sm" onClick={applyEvenSplit}>
                  ⚡ Gợi ý chia đều {lot.remaining_quantity} {unit}
                </button>
                <button
                  type="button"
                  className="ds-button ds-button-secondary ds-button-sm"
                  disabled={children.length >= 100}
                  onClick={() =>
                    setChildren((current) => [
                      ...current,
                      {
                        name: `${lot.product?.name ?? 'Nông sản'} — phần ${current.length + 1}`,
                        quantity: '',
                        location_id: '',
                      },
                    ])
                  }
                >
                  Thêm lô con
                </button>
              </div>
            </>
          ) : (
            <>
              <label>
                Tên lô gộp
                <input required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} />
              </label>
              {candidates.length > 0 && (
                <div className="action-row" style={{ margin: '0.25rem 0 0.5rem' }}>
                  <button type="button" className="ds-button ds-button-secondary ds-button-sm" onClick={selectAllCandidates}>
                    ⚡ Chọn tất cả {candidates.length} lô cùng nông sản
                  </button>
                </div>
              )}
              {displayedMergeLots.map((item) => (
                <label key={item.id}>
                  {item.lot_code ?? item.name} · còn {item.remaining_quantity} {item.product?.unit ?? unit}
                  <span>
                    <input
                      type="checkbox"
                      aria-label={`Chọn ${item.lot_code ?? item.name}`}
                      checked={!!quantities[item.id]}
                      onChange={(event) =>
                        setQuantities((current) => ({
                          ...current,
                          [item.id]: event.target.checked ? item.remaining_quantity : '',
                        }))
                      }
                    />{' '}
                    Chọn lô (mặc định lấy toàn bộ phần còn lại)
                  </span>
                  <input
                    inputMode="decimal"
                    value={quantities[item.id] ?? ''}
                    onChange={(event) =>
                      setQuantities((current) => ({ ...current, [item.id]: event.target.value }))
                    }
                    placeholder="Để trống nếu không chọn"
                  />
                </label>
              ))}
              {candidatePages > 1 && (
                <div className="action-row">
                  <span>
                    Lô chưa chọn: trang {currentCandidatePage + 1}/{candidatePages}
                  </span>
                  <button
                    type="button"
                    className="ds-button ds-button-secondary"
                    disabled={currentCandidatePage === 0}
                    onClick={() => setCandidatePage(currentCandidatePage - 1)}
                  >
                    Lô trước
                  </button>
                  <button
                    type="button"
                    className="ds-button ds-button-secondary"
                    disabled={currentCandidatePage === candidatePages - 1}
                    onClick={() => setCandidatePage(currentCandidatePage + 1)}
                  >
                    Lô tiếp
                  </button>
                </div>
              )}
              {cursor && (
                <button
                  type="button"
                  className="ds-button ds-button-secondary"
                  disabled={loading}
                  onClick={() => void loadMore()}
                >
                  {loading ? 'Đang tải…' : 'Tải thêm lô cùng sản phẩm'}
                </button>
              )}
              {loading && <p aria-busy="true">Đang tải lô cùng sản phẩm…</p>}
              {!loading && candidates.length === 0 && (
                <p className="panel-sub">
                  Chưa có lô khác cùng sản phẩm do đơn vị của bạn đang giữ và còn khối lượng.
                </p>
              )}
            </>
          )}
          <p
            className={`mass-summary ${mode === 'split' && summary.remaining < 0n ? 'mass-error' : ''}`}
            role="status"
            aria-live="polite"
          >
            Tổng khối lượng: <strong>{formatGrams(mode === 'split' ? summary.total : mergeTotal)} {unit}</strong>
            {mode === 'split' && (
              <>
                {' '}
                ·{' '}
                {summary.remaining < 0n
                  ? `Vượt ${formatGrams(-summary.remaining)}`
                  : `Lô nguồn sẽ còn ${formatGrams(summary.remaining)}`}{' '}
                {unit}
              </>
            )}
          </p>
          <div className="action-row" style={{ marginTop: '0.75rem', justifyContent: 'flex-end' }}>
            {onClose && (
              <button type="button" className="ds-button ds-button-secondary" onClick={onClose} disabled={saving}>
                Hủy
              </button>
            )}
            <button
              type="submit"
              className="ds-button ds-button-brand"
              disabled={mode === 'split' ? !summary.valid || children.some((child) => !child.name.trim()) : !mergeValid}
            >
              {saving ? 'Đang xử lý…' : mode === 'split' ? 'Xác nhận tách lô' : 'Xác nhận gộp lô'}
            </button>
          </div>
        </fieldset>
      </form>
    </section>
  )
}
