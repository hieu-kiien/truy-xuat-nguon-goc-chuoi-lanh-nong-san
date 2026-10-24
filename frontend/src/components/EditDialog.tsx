import { useEffect, useRef, type ReactNode } from 'react'

export function EditDialog({ title, children, onClose, busy = false }: {
  title: string; children: ReactNode; onClose: () => void; busy?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const dialog = ref.current
    dialog?.showModal()
    return () => { dialog?.close(); previous?.focus() }
  }, [])
  const handleKeyDown = (event: React.KeyboardEvent<HTMLDialogElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      if (!busy) onClose()
      return
    }
    if (event.key === 'Tab') {
      const dialog = ref.current
      if (!dialog) return
      const focusable = dialog.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }

  return <dialog ref={ref} className="edit-dialog" aria-label={title} aria-labelledby="dialog-heading" aria-busy={busy}
    onKeyDown={handleKeyDown}
    onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
    <div className="edit-dialog-header"><h2 id="dialog-heading">{title}</h2>
      <button type="button" className="ds-button ds-button-secondary" disabled={busy} onClick={onClose} aria-label="Đóng hộp thoại">Đóng</button>
    </div>
    {children}
  </dialog>
}
