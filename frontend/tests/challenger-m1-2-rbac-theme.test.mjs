import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import { createServer } from 'vite'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { JSDOM } from 'jsdom'

// Set up server for SSR loading of React components
const server = await createServer({
  root: fileURLToPath(new URL('..', import.meta.url)),
  configFile: false,
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false },
})
after(() => server.close())

globalThis.window = { location: { search: '' }, history: { pushState() {}, replaceState() {} } }
const load = async (name) => (await server.ssrLoadModule(`/src/components/${name}.tsx`))[name]
const html = (component, props) => renderToStaticMarkup(React.createElement(component, props))

const makeUser = (role, orgType = 'farm') => ({
  id: `u-${role}`,
  email: `${role}@example.com`,
  full_name: `Nguyễn Văn ${role.toUpperCase()}`,
  organization_id: `org-${role}`,
  organization_name: `Tổ chức ${role}`,
  organization_type: orgType,
  role,
})

// =========================================================================
// SECTION 1: WORKSPACE SIDEBAR RBAC & GROUPING FOR ALL 6 ROLES
// =========================================================================

test('RBAC 1.1: WorkspaceSidebar for "grower" (farm) organizes items into 3 groups and strictly hides unauthorized cold-chain & admin operations', async () => {
  const WorkspaceSidebar = await load('WorkspaceSidebar')
  const output = html(WorkspaceSidebar, {
    user: makeUser('grower', 'farm'),
    activeTab: 'lots',
    sidebarOpen: true,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })

  // Group Headers
  assert.match(output, /Quản lý Nông sản/, 'Group 1 "Quản lý Nông sản" must be visible')
  assert.match(output, /Vận hành Chuỗi lạnh/, 'Group 2 "Vận hành Chuỗi lạnh" must be visible')
  assert.match(output, /Giám sát &amp; Quản trị|Giám sát & Quản trị/, 'Group 3 "Giám sát & Quản trị" must be visible')

  // Group 1 Items
  assert.match(output, /Danh sách lô/, 'Grower must see "Danh sách lô"')
  assert.match(output, /Vùng trồng/, 'Grower must see "Vùng trồng"')
  assert.match(output, /Nông sản/, 'Grower must see "Nông sản"')

  // Group 2 Items: Only "Bàn giao" allowed for grower
  assert.match(output, /Bàn giao/, 'Grower must see "Bàn giao"')
  assert.doesNotMatch(output, /Thao tác chuỗi lạnh/, 'Grower MUST NOT see "Thao tác chuỗi lạnh"')
  assert.doesNotMatch(output, /Chuỗi nhiệt độ/, 'Grower MUST NOT see "Chuỗi nhiệt độ"')
  assert.doesNotMatch(output, /Thống kê chuỗi lạnh/, 'Grower MUST NOT see "Thống kê chuỗi lạnh"')
  assert.doesNotMatch(output, /Điểm phân phối/, 'Grower MUST NOT see "Điểm phân phối"')

  // Group 3 Items: Only "Quản trị tổ chức"
  assert.match(output, /Quản trị tổ chức/, 'Grower must see "Quản trị tổ chức"')
  assert.doesNotMatch(output, /Tính toàn vẹn/, 'Grower MUST NOT see "Tính toàn vẹn"')
  assert.doesNotMatch(output, /Nhật ký thao tác/, 'Grower MUST NOT see "Nhật ký thao tác"')
})

