import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { WorkspaceTab } from './FarmWorkspace'
import { Icon } from './Icons'

interface CommandPaletteProps {
  onClose: () => void
  onNavigate: (tab: WorkspaceTab) => void
  onRefresh: () => void
  onToggleTheme: () => void
}

const COMMANDS: Array<{ title: string; detail: string; tab?: WorkspaceTab; action?: 'refresh' | 'theme'; icon: 'trace' | 'atlas' | 'journey' | 'integrity' | 'security' | 'presentation' | 'refresh' | 'sun' }> = [
  { title: 'Trace Command Center', detail: 'Mở sơ đồ hành trình', tab: 'overview', icon: 'trace' },
  { title: 'Farm Atlas', detail: 'Tọa độ và CRUD vùng trồng', tab: 'farms', icon: 'atlas' },
  { title: 'Cold Chain Journey', detail: 'Nhiệt độ, độ ẩm và mốc thời gian', tab: 'journey', icon: 'journey' },
  { title: 'Integrity Forensics', detail: 'SHA-256 và liên kết event', tab: 'integrity', icon: 'integrity' },
  { title: 'Security X-Ray', detail: 'RBAC, tenant và PostgreSQL RLS', tab: 'security', icon: 'security' },
  { title: 'Hướng dẫn khám phá', detail: 'Bắt đầu hướng dẫn bốn chương', tab: 'presentation', icon: 'presentation' },
  { title: 'Làm mới dữ liệu vùng trồng', detail: 'Gọi GET /api/v1/farms/', action: 'refresh', icon: 'refresh' },
  { title: 'Chuyển giao diện sáng / tối', detail: 'Đổi theme hiện tại', action: 'theme', icon: 'sun' },
]

export function CommandPalette({ onClose, onNavigate, onRefresh, onToggleTheme }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const dialogRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef(COMMANDS)
  const activeIndexRef = useRef(activeIndex)

  const results = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase()
    if (!normalized) return COMMANDS
    return COMMANDS.filter((command) => `${command.title} ${command.detail}`.toLocaleLowerCase().includes(normalized))
  }, [query])

  const execute = useCallback((command: (typeof COMMANDS)[number]) => {
    if (command.tab) onNavigate(command.tab)
    if (command.action === 'refresh') onRefresh()
    if (command.action === 'theme') onToggleTheme()
    onClose()
  }, [onClose, onNavigate, onRefresh, onToggleTheme])

  useEffect(() => {
    resultsRef.current = results
    activeIndexRef.current = activeIndex
  }, [activeIndex, results])

  useEffect(() => {
    const shell = document.querySelector<HTMLElement>('.workspace-shell')
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    if (shell) shell.inert = true
    document.body.style.overflow = 'hidden'
    inputRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setActiveIndex((index) => Math.min(index + 1, Math.max(0, resultsRef.current.length - 1)))
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setActiveIndex((index) => Math.max(0, index - 1))
      }
      if (event.key === 'Enter' && event.target === inputRef.current && resultsRef.current[activeIndexRef.current]) {
        event.preventDefault()
        execute(resultsRef.current[activeIndexRef.current])
      }
      if (event.key === 'Tab' && dialogRef.current) {
        const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>('input:not([tabindex="-1"]), button:not(:disabled):not([tabindex="-1"])'))
        if (focusable.length) {
          const first = focusable[0]
          const last = focusable[focusable.length - 1]
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
          else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
        }
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      if (shell) shell.inert = false
      if (previousFocus?.isConnected && previousFocus !== document.body) previousFocus.focus()
      else { const heading = shell?.querySelector<HTMLElement>('main h1'); heading?.setAttribute('tabindex', '-1'); heading?.focus({ preventScroll: true }) }
    }
  }, [execute, onClose])

  return (
    <div className="palette-layer">
      <button type="button" tabIndex={-1} className="palette-backdrop" aria-label="Đóng command palette" onClick={onClose} />
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-label="Command palette" className="command-palette">
        <label className="palette-search"><Icon name="search" size={19} /><input ref={inputRef} type="search" role="combobox" aria-autocomplete="list" aria-controls={results.length ? 'command-results' : undefined} aria-expanded={results.length > 0} aria-activedescendant={results[activeIndex] ? `command-option-${activeIndex}` : undefined} value={query} onChange={(event) => { setQuery(event.target.value); setActiveIndex(0) }} placeholder="Đi tới một phân hệ hoặc hành động…" aria-label="Tìm lệnh" /><button type="button" onClick={onClose} aria-label="Đóng"><kbd>ESC</kbd></button></label>
        <p className="palette-section-label">PHÂN HỆ / HÀNH ĐỘNG</p>
        {results.length ? <ul className="palette-results" id="command-results" role="listbox" aria-label="Kết quả lệnh">{results.map((command, index) => <li key={command.title}><button id={`command-option-${index}`} type="button" role="option" aria-selected={activeIndex === index} tabIndex={-1} className={activeIndex === index ? 'palette-result palette-result-active' : 'palette-result'} onMouseEnter={() => setActiveIndex(index)} onClick={() => execute(command)}><span className="palette-icon"><Icon name={command.icon} size={17} /></span><span><strong>{command.title}</strong><small>{command.detail}</small></span><kbd>{command.tab ? '↵' : 'RUN'}</kbd></button></li>)}</ul> : <p className="palette-empty">Không có lệnh phù hợp.</p>}
        <div className="palette-footer"><span>↑ ↓ chọn</span><span>Enter mở</span><span>Esc đóng</span><span className="palette-shortcut">⌘ K</span></div>
      </div>
    </div>
  )
}
