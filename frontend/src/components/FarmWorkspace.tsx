import { useCallback, useEffect, useMemo, useState, useRef } from 'react'
import { flushSync } from 'react-dom'
import { inspectJourney, stageProgress } from '../domain/journeyModel'
import { JourneyLens } from './JourneyLens'
import { createFarm, getFarms, login, updateFarm, ApiError, DEMO_LOGIN_ENABLED } from '../services/api'
import { calculateDemoHashChain, DEMO_CHAPTERS, type DemoHashBlock } from '../domain/demoScenario'
import { DEMO_ACCOUNTS, hasPermission, ROLE_LABELS, type DemoAccount, type Farm, type FarmPayload, type SessionUser } from '../types'
import { CommandPalette } from './CommandPalette'
import { ColdChainJourney } from './ColdChainJourney'
import { DemoGuide } from './DemoGuide'
import { FarmAtlas } from './FarmAtlas'
import { Icon, type IconName } from './Icons'
import { IntegrityLab } from './IntegrityLab'
import { PresentationMode } from './PresentationMode'
import { SecurityXray, type AccessProbeState } from './SecurityXray'
import { TraceCommandCenter } from './TraceCommandCenter'

export type WorkspaceTab = 'overview' | 'farms' | 'journey' | 'integrity' | 'security' | 'presentation'

interface FarmWorkspaceProps {
  user: SessionUser
  backendOnline: boolean | null
  activeTab: WorkspaceTab
  isDark: boolean
  onToggleTheme: () => void
  onTabChange: (tab: WorkspaceTab) => void
  onSwitchUser: (user: SessionUser) => void
  onLogout: () => void
  onNotify: (message: string) => void
}

const NAV_ITEMS: Array<{ id: WorkspaceTab; label: string; compact: string; icon: IconName }> = [
  { id: 'overview', label: 'Trace', compact: 'Trace', icon: 'trace' },
  { id: 'farms', label: 'Farm Atlas', compact: 'Atlas', icon: 'atlas' },
  { id: 'journey', label: 'Cold Chain', compact: 'Journey', icon: 'journey' },
  { id: 'integrity', label: 'Forensics', compact: 'Integrity', icon: 'integrity' },
  { id: 'security', label: 'Security X-Ray', compact: 'Security', icon: 'security' },
  { id: 'presentation', label: 'Demo mode', compact: 'Guide', icon: 'presentation' },
]

const PAGE_LABELS: Record<WorkspaceTab, { eyebrow: string; title: string }> = {
  overview: { eyebrow: 'MISSION CONTROL', title: 'Trace Command Center' },
  farms: { eyebrow: 'SPATIAL REGISTER', title: 'Farm Atlas' },
  journey: { eyebrow: 'COLD CHAIN TELEMETRY', title: 'Cold Chain Journey' },
  integrity: { eyebrow: 'DATA INTEGRITY', title: 'Integrity Forensics Lab' },
  security: { eyebrow: 'REQUEST INSPECTOR', title: 'Security X-Ray' },
  presentation: { eyebrow: 'PRESENTATION MODE', title: 'Field Guide' },
}