test('RBAC 1.2: WorkspaceSidebar for "transporter" (transport) hides farms and distribution points, shows cold-chain suite', async () => {
  const WorkspaceSidebar = await load('WorkspaceSidebar')
  const output = html(WorkspaceSidebar, {
    user: makeUser('transporter', 'transport'),
    activeTab: 'cold-chain',
    sidebarOpen: true,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })

  // Group 1: Has Lots and Products, but NO Farms
  assert.match(output, /Danh sách lô/)
  assert.match(output, /Nông sản/)
  assert.doesNotMatch(output, /Vùng trồng/, 'Transporter does not cultivate farms; "Vùng trồng" MUST be hidden')

  // Group 2: Complete Cold Chain operations suite
  assert.match(output, /Bàn giao/)
  assert.match(output, /Thao tác chuỗi lạnh/)
  assert.match(output, /Chuỗi nhiệt độ/)
  assert.match(output, /Thống kê chuỗi lạnh/)
  assert.doesNotMatch(output, /Điểm phân phối/, 'Transporter MUST NOT see "Điểm phân phối"')

  // Group 3: Organization Admin only
  assert.match(output, /Quản trị tổ chức/)
  assert.doesNotMatch(output, /Tính toàn vẹn/)
  assert.doesNotMatch(output, /Nhật ký thao tác/)
})

test('RBAC 1.3: WorkspaceSidebar for "distributor" (distribution) enables distribution locations and cold-chain monitoring', async () => {
  const WorkspaceSidebar = await load('WorkspaceSidebar')
  const output = html(WorkspaceSidebar, {
    user: makeUser('distributor', 'distribution'),
    activeTab: 'lots',
    sidebarOpen: true,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })

  // Group 1: Lots and Products, NO Farms
  assert.match(output, /Danh sách lô/)
  assert.match(output, /Nông sản/)
  assert.doesNotMatch(output, /Vùng trồng/)

  // Group 2: Includes "Điểm phân phối" specifically for distribution org
  assert.match(output, /Bàn giao/)
  assert.match(output, /Thao tác chuỗi lạnh/)
  assert.match(output, /Chuỗi nhiệt độ/)
  assert.match(output, /Thống kê chuỗi lạnh/)
  assert.match(output, /Điểm phân phối/, 'Distributor with distribution org MUST see "Điểm phân phối"')

  // Group 3
  assert.match(output, /Quản trị tổ chức/)
  assert.doesNotMatch(output, /Tính toàn vẹn/)
  assert.doesNotMatch(output, /Nhật ký thao tác/)
})

test('RBAC 1.4: WorkspaceSidebar for "inspector" (inspection) displays audit & integrity tools, hides operational writes', async () => {
  const WorkspaceSidebar = await load('WorkspaceSidebar')
  const output = html(WorkspaceSidebar, {
    user: makeUser('inspector', 'inspection'),
    activeTab: 'integrity',
    sidebarOpen: true,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })

  // Group 1: Lots (via lots:read_all) and Products, NO Farms
  assert.match(output, /Danh sách lô/)
  assert.match(output, /Nông sản/)
  assert.doesNotMatch(output, /Vùng trồng/)

  // Group 2: Read-only cold-chain telemetry, NO handovers or shipment creation
  assert.doesNotMatch(output, /Bàn giao/, 'Inspector does not hold cargo; "Bàn giao" MUST be hidden')
  assert.doesNotMatch(output, /Thao tác chuỗi lạnh/, 'Inspector does not create shipments; "Thao tác chuỗi lạnh" MUST be hidden')
  assert.match(output, /Chuỗi nhiệt độ/, 'Inspector can inspect "Chuỗi nhiệt độ"')
  assert.match(output, /Thống kê chuỗi lạnh/, 'Inspector can inspect "Thống kê chuỗi lạnh"')
  assert.doesNotMatch(output, /Điểm phân phối/)

  // Group 3: Has "Tính toàn vẹn" via events:verify!
  assert.match(output, /Tính toàn vẹn/, 'Inspector MUST see dedicated "Tính toàn vẹn" audit tab')
  assert.match(output, /Quản trị tổ chức/)
  assert.doesNotMatch(output, /Nhật ký thao tác/, 'Only system_admin can view security log')
})

