import type { FormEvent } from 'react'
import type { Farm } from '../types'

interface PresetLocation {
  label: string
  name: string
  area_ha: string
  latitude: string
  longitude: string
}

const PRESET_LOCATIONS: PresetLocation[] = [
  {
    label: 'Mẫu Đà Lạt',
    name: 'Phân khu Rau hữu cơ Trại Mát',
    area_ha: '3.2500',
    latitude: '11.924850',
    longitude: '108.497210',
  },
  {
    label: 'Mẫu Mộc Châu',
    name: 'Đồi Dâu tây Bản Áng Khu B',
    area_ha: '4.5000',
    latitude: '20.828640',
    longitude: '104.661520',
  },
  {
    label: 'Mẫu Tiền Giang',
    name: 'Vùng trồng Xoài Cát Hòa Lộc Cái Bè',
    area_ha: '6.1000',
    latitude: '10.334910',
    longitude: '106.028450',
  },
]

interface FarmFormPanelProps {
  canReadFarms: boolean
  canWriteFarms: boolean
  farms: Farm[]
  totalAreaHa: number
  maxAreaHa: number
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
  onApplyPreset: (preset: PresetLocation) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onCancelEdit: () => void
  onNotify: (message: string) => void
}

export function FarmFormPanel({
  canReadFarms,
  canWriteFarms,
  farms,
  totalAreaHa,
  maxAreaHa,
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
  onApplyPreset,
  onSubmit,
  onCancelEdit,
  onNotify,
}: FarmFormPanelProps) {
  return (
    <div className="info-stack">
      {canWriteFarms && (
        <section className="panel-box panel-card" aria-labelledby="form-title">
          <div className="panel-head">
            <h2 id="form-title">
              {editingFarm
                ? 'Cập nhật Vùng trồng'
                : 'Khai báo Vùng trồng mới (N3-7)'}
            </h2>
            {editingFarm && (
              <code title={editingFarm.id}>
                ID: {editingFarm.id.slice(0, 8)}...
              </code>
            )}
          </div>

          {!editingFarm && (
            <div className="preset-strip">
              <span className="preset-label">Mẫu nhanh:</span>
              {PRESET_LOCATIONS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className="ds-button ds-button-secondary ds-button-xs"
                  onClick={() => onApplyPreset(preset)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          )}

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
      )}

      {canReadFarms && farms.length > 0 && (
        <section className="panel-box panel-card" aria-labelledby="chart-title">
          <div className="panel-head">
            <h2 id="chart-title">Tương quan diện tích các lô (ha)</h2>
            <span className="panel-sub">Tổng: {totalAreaHa.toFixed(2)} ha</span>
          </div>

          <div
            className="chart-bars"
            role="group"
            aria-label="Biểu đồ diện tích các vùng trồng. Có thể chọn từng cột để xem chi tiết."
          >
            {farms.map((farm, idx) => {
              const area = Number(farm.area_ha) || 0
              const heightPct = Math.max(
                18,
                Math.min(100, (area / maxAreaHa) * 100)
              )
              return (
                <div key={farm.id} className="chart-bar-col">
                  <span className="chart-bar-value">{area.toFixed(1)}</span>
                  <button
                    type="button"
                    className="chart-bar"
                    style={{ height: `${heightPct}%` }}
                    title={`${farm.name}: ${area.toFixed(2)} ha`}
                    aria-label={`${farm.name}: ${area.toFixed(2)} hecta`}
                    onClick={() =>
                      onNotify(
                        `${farm.name} — Diện tích: ${area.toFixed(2)} ha`
                      )
                    }
                  />
                  <span className="chart-bar-caption">Lô #{idx + 1}</span>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