export function FarmWorkspace({
  user,
  backendOnline,
  activeTab,
  isDark,
  onToggleTheme,
  onTabChange,
  onSwitchUser,
  onLogout,
  onNotify,
}: FarmWorkspaceProps) {
  const canReadFarms = hasPermission(user.role, 'farms:read')
  const canWriteFarms = hasPermission(user.role, 'farms:write')
  const [farms, setFarms] = useState<Farm[]>([])
  const [loadingFarms, setLoadingFarms] = useState(canReadFarms)
  const [farmError, setFarmError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [journeyProgress, setJourneyProgress] = useState(0)
  const focusedTabRef = useRef<WorkspaceTab | null>(null)
  const mainRef = useRef<HTMLElement>(null)
  const transitionRef = useRef<ViewTransition | null>(null)
  const setSelectedStage = useCallback((index: number) => setJourneyProgress(stageProgress(Math.max(0, Math.min(3, index)))), [])
  const [temperatureExcursion, setTemperatureExcursion] = useState(false)
  const [tampered, setTampered] = useState(false)
  const [chainResult, setChainResult] = useState<{ key: string; blocks: DemoHashBlock[]; error: string | null } | null>(null)
  const [probe, setProbe] = useState<AccessProbeState>({ status: 'idle' })
  const [switchingAccount, setSwitchingAccount] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const [guideChapter, setGuideChapter] = useState(0)
  const [paletteOpen, setPaletteOpen] = useState(false)

  const refreshFarms = useCallback(async () => {
    if (!canReadFarms) {
      setFarms([])
      setLoadingFarms(false)
      return
    }
    setLoadingFarms(true)
    setFarmError(null)
    try {
      setFarms(await getFarms())
    } catch (err) {
      setFarmError(err instanceof Error ? err.message : 'Không thể tải danh sách vùng trồng.')
    } finally {
      setLoadingFarms(false)
    }
  }, [canReadFarms])

  const refreshNow = useCallback(() => { void refreshFarms() }, [refreshFarms])
  const closePalette = useCallback(() => setPaletteOpen(false), [])
  const closeGuide = useCallback(() => setGuideOpen(false), [])
  const toggleTamper = useCallback(() => setTampered((current) => !current), [])
  const toggleExcursion = useCallback(() => setTemperatureExcursion((current) => !current), [])

  useEffect(() => {
    void Promise.resolve().then(refreshFarms)
  }, [refreshFarms])

  useEffect(() => {
    let current = true
    const key = `${tampered}:${temperatureExcursion}`
    void calculateDemoHashChain({ tampered, temperatureExcursion })
      .then((blocks) => { if (current) setChainResult({ key, blocks, error: null }) })
      .catch((err: unknown) => { if (current) setChainResult({ key, blocks: [], error: err instanceof Error ? err.message : 'Không thể tính SHA-256.' }) })
    return () => { current = false }
  }, [tampered, temperatureExcursion])

  const selectedStage = inspectJourney(journeyProgress, temperatureExcursion).nearest

  const navigate = useCallback((tab: WorkspaceTab) => {
    if (tab === activeTab) return
    transitionRef.current?.skipTransition()
    if (typeof document.startViewTransition === 'function' && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const transition = document.startViewTransition(() => flushSync(() => onTabChange(tab)))
      transitionRef.current = transition
      void transition.ready.catch(() => {})
      void transition.finished.finally(() => { if (transitionRef.current === transition) transitionRef.current = null }).catch(() => {})
    } else onTabChange(tab)
  }, [activeTab, onTabChange])

  useEffect(() => {
    if (focusedTabRef.current === activeTab) return
    focusedTabRef.current = activeTab
    if (guideOpen || paletteOpen) return
    const frame = requestAnimationFrame(() => {
      const heading = mainRef.current?.querySelector('h1')
      heading?.setAttribute('tabindex', '-1')
      heading?.focus({ preventScroll: true })
    })
    return () => cancelAnimationFrame(frame)
  }, [activeTab, guideOpen, paletteOpen])

  useEffect(() => () => transitionRef.current?.skipTransition(), [])

  const chainKey = `${tampered}:${temperatureExcursion}`
  const chain = chainResult?.key === chainKey ? chainResult.blocks : []
  const chainError = chainResult?.key === chainKey ? chainResult.error : null

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen(true)
      }
    }
    document.addEventListener('keydown', handleShortcut)
    return () => document.removeEventListener('keydown', handleShortcut)
  }, [])

  const saveFarm = useCallback(async (id: string | null, payload: FarmPayload): Promise<Farm> => {
    if (!canWriteFarms) throw new ApiError(403, 'Vai trò hiện tại không có quyền farms:write.')
    const saved = id ? await updateFarm(id, payload) : await createFarm(payload)
    setFarms((current) => id ? current.map((farm) => farm.id === saved.id ? saved : farm) : [...current, saved])
    await onNotify(id ? `Đã cập nhật ${saved.name}` : `Đã thêm vùng trồng ${saved.name}`)
    return saved
  }, [canWriteFarms, onNotify])

  const runProbe = useCallback(async () => {
    setProbe({ status: 'pending' })
    try {
      const visible = await getFarms()
      setProbe({ status: 'allowed', httpStatus: 200, visibleRows: visible.length, records: visible.map(({ id, name, organization_id }) => ({ id, name, organization_id })) })
      onNotify(`GET /api/v1/farms/ trả 200 OK · ${visible.length} bản ghi tenant-visible`)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setProbe({ status: 'blocked', httpStatus: 403, message: err.message })
        onNotify('GET /api/v1/farms/ bị chặn tại RBAC (403)')
      } else if (err instanceof ApiError && err.status === 401) {
        setProbe({ status: 'unauthenticated', httpStatus: 401, message: err.message })
        onNotify('Phiên đăng nhập đã hết hạn (401)')
      } else {
        const message = err instanceof Error ? err.message : 'Request thất bại.'
        setProbe({ status: 'error', httpStatus: err instanceof ApiError ? err.status : null, message })
      }
    }
  }, [onNotify])

  const switchDemoAccount = async (account: DemoAccount) => {
    if (!DEMO_LOGIN_ENABLED || switchingAccount || account.email === user.email) return
    setSwitchingAccount(true)
    try {
      const nextUser = await login({ email: account.email })
      onNotify(`Đã chuyển phiên sang ${nextUser.organization_name}`)
      onSwitchUser(nextUser)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Không thể đổi tài khoản demo.')
    } finally {
      setSwitchingAccount(false)
    }
  }

  const selectGuideChapter = useCallback((index: number) => {
    const nextIndex = Math.max(0, Math.min(index, DEMO_CHAPTERS.length - 1))
    setGuideChapter(nextIndex)
    const tab = DEMO_CHAPTERS[nextIndex].tab as WorkspaceTab
    onTabChange(tab)
    setSelectedStage(nextIndex === 0 ? 0 : nextIndex === 1 ? 2 : 2)
  }, [onTabChange, setSelectedStage])

  const startGuide = (index: number) => {
    selectGuideChapter(index)
    setGuideOpen(true)
  }

  const page = PAGE_LABELS[activeTab]
  const activeNavigation = useMemo(() => NAV_ITEMS.find((item) => item.id === activeTab), [activeTab])

  return (
    <>
      <div className="workspace-shell">
        <a className="workspace-skip" href="#mission-content">Đi tới nội dung</a>
        <aside className="workspace-dock" aria-label="Điều hướng chính">
          <a className="dock-brand" href="#mission-content" aria-label="AgroChain, về Trace Command Center" onClick={(event) => { event.preventDefault(); navigate('overview') }}><Icon name="agro" size={22} /></a>
          <span className="dock-separator" />
          <nav className="dock-nav">
            {NAV_ITEMS.map((item) => <button key={item.id} type="button" className={activeTab === item.id ? 'dock-item dock-item-active' : 'dock-item'} aria-label={item.label} aria-current={activeTab === item.id ? 'page' : undefined} title={item.label} onClick={() => navigate(item.id)}><Icon name={item.icon} size={19} /><span>{item.compact}</span></button>)}
          </nav>
          <div className="dock-bottom"><span className={`dock-api-state ${backendOnline === true ? 'dock-api-online' : backendOnline === false ? 'dock-api-offline' : ''}`} title={backendOnline === true ? 'API online' : backendOnline === false ? 'API offline' : 'API connecting'} /><span className="dock-bottom-label">API</span></div>
        </aside>

        <div className="workspace-main-frame">
          <header className="workspace-topbar">
            <div className="workspace-breadcrumb"><span>{page.eyebrow}</span><Icon name="chevron" size={14} /><strong>{page.title}</strong></div>
            <div className="workspace-tools">
              <span className="topbar-api"><i className={`api-indicator ${backendOnline === true ? 'api-indicator-online' : backendOnline === false ? 'api-indicator-offline' : ''}`} />{backendOnline === true ? 'API live' : backendOnline === false ? 'API offline' : 'Connecting'}</span>
              {DEMO_LOGIN_ENABLED && <details className="identity-switcher"><summary aria-label="Chuyển tài khoản demo" title="Đổi phiên demo"><span className="switcher-avatars"><i>G</i><i>A</i><i>I</i></span><span className="switcher-label">Switch role</span><Icon name="chevron" size={13} /></summary><div className="switcher-menu"><span className="micro-label">DEMO IDENTITY</span>{[['grower@caudat.vn', 'Cầu Đất / Grower'], ['admin@mocchau.vn', 'Mộc Châu / Org admin'], ['inspector@chicuc.gov.vn', 'Thanh tra / Inspector']].map(([email, label]) => <button key={email} type="button" disabled={switchingAccount || email === user.email} aria-current={email === user.email ? 'true' : undefined} onClick={() => { const account = DEMO_ACCOUNTS.find((item) => item.email === email); if (account) void switchDemoAccount(account) }}><span className="switcher-menu-dot" />{label}{email === user.email && <small>HIỆN TẠI</small>}</button>)}</div></details>}
              <details className="mobile-session-menu"><summary aria-label="Tài khoản và phiên làm việc"><Icon name="shield" size={19} /></summary><div><strong>{user.full_name}</strong><small>{ROLE_LABELS[user.role]}</small>{DEMO_LOGIN_ENABLED && DEMO_ACCOUNTS.map((account) => <button type="button" key={account.email} disabled={switchingAccount || account.email === user.email} onClick={() => void switchDemoAccount(account)}>{account.shortName}</button>)}<button type="button" onClick={onLogout}><Icon name="logout" size={16} />Đăng xuất</button></div></details>
              <button type="button" className="command-trigger" onClick={() => setPaletteOpen(true)} aria-haspopup="dialog"><Icon name="search" size={16} /><span>Jump to…</span><kbd>⌘ K</kbd></button>
              <button type="button" className="icon-button" aria-label={isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'} title={isDark ? 'Giao diện sáng' : 'Giao diện tối'} onClick={onToggleTheme}><Icon name={isDark ? 'sun' : 'moon'} size={17} /></button>
              <div className="current-identity" title={`${user.full_name} · ${user.email}`}><span className="identity-avatar">{user.full_name.trim().slice(0, 1).toLocaleUpperCase()}</span><span className="identity-copy"><strong>{user.full_name}</strong><small>{ROLE_LABELS[user.role]}</small></span></div>
              <button type="button" className="icon-button logout-button" aria-label="Đăng xuất" title="Đăng xuất" onClick={onLogout}><Icon name="logout" size={17} /></button>
            </div>
          </header>

          <main ref={mainRef} className={`workspace-main ${activeTab === 'presentation' ? 'workspace-main-presentation' : ''}`} id="mission-content" tabIndex={-1}>
            {(['overview', 'journey', 'integrity'] as WorkspaceTab[]).includes(activeTab) && <JourneyLens tab={activeTab} selected={selectedStage} block={chain[selectedStage]} onNavigate={navigate} />}
            {chainError && <div className="workspace-chain-error notice notice-error" role="alert">Không thể tính SHA-256: {chainError}</div>}
            {activeTab === 'overview' && <TraceCommandCenter progress={journeyProgress} onProgress={setJourneyProgress} selectedStage={selectedStage} temperatureExcursion={temperatureExcursion} chain={chain} onSelectStage={setSelectedStage} onOpenJourney={() => navigate('journey')} onOpenIntegrity={() => navigate('integrity')} />}
            {activeTab === 'farms' && <FarmAtlas farms={farms} loading={loadingFarms} error={farmError} canRead={canReadFarms} canWrite={canWriteFarms} searchQuery={searchQuery} onSearchChange={setSearchQuery} onRefresh={() => void refreshFarms()} onSave={saveFarm} />}
            {activeTab === 'journey' && <ColdChainJourney progress={journeyProgress} onProgress={setJourneyProgress} selectedStage={selectedStage} temperatureExcursion={temperatureExcursion} tampered={tampered} chain={chain} onSelectStage={setSelectedStage} onToggleExcursion={() => { setTemperatureExcursion((current) => !current); onNotify(temperatureExcursion ? 'Đã khôi phục fixture sensor.' : 'Đã tạo ngoại lệ nhiệt cục bộ; integrity được tính riêng.') }} onOpenIntegrity={() => navigate('integrity')} />}
            {activeTab === 'integrity' && <IntegrityLab key={`${tampered}:${temperatureExcursion}`} chain={chain} chainError={chainError} tampered={tampered} temperatureExcursion={temperatureExcursion} selectedStage={selectedStage} onSelectStage={setSelectedStage} onToggleTamper={() => { setSelectedStage(2); setTampered((current) => !current); onNotify(tampered ? 'Đã khôi phục payload fixture.' : 'Đã sửa temp_c cục bộ và tính lại SHA-256 thật.') }} />}
            {activeTab === 'security' && <SecurityXray user={user} probe={probe} onProbe={() => void runProbe()} demoLoginEnabled={DEMO_LOGIN_ENABLED} />}
            {activeTab === 'presentation' && <PresentationMode onStart={startGuide} />}
          </main>

          <footer className="workspace-footer"><span><i className={`api-indicator ${backendOnline === true ? 'api-indicator-online' : backendOnline === false ? 'api-indicator-offline' : ''}`} />{backendOnline === true ? 'Backend reachable' : backendOnline === false ? 'Backend unavailable' : 'Checking backend'}</span><span className="footer-tenant">TENANT / {user.organization_id.slice(0, 8).toUpperCase()}</span><span className="footer-mode">{activeNavigation?.label ?? 'Workspace'} · SESSION {user.id.slice(0, 8).toUpperCase()}</span></footer>
        </div>

        <nav className="mobile-dock" aria-label="Điều hướng chính">
          {NAV_ITEMS.map((item) => <button key={item.id} type="button" className={activeTab === item.id ? 'mobile-dock-item mobile-dock-item-active' : 'mobile-dock-item'} aria-label={item.label} aria-current={activeTab === item.id ? 'page' : undefined} onClick={() => navigate(item.id)}><Icon name={item.icon} size={18} /><span>{item.compact}</span></button>)}
        </nav>
      </div>

      {guideOpen && <DemoGuide chapterIndex={guideChapter} tampered={tampered} temperatureExcursion={temperatureExcursion} probe={probe} onClose={closeGuide} onSelectChapter={selectGuideChapter} onToggleTamper={toggleTamper} onToggleExcursion={toggleExcursion} onProbe={() => void runProbe()} />}
      {paletteOpen && <CommandPalette onClose={closePalette} onNavigate={navigate} onRefresh={refreshNow} onToggleTheme={onToggleTheme} />}
    </>
  )
}