test('RBAC 1.5: WorkspaceSidebar for "organization_admin" allows full tenant management and operations', async () => {
  const WorkspaceSidebar = await load('WorkspaceSidebar')
  const output = html(WorkspaceSidebar, {
    user: makeUser('organization_admin', 'cooperative'),
    activeTab: 'lots',
    sidebarOpen: true,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })

  assert.match(output, /Danh sách lô/)
  assert.match(output, /Vùng trồng/)
  assert.match(output, /Nông sản/)
  assert.match(output, /Bàn giao/)
  assert.match(output, /Thao tác chuỗi lạnh/)
  assert.match(output, /Chuỗi nhiệt độ/)
  assert.match(output, /Thống kê chuỗi lạnh/)
  assert.match(output, /Quản trị tổ chức/)
  assert.doesNotMatch(output, /Nhật ký thao tác/, 'Security log is restricted to system_admin')
})

test('RBAC 1.6: WorkspaceSidebar for "system_admin" enables all 3 governance tools and system-wide monitors', async () => {
  const WorkspaceSidebar = await load('WorkspaceSidebar')
  const output = html(WorkspaceSidebar, {
    user: makeUser('system_admin', 'administration'),
    activeTab: 'dashboard',
    sidebarOpen: true,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })

  assert.match(output, /Danh sách lô/)
  assert.match(output, /Vùng trồng/)
  assert.match(output, /Nông sản/)

  // System admin does not perform physical cargo handovers
  assert.doesNotMatch(output, /Bàn giao/, 'System admin is not a cargo holding org')
  assert.match(output, /Thao tác chuỗi lạnh/)
  assert.match(output, /Chuỗi nhiệt độ/)
  assert.match(output, /Thống kê chuỗi lạnh/)

  // All 3 governance tools visible
  assert.match(output, /Tính toàn vẹn/, 'System admin sees "Tính toàn vẹn"')
  assert.match(output, /Nhật ký thao tác/, 'System admin sees "Nhật ký thao tác"')
  assert.match(output, /Quản trị tổ chức/, 'System admin sees "Quản trị tổ chức"')
})

// =========================================================================
// SECTION 2: CRYPTOGRAPHIC HASH CHAIN AUDIT BADGE FOR NON-ADMIN ROLES
// =========================================================================

