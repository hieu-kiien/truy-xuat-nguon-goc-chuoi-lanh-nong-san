import type { FormEvent } from 'react'
import type { Farm } from '../types'

interface FarmFormPanelProps {
  canWriteFarms: boolean
  editingFarm: Farm | null
  name: string
  areaHa: string
  latitude: string
  longitude: string
  saving: boolean
  formFeedback: { type: 'success' | 'error'; message: string } | null
  onNameChange: (value: string) => void
  onAreaChange: (value: string) => void
  onLatChange: (value: string) => void
  onLngChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onCancelEdit: () => void
}

export function FarmFormPanel({
  canWriteFarms,
  editingFarm,
  name,
  areaHa,
  latitude,
  longitude,
  saving,
  formFeedback,
  onNameChange,
  onAreaChange,
  onLatChange,
  onLngChange,
  onSubmit,
  onCancelEdit,
}: FarmFormPanelProps) {
  if (!canWriteFarms) return null

  return (
    <section className="panel-box panel-card" aria-labelledby="form-title">
          <div className="panel-head">
            <h2 id="form-title">
              {editingFarm
                ? 'Cập nhật Vùng trồng'
                : 'Thêm vùng trồng'}
            </h2>
            {editingFarm && (
              <code title={editingFarm.id}>
                ID: {editingFarm.id.slice(0, 8)}...
              </code>
            )}
          </div>

          {formFeedback && (
            <div
              className={`alert-box ${
                formFeedback.type === 'success'
                  ? 'alert-success'
                  : 'alert-error'
              }`}
              role="status"
            >
              {formFeedback.message}
            </div>
          )}

          <form onSubmit={onSubmit} className="form-stack">
            <div className="form-row-2">
              <div className="form-field">
                <label htmlFor="farm-name">
                  Tên vùng trồng / thửa đất{' '}
                  <span className="required-mark">*</span>
                </label>
                <input
                  id="farm-name"
                  type="text"
                  required
                  maxLength={200}
                  value={name}
                  onChange={(e) => onNameChange(e.target.value)}
                  placeholder="VD: Khu nhà kính Dâu tây A1"
                />
              </div>

              <div className="form-field">
                <label htmlFor="farm-area">
                  Diện tích (ha &gt; 0){' '}
                  <span className="required-mark">*</span>
                </label>
                <input
                  id="farm-area"
                  type="number"
                  step="0.0001"
                  min="0.0001"
                  required
                  value={areaHa}
                  onChange={(e) => onAreaChange(e.target.value)}
                  placeholder="VD: 2.4500"
                />
              </div>
            </div>

            <div className="form-row-2">
              <div className="form-field">
                <label htmlFor="farm-lat">
                  Vĩ độ (-90..90) <span className="required-mark">*</span>
                </label>
                <input
                  id="farm-lat"
                  type="number"
                  step="0.000001"
                  min="-90"
                  max="90"
                  required
                  value={latitude}
                  onChange={(e) => onLatChange(e.target.value)}
                  placeholder="11.862450"
                />
              </div>

              <div className="form-field">
                <label htmlFor="farm-lng">
                  Kinh độ (-180..180) <span className="required-mark">*</span>
                </label>
                <input
                  id="farm-lng"
                  type="number"
                  step="0.000001"
                  min="-180"
                  max="180"
                  required
                  value={longitude}
                  onChange={(e) => onLngChange(e.target.value)}
                  placeholder="108.538120"
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
                  : editingFarm
                    ? 'Lưu cập nhật'
                    : 'Thêm vùng trồng'}
              </button>
              {editingFarm && (
                <button
                  type="button"
                  className="ds-button ds-button-secondary ds-button-sm"
                  onClick={onCancelEdit}
                >
                  Hủy
                </button>
              )}
            </div>
          </form>
    </section>
  )
}
