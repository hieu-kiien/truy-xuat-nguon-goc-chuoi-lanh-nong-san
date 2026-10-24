import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { PublicRoute } from '../types'

interface RouteMapProps {
  route: PublicRoute | null
  lotCode: string
}

function createPinDataUri(fillColor: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="42" viewBox="0 0 30 42" fill="none"><path d="M15 1.5C7.544 1.5 1.5 7.544 1.5 15c0 9.65 11.45 23.16 12.66 24.55a1.12 1.12 0 0 0 1.68 0C17.05 38.16 28.5 24.65 28.5 15c0-7.456-6.044-13.5-13.5-13.5Z" fill="${fillColor}" stroke="#ffffff" stroke-width="2.2"/><circle cx="15" cy="15" r="5.5" fill="#ffffff"/></svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

const ORIGIN_MARKER_ICON = L.icon({
  iconUrl: createPinDataUri('#15803d'),
  iconRetinaUrl: createPinDataUri('#15803d'),
  iconSize: [30, 42],
  iconAnchor: [15, 40],
  popupAnchor: [0, -36],
})

const STOP_MARKER_ICON = L.icon({
  iconUrl: createPinDataUri('#c85a32'),
  iconRetinaUrl: createPinDataUri('#c85a32'),
  iconSize: [30, 42],
  iconAnchor: [15, 40],
  popupAnchor: [0, -36],
})

export function RouteMap({ route, lotCode }: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)

  useEffect(() => {
    if (!containerRef.current || !route || route.points.length === 0) return

    const map = L.map(containerRef.current, { scrollWheelZoom: false })
    mapRef.current = map
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
      subdomains: ['a', 'b', 'c'],
      maxZoom: 18,
    }).addTo(map)

    const points = route.points
    const latlngs = points.map((point) => [point.latitude, point.longitude] as [number, number])

    points.forEach((point, index) => {
      const isOrigin = point.kind === 'origin'
      L.marker(latlngs[index], {
        icon: isOrigin ? ORIGIN_MARKER_ICON : STOP_MARKER_ICON,
        title: point.name,
        alt: point.name,
      })
        .addTo(map)
        .bindPopup(
          `<strong>${isOrigin ? 'Vùng trồng xuất phát' : 'Điểm dừng'}</strong><br/>${point.name}`,
        )
    })

    if (latlngs.length > 1) {
      L.polyline(latlngs, { color: '#15803d', weight: 3, dashArray: '6 6' }).addTo(map)
      map.fitBounds(L.latLngBounds(latlngs).pad(0.25))
    } else {
      map.setView(latlngs[0], 11)
    }

    const resizeTimer = window.setTimeout(() => {
      map.invalidateSize()
    }, 120)

    return () => {
      window.clearTimeout(resizeTimer)
      map.remove()
      mapRef.current = null
    }
  }, [route])

  if (!route || route.points.length === 0) {
    return null
  }

  return (
    <section className="panel-card panel-box route-map-card" aria-label={`Bản đồ hành trình của lô ${lotCode}`}>
      <header className="panel-head">
        <div>
          <h2>Bản đồ hành trình</h2>
          <p className="panel-sub">{route.precision_note}</p>
        </div>
      </header>
      <div ref={containerRef} className="route-map" role="img" aria-label="Bản đồ các điểm dừng của hành trình" />
      <ol className="route-map-points">
        {route.points.map((point, index) => (
          <li key={`${index}-${point.order}-${point.name}`}>
            <strong>{point.kind === 'origin' ? 'Vùng trồng xuất phát' : 'Điểm dừng'}</strong> · {point.name}
          </li>
        ))}
      </ol>
    </section>
  )
}