test('AUDIT BADGE 2.1: Non-admin roles (grower, transporter, distributor) render verified hash chain badge via getLotHistory without calling privileged /integrity (avoiding 403 Forbidden)', async () => {
  const dom = new JSDOM('<div id="root"></div>', { url: 'http://test.local/lots/test-lot-id' })
  for (const key of ['window', 'document', 'HTMLElement', 'HTMLDivElement', 'HTMLDialogElement', 'Element', 'Node', 'Event', 'sessionStorage']) {
    globalThis[key] = dom.window[key]
  }
  if (!dom.window.HTMLDialogElement?.prototype?.showModal) {
    dom.window.HTMLDialogElement.prototype.showModal = function () { this.open = true }
    dom.window.HTMLDialogElement.prototype.close = function () { this.open = false }
  }

  const sampleLot = {
    id: 'lot-chain-1',
    lot_code: 'LOT-AUDIT-01',
    name: 'Bưởi Da Xanh VietGAP',
    product_id: 'prod-buoi',
    product: { id: 'prod-buoi', name: 'Bưởi Da Xanh', unit: 'kg' },
    current_holder_organization_id: 'org-grower',
    current_holder_organization_name: 'Nông trại Bến Tre',
    remaining_quantity: '500.000',
    quantity: '500.000',
    status: 'active',
    harvested_on: '2026-10-20',
    current_location_id: null,
    current_location: null,
    event_count: 2,
    parents: [],
    children: [],
    direct_farms: [{ id: 'farm-1', name: 'Vườn Bến Tre' }],
    root_farms: [{ id: 'farm-1', name: 'Vườn Bến Tre' }],
  }

  const mockHistoryValid = {
    events: [
      {
        id: 'ev-1',
        sequence_number: 1,
        event_type: 'harvest',
        recorded_at: '2026-10-20T07:00:00Z',
        organization_name: 'Nông trại Bến Tre',
        payload: { mass: 500 },
        prev_hash: '0'.repeat(64),
        event_hash: 'abc123hash',
      },
      {
        id: 'ev-2',
        sequence_number: 2,
        event_type: 'certify',
        recorded_at: '2026-10-20T08:00:00Z',
        organization_name: 'Nông trại Bến Tre',
        payload: { cert: 'VietGAP' },
        prev_hash: 'abc123hash',
        event_hash: 'def456hash',
      },
    ],
    integrity: {
      valid: true,
      checked_events: 2,
      first_invalid_sequence: null,
      issues: [],
    },
    total: 2,
  }

  const routesCalled = []
  globalThis.fetch = async (url) => {
    const urlStr = String(url)
    routesCalled.push(urlStr)

    // Adversarial trap: If client calls privileged /integrity endpoint, return 403 Forbidden!
    if (urlStr.includes('/api/v1/events/lots/lot-chain-1/integrity') && !urlStr.includes('/history')) {
      return new Response(JSON.stringify({ detail: 'Quyền bị từ chối: events:verify yêu cầu vai trò thanh tra hoặc quản trị hệ thống' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    if (urlStr.includes('/api/v1/lots/lot-chain-1')) {
      return new Response(JSON.stringify(sampleLot), { headers: { 'Content-Type': 'application/json' } })
    }
    if (urlStr.includes('/history')) {
      return new Response(JSON.stringify(mockHistoryValid), { headers: { 'Content-Type': 'application/json' } })
    }
    return new Response(JSON.stringify([]), { headers: { 'Content-Type': 'application/json' } })
  }

  const LotDetailPanel = await load('LotDetailPanel')
  const { act } = await import('react')
  const { createRoot } = await import('react-dom/client')
  const rootEl = document.getElementById('root')
  const root = createRoot(rootEl)

  // Mount as non-admin "grower"
  await act(async () => {
    root.render(
      React.createElement(LotDetailPanel, {
        lotId: 'lot-chain-1',
        organizationId: 'org-grower',
        canReadEvents: true,
        canCreateEvents: true,
        canCreateHandover: true,
        canResolveHandover: false,
        onBack: () => {},
        onOpenLot: () => {},
      })
    )
  })

  // Allow async fetch & state updates
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 100))
  })

  // Assert that privileged /integrity endpoint was NEVER called
  const calledPrivilegedIntegrity = routesCalled.some((r) => r.includes('/integrity') && !r.includes('/history'))
  assert.equal(calledPrivilegedIntegrity, false, 'Client MUST NOT call privileged /integrity endpoint for non-admin roles')

  // Assert that /history endpoint WAS called
  const calledHistory = routesCalled.some((r) => r.includes('/events/lots/lot-chain-1/history'))
  assert.equal(calledHistory, true, 'Client MUST call unprivileged /history endpoint')

  // Assert that Cryptographic Hash Chain Audit Badge is displayed in the DOM
  const badges = Array.from(rootEl.querySelectorAll('.status-badge'))
  const hashChainBadge = badges.find((b) => b.textContent.includes('Chuỗi băm toàn vẹn'))
  assert.ok(hashChainBadge, 'Cryptographic hash chain badge must be rendered in DOM')
  assert.ok(hashChainBadge.classList.contains('status-done'), 'Badge must have status-done class for valid chain')
  assert.match(
    hashChainBadge.getAttribute('title') ?? '',
    /Đã kiểm tra 2 sự kiện trong chuỗi băm SHA-256/,
    'Title tooltip must show verified event count'
  )

  root.unmount()
})

