import type { MouseEvent, ReactNode } from 'react'

/** Navigate within the current tab for task pages. Editing uses EditDialog. */
export function TaskLink({ href, children, secondary = false }: { href: string; children: ReactNode; secondary?: boolean }) {
  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      !href.startsWith('/')
    ) {
      return
    }
    event.preventDefault()
    window.history.pushState(null, '', href)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  return <a href={href} onClick={handleClick} className={`ds-button ${secondary ? 'ds-button-secondary' : 'ds-button-brand'}`}>
    {children}
  </a>
}
