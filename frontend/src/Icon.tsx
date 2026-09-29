import type { ReactNode } from 'react'

type IconName =
  | 'sprout'
  | 'leaf'
  | 'package'
  | 'pin'
  | 'plus'
  | 'edit'
  | 'lock'
  | 'eye'
  | 'eyeOff'

const paths: Record<IconName, ReactNode> = {
  sprout: (
    <>
      <path d="M12 21v-9" />
      <path d="M12 12c-4.5 0-7-2.5-7-7 4.5 0 7 2.2 7 7Z" />
      <path d="M12 14c0-4.5 2.5-7 7-7 0 4.5-2.5 7-7 7Z" />
    </>
  ),
  leaf: (
    <>
      <path d="M20 4c-9 0-14 4-14 11a5 5 0 0 0 5 5c7 0 11-5 9-16Z" />
      <path d="M4 21c3-5 7-8 12-11" />
    </>
  ),
  package: (
    <>
      <path d="m3.5 7 8.5-4 8.5 4-8.5 4-8.5-4Z" />
      <path d="M3.5 7v10l8.5 4 8.5-4V7M12 11v10" />
      <path d="m7.5 5.2 8.5 4" />
    </>
  ),
  pin: (
    <>
      <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  edit: <path d="m15 5 4 4M4 20l4.5-.9L19 8.6a2.1 2.1 0 0 0-3-3L5.5 16.1 4 20Z" />,
  lock: (
    <>
      <rect x="4" y="10" width="16" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  eyeOff: (
    <>
      <path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8" />
      <path d="M9.9 5.2A10.6 10.6 0 0 1 12 5c6.4 0 10 7 10 7a16.6 16.6 0 0 1-3.1 3.8M6.2 6.2C3.5 8.1 2 12 2 12s3.6 7 10 7a10 10 0 0 0 3.1-.5" />
    </>
  ),
}

export default function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  )
}
