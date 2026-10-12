import type { ReactNode } from 'react'

/** Navigate within the current tab for task pages. Editing uses EditDialog. */
export function TaskLink({ href, children, secondary = false }: { href: string; children: ReactNode; secondary?: boolean }) {
  return <a href={href} className={`ds-button ${secondary ? 'ds-button-secondary' : 'ds-button-brand'}`}>
    {children}
  </a>
}