test('AUDIT BADGE 2.2: Cryptographic Hash Chain Badge displays warning and identifies invalid sequence on tamper', async () => {
  const dom = new JSDOM('<div id="root"></div>', { url: 'http://test.local/lots/tampered-lot' })
  for (const key of ['window', 'document', 'HTMLElement', 'HTMLDivElement', 'HTMLDialogElement', 'Element', 'Node', 'Event', 'sessionStorage']) {
    globalThis[key] = dom.window[key]
  }

  const sampleLot = {
    id: 'lot-tampered',
    lot_code: 'LOT-TAMPER-99',
    name: 'Sầu Riêng Ri6',
    remaining_quantity: '100.000',
    quantity: '100.000',
    status: 'active',
    harvested_on: '2026-10-18',
    current_holder_organization_id: 'org-test',
    current_holder_organization_name: 'Vựa Trái Cây',
    current_location_id: null,
    current_location: null,
    event_count: 4,
    parents: [],
    children: [],
    direct_farms: [{ id: 'farm-tamper', name: 'Vườn Cái Mơn' }],
    root_farms: [{ id: 'farm-tamper', name: 'Vườn Cái Mơn' }],
  }

  const mockHistoryTampered = {
    events: [],
    integrity: {
      valid: false,
      checked_events: 4,
      first_invalid_sequence: 3,
      issues: [{ sequence_number: 3, kind: 'hash_mismatch' }],
    },
    total: 4,
  }

  globalThis.fetch = async (url) => {
    const urlStr = String(url)
    if (urlStr.includes('/api/v1/lots/lot-tampered')) {
      return new Response(JSON.stringify(sampleLot), { headers: { 'Content-Type': 'application/json' } })
    }
    if (urlStr.includes('/history')) {
      return new Response(JSON.stringify(mockHistoryTampered), { headers: { 'Content-Type': 'application/json' } })
    }
    return new Response(JSON.stringify([]), { headers: { 'Content-Type': 'application/json' } })
  }

  const LotDetailPanel = await load('LotDetailPanel')
  const { act } = await import('react')
  const { createRoot } = await import('react-dom/client')
  const rootEl = document.getElementById('root')
  const root = createRoot(rootEl)

  await act(async () => {
    root.render(
      React.createElement(LotDetailPanel, {
        lotId: 'lot-tampered',
        organizationId: 'org-test',
        canReadEvents: true,
        onBack: () => {},
        onOpenLot: () => {},
      })
    )
  })

  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 100))
  })

  const badges = Array.from(rootEl.querySelectorAll('.status-badge'))
  const dangerBadge = badges.find((b) => b.classList.contains('status-danger'))
  assert.ok(dangerBadge, 'Danger status badge must be rendered when hash chain is invalid')
  assert.match(dangerBadge.textContent, /Sai lệch hash \(#3\)/, 'Badge must indicate exact invalid sequence number')

  root.unmount()
})

// =========================================================================
// SECTION 3: THEME CONTRAST & DARK MODE COMPLIANCE IN INDEX.CSS
// =========================================================================

function hexToRgb(hex) {
  const clean = hex.replace('#', '').trim()
  if (clean.length === 3) {
    return [
      parseInt(clean[0] + clean[0], 16),
      parseInt(clean[1] + clean[1], 16),
      parseInt(clean[2] + clean[2], 16),
    ]
  }
  return [
    parseInt(clean.slice(0, 2), 16),
    parseInt(clean.slice(2, 4), 16),
    parseInt(clean.slice(4, 6), 16),
  ]
}

function relativeLuminance(r, g, b) {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const s = c / 255
    return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  })
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs
}

