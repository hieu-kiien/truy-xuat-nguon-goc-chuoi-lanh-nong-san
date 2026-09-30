import { useEffect, useState } from 'react'
import { getLots } from '../services/api'
import type { Lot } from '../types'

interface LotsPanelProps {
  canReadLots: boolean
}

export function LotsPanel({ canReadLots }: LotsPanelProps) {
  const [lots, setLots] = useState<Lot[]>([])
  const [loading, setLoading] = useState(canReadLots)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      setLots(await getLots())
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Không thể tải danh sách lô'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!canReadLots) return
    let active = true

    getLots()
      .then((data) => {
        if (active) setLots(data)
      })
      .catch((err: unknown) => {
        if (active) {
          setError(
            err instanceof Error ? err.message : 'Không thể tải danh sách lô'
          )
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [canReadLots])

  if (!canReadLots) {
    return (
      <section className="sticker-panel panel-box" role="status">
        Tài khoản này không có quyền xem danh sách lô.
      </section>
    )
  }

  return (
    <section
      className="data-table-wrapper sticker-panel"
      aria-labelledby="lots-table-title"
    >
      <div className="data-table-header">
        <div>
          <h2 id="lots-table-title" className="section-title">
            Danh sách lô ({lots.length})
          </h2>
          <p className="panel-sub">
            Dữ liệu được lọc theo tổ chức ở API và PostgreSQL RLS.
          </p>
        </div>
        <button
          type="button"
          className="ds-button ds-button-secondary ds-button-sm"
          onClick={() => void refresh()}
          disabled={loading}
        >
          {loading ? 'Đang tải...' : 'Làm mới'}
        </button>
      </div>

      {error && (
        <div className="alert-box alert-error table-alert" role="alert">
          {error}
        </div>
      )}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Mã lô</th>
              <th scope="col">Tên lô</th>
              <th scope="col">Tổ chức</th>
              <th scope="col">Mã thửa đất</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={4} className="cell-center" aria-busy="true">
                  Đang tải danh sách lô...
                </td>
              </tr>
            ) : lots.length === 0 ? (
              <tr>
                <td colSpan={4} className="cell-center">
                  Tổ chức chưa có lô nào được khai báo.
                </td>
              </tr>
            ) : (
              lots.map((lot) => (
                <tr key={lot.id}>
                  <td>
                    <code title={lot.id}>{lot.id}</code>
                  </td>
                  <th scope="row" className="cell-strong">
                    {lot.name}
                  </th>
                  <td>
                    <code title={lot.organization_id}>
                      {lot.organization_id}
                    </code>
                  </td>
                  <td>
                    <code title={lot.farm_id}>{lot.farm_id}</code>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
