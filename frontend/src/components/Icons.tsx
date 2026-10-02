import type { SVGProps } from 'react'

export type IconName =
  | 'agro'
  | 'trace'
  | 'atlas'
  | 'journey'
  | 'integrity'
  | 'security'
  | 'presentation'
  | 'search'
  | 'refresh'
  | 'sun'
  | 'moon'
  | 'logout'
  | 'arrow'
  | 'pin'
  | 'thermometer'
  | 'shield'
  | 'check'
  | 'plus'
  | 'close'
  | 'play'
  | 'pause'
  | 'layers'
  | 'list'
  | 'compare'
  | 'chevron'
  | 'clock'
  | 'truck'
  | 'zoom-in'
  | 'zoom-out'

const PATHS: Record<IconName, string> = {
  agro: 'M4 20c0-8 4-13 16-16-1 10-5 16-13 16m-1 0c3-6 6-9 12-13',
  trace: 'M4 18c4-9 7-9 10-4s5 5 8-4M3 18h3m12-8h4',
  atlas: 'M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3zm6-3v15m6-12v15',
  journey: 'M5 4v16m0-14h12l-3 4 3 4H5m0 6h14',
  integrity: 'M12 3l8 4v5c0 5-3.4 8-8 10-4.6-2-8-5-8-10V7zm-3 9l2 2 4-5',
  security: 'M12 3l8 4v5c0 5-3.4 8-8 10-4.6-2-8-5-8-10V7zm-3 9l2 2 4-5',
  presentation: 'M4 4h16v12H4zm8 12v4m-4 0h8m-11-9h4l2-3 2 5 2-3h2',
  search: 'M10.8 18.2a7.4 7.4 0 1 1 0-14.8 7.4 7.4 0 0 1 0 14.8zm5.2-2 5 5',
  refresh: 'M20 7v5h-5M4 17v-5h5m-4 0a7 7 0 0 1 12-4l3 4m-16 0 3 4a7 7 0 0 0 12-4',
  sun: 'M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6L7 7m10 10 1.4 1.4m0-12.8L17 7M7 17l-1.4 1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z',
  moon: 'M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5 8.6 8.6 0 1 0 20.5 14.5z',
  logout: 'M10 4H5v16h5m4-4 4-4-4-4m4 4H9',
  arrow: 'M4 12h15m-6-6 6 6-6 6',
  pin: 'M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0zm-4 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
  thermometer: 'M14 14.8V5a3 3 0 0 0-6 0v9.8a5 5 0 1 0 6 0zM11 6v10m0 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4z',
  shield: 'M12 3l8 4v5c0 5-3.4 8-8 10-4.6-2-8-5-8-10V7zm-3 9l2 2 4-5',
  check: 'M5 12l4 4L19 6',
  plus: 'M12 5v14m-7-7h14',
  close: 'M6 6l12 12M18 6 6 18',
  play: 'M8 5l11 7-11 7z',
  pause: 'M8 5v14m8-14v14',
  layers: 'M12 3L3 8l9 5 9-5zm-9 9 9 5 9-5m-18 5 9 5 9-5',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  compare: 'M4 5h7v14H4zm9 0h7v14h-7zM7 9h1m8 0h1M7 13h1m8 0h1',
  chevron: 'M6 9l6 6 6-6',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zm0-16v6l4 2',
  truck: 'M3 5h11v12H3zm11 5h4l3 4v3h-7M6 21a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm12 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  'zoom-in': 'M10 17a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm5-2 6 6M7 10h6m-3-3v6',
  'zoom-out': 'M10 17a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm5-2 6 6M7 10h6',
}

interface IconProps extends SVGProps<SVGSVGElement> {
  name: IconName
  size?: number
}

export function Icon({ name, size = 18, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