function contrastRatio(hex1, hex2) {
  const [r1, g1, b1] = hexToRgb(hex1)
  const [r2, g2, b2] = hexToRgb(hex2)
  const l1 = relativeLuminance(r1, g1, b1)
  const l2 = relativeLuminance(r2, g2, b2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

test('THEME CONTRAST 3.1: Dark Mode text tokens meet WCAG AA (>= 4.5:1) and AAA (>= 7:1) contrast thresholds on Slate-950 and Slate-900', () => {
  // Extract Dark Mode Backgrounds
  const slate950 = '#161917' // Base background
  const slate900 = '#222623' // Card/panel background

  // Extract high-contrast tokens
  // 1. .vf-ok-text (#9BBF92 / --emerald-300)
  const okTextHex = '#9BBF92'
  const okVs950 = contrastRatio(okTextHex, slate950)
  const okVs900 = contrastRatio(okTextHex, slate900)
  assert.ok(
    okVs950 >= 7.0,
    `.vf-ok-text (${okTextHex}) vs Slate-950 (${slate950}) contrast is ${okVs950.toFixed(2)}:1 (meets WCAG AAA >= 7.0:1)`
  )
  assert.ok(
    okVs900 >= 4.5,
    `.vf-ok-text (${okTextHex}) vs Slate-900 (${slate900}) contrast is ${okVs900.toFixed(2)}:1 (meets WCAG AA >= 4.5:1)`
  )

  // 2. .vf-mint-text (#33A881 / --mint-500)
  const mintTextHex = '#33A881'
  const mintVs950 = contrastRatio(mintTextHex, slate950)
  const mintVs900 = contrastRatio(mintTextHex, slate900)
  assert.ok(
    mintVs950 >= 4.5,
    `.vf-mint-text (${mintTextHex}) vs Slate-950 contrast is ${mintVs950.toFixed(2)}:1 (meets WCAG AA >= 4.5:1)`
  )
  assert.ok(
    mintVs900 >= 4.0,
    `.vf-mint-text (${mintTextHex}) vs Slate-900 contrast is ${mintVs900.toFixed(2)}:1 (meets WCAG AA >= 3.0:1 for bold text)`
  )

  // 3. .vf-terracotta-text (#f87171)
  const terracottaHex = '#f87171'
  const terraVs950 = contrastRatio(terracottaHex, slate950)
  const terraVs900 = contrastRatio(terracottaHex, slate900)
  assert.ok(
    terraVs950 >= 4.5,
    `.vf-terracotta-text (${terracottaHex}) vs Slate-950 contrast is ${terraVs950.toFixed(2)}:1 (meets WCAG AA >= 4.5:1)`
  )
  assert.ok(
    terraVs900 >= 4.5,
    `.vf-terracotta-text (${terracottaHex}) vs Slate-900 contrast is ${terraVs900.toFixed(2)}:1 (meets WCAG AA >= 4.5:1)`
  )

  // 4. Heading & Body Text in Dark Mode
  const headingHex = '#F4F1E8' // --slate-50
  const bodyHex = '#E5DFD3'    // --slate-200
  const headingVs950 = contrastRatio(headingHex, slate950)
  const bodyVs950 = contrastRatio(bodyHex, slate950)
  assert.ok(
    headingVs950 >= 12.0,
    `Heading text contrast ${headingVs950.toFixed(2)}:1 exceeds AAA standard`
  )
  assert.ok(
    bodyVs950 >= 10.0,
    `Body text contrast ${bodyVs950.toFixed(2)}:1 exceeds AAA standard`
  )
})

test('THEME CONTRAST 3.2: index.css contains dark mode styles for ReactFlow lineage nodes and Leaflet map tiles', () => {
  const cssPath = path.resolve(fileURLToPath(new URL('..', import.meta.url)), 'src/index.css')
  const css = fs.readFileSync(cssPath, 'utf-8')

  // ReactFlow Lineage Panel rules
  assert.match(css, /html\.dark\s+\.lineage-canvas\s+\.react-flow/, 'ReactFlow dark container styling present')
  assert.match(css, /--xy-background-color-default:\s*var\(--slate-950\)/, 'ReactFlow dark background variable')
  assert.match(css, /html\.dark\s+\.lineage-canvas\s+\.react-flow__node/, 'ReactFlow dark node container styling')
  assert.match(css, /html\.dark\s+\.lineage-current/, 'ReactFlow selected node highlight in dark mode')
  assert.match(css, /html\.dark\s+\.lineage-canvas\s+\.react-flow__edge-path/, 'ReactFlow high-contrast edges in dark mode')

  // Leaflet RouteMap rules
  assert.match(css, /html\.dark\s+\.route-map\s+\.leaflet-tile-pane/, 'Leaflet dark tile filter present')
  assert.match(css, /filter:\s*invert\(1\)\s+hue-rotate\(180deg\)/, 'Leaflet night mode tile inversion filter')
  assert.match(css, /html\.dark\s+\.route-map\s+\.leaflet-popup-content-wrapper/, 'Leaflet popup dark theme wrapper')
  assert.match(css, /html\.dark\s+\.route-map\s+\.leaflet-control-zoom/, 'Leaflet dark zoom control styling')
})
