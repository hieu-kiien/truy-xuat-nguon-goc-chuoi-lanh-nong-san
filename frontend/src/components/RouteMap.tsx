import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { PublicRoute } from '../types'

interface RouteMapProps {
  route: PublicRoute | null
  lotCode: string
}

export function RouteMap({ route, lotCode }: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)

  useEffect(() => {
    if (!containerRef.current || !route || route.points.length === 0) return

    const map = L.map(containerRef.current, { scrollWheelZoom: false })
    mapRef.current = map
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
      maxZoom: 18,
    }).addTo(map)

    const points = route.points
    const latlngs = points.map((point) => [point.latitude, point.longitude] as [number, number])

    points.forEach((point, index) => {
      const isOrigin = point.kind === 'origin'
      L.marker(latlngs[index], {
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

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [route])

  if (!route || route.points.length === 0) {
    return null
  }

  return (
    <section className="panel-card panel-box" aria-label={`Bản đồ hành trình của lô ${lotCode}`}>
      <header className="panel-head">
        <div>
          <h2>Bản đồ hành trình</h2>
          <p className="panel-sub">{route.precision_note}</p>
        </div>
      </header>
      <div ref={containerRef} className="route-map" role="img" aria-label="Bản đồ các điểm dừng của hành trình" />
      <ol className="route-map-points">
        {route.points.map((point) => (
          <li key={`${point.order}-${point.name}`}>
            <strong>{point.kind === 'origin' ? 'Vùng trồng xuất phát' : 'Điểm dừng'}</strong> · {point.name}
          </li>
        ))}
      </ol>
    </section>
  )
}
