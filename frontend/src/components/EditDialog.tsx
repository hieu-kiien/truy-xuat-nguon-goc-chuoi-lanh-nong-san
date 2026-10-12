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
  return <dialog ref={ref} className="edit-dialog" aria-label={title} aria-busy={busy}
    onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
    <div className="edit-dialog-header"><h2>{title}</h2>
      <button type="button" className="ds-button ds-button-secondary" disabled={busy} onClick={onClose} aria-label="Đóng hộp thoại">Đóng</button>
    </div>
    {children}
  </dialog>
}
