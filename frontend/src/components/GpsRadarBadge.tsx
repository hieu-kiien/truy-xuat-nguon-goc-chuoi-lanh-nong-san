import { useState } from 'react'

interface GpsRadarBadgeProps {
  latitude: string | number
  longitude: string | number
  farmName?: string
}

export function GpsRadarBadge({ latitude, longitude, farmName }: GpsRadarBadgeProps) {
  const [active, setActive] = useState(false)
  const mapUrl = `https://www.google.com/maps?q=${latitude},${longitude}`

  return (
    <div
      className={`gps-radar-badge ${active ? 'radar-active' : ''}`}
      onMouseEnter={() => setActive(true)}
      onMouseLeave={() => setActive(false)}
      onFocus={() => setActive(true)}
      onBlur={() => setActive(false)}
    >
      <div className="radar-sonar-emitter" aria-hidden="true">
        <span className="radar-core-dot" />
        <span className="radar-ping-ring ring-1" />
        <span className="radar-ping-ring ring-2" />
      </div>

      <code className="gps-coord-value" title={`Tọa độ WGS84: ${latitude}, ${longitude}`}>
        {latitude}, {longitude}
      </code>

      <a
        href={mapUrl}
        target="_blank"
        rel="noreferrer"
        className="gps-map-action"
        title={`Mở vị trí ${farmName || 'thửa đất'} trên Google Maps vệ tinh`}
        aria-label={`Xem bản đồ vệ tinh cho tọa độ ${latitude}, ${longitude}`}
      >
        <span className="map-icon" aria-hidden="true">🗺️</span>
        <span>Bản đồ</span>
      </a>
    </div>
  )
}
