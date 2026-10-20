import assert from 'node:assert/strict'
import { after, afterEach, beforeEach, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { JSDOM } from 'jsdom'
import { createServer } from 'vite'
import React, { act } from 'react'

// N3-72: xuất hồ sơ truy xuất PDF kèm kết quả kiểm toàn vẹn.
// Mọi HTTP request được mock; không mở trình duyệt hay gọi API thật.
const dom = new JSDOM('<div id="root"></div>', {
  url: 'http://test.local/lots',
  pretendToBeVisual: true,
})
for (const key of [
  'window',
  'document',
  'HTMLElement',
  'HTMLDivElement',
  'HTMLAnchorElement',
  'SVGElement',
  'Element',
  'Node',
  'Event',
  'MouseEvent',
  'sessionStorage',
  'getComputedStyle',
  'requestAnimationFrame',
  'cancelAnimationFrame',
]) {
  globalThis[key] = dom.window[key]
}
Object.defineProperty(globalThis, 'navigator', {
  value: dom.window.navigator,
  configurable: true,
})
globalThis.ResizeObserver = dom.window.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.IS_REACT_ACT_ENVIRONMENT = true

const { createRoot } = await import('react-dom/client')
const server = await createServer({
  root: fileURLToPath(new URL('..', import.meta.url)),
  configFile: false,
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false },
})
const originalFetch = globalThis.fetch
const originalCreateObjectUrl = globalThis.URL.createObjectURL
const originalRevokeObjectUrl = globalThis.URL.revokeObjectURL
let root, routes, calls, downloads

beforeEach(() => {
  routes = new Map()
  calls = []
  downloads = []
  dom.window.history.replaceState({}, '', '/lots')
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(url, dom.window.location.href).pathname
    const key = `${options.method ?? 'GET'} ${path}`
    calls.push({ path, method: options.method ?? 'GET' })
    const value = routes.get(key)
    assert.ok(value, `Unexpected request: ${key}`)
    return typeof value === 'function' ? value() : value
  }
  globalThis.URL.createObjectURL = () => 'blob:n3-72-report'
  globalThis.URL.revokeObjectURL = () => {}
  dom.window.HTMLAnchorElement.prototype.click = function click() {
    downloads.push(this.download)
  }
  root = createRoot(document.getElementById('root'))
})

afterEach(async () => {
  await act(async () => {
    root.unmount()
    await new Promise((resolve) => setTimeout(resolve, 50))
  })
})

after(async () => {
  globalThis.fetch = originalFetch
  globalThis.URL.createObjectURL = originalCreateObjectUrl
  globalThis.URL.revokeObjectURL = originalRevokeObjectUrl
  await server.close()
  dom.window.close()
})

const load = async (name) =>
  (await server.ssrLoadModule(`/src/components/${name}.tsx`))[name]
const mount = async (name, props) => {
  const component = await load(name)
  await act(async () => {
    root.render(React.createElement(component, props))
  })
}
const button = (label) =>
  [...document.querySelectorAll('button')].find(
    (item) => item.textContent === label,
  )
const click = async (element) => {
  assert.ok(element)
  await act(() => element.click())
}
const waitFor = async (condition) => {
  const deadline = Date.now() + 5000
  while (!condition() && Date.now() < deadline) {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20))
    })
  }
  assert.ok(condition(), 'Expected component state did not appear within 5 seconds')
}

const lot = {
  id: '89d69962-fa86-59d7-8adf-26cb56fa9ef4',
  lot_code: 'XOAI-001',
  name: 'Xoài Cát Chu',
  product_id: 'product',
  product: { id: 'product', name: 'Xoài Cát Chu', unit: 'kg' },
  current_holder_organization_id: 'own',
  current_holder_organization_name: 'HTX Cao Lãnh',
  remaining_quantity: '40.000',
  quantity: '40.000',
  status: 'active',
}
const detailProps = {
  lotId: lot.id,
  organizationId: 'own',
  canReadEvents: true,
  canCreateEvents: true,
  canCreateHandover: true,
  canResolveHandover: true,
  canTransform: true,
  canManageDistribution: false,
  onOpenLot: () => {},
  onBack: () => {},
}
const seedDetails = () => {
  routes.set(
    `GET /api/v1/lots/${lot.id}`,
    new Response(
      JSON.stringify({
        ...lot,
        parents: [],
        children: [],
        direct_farms: [],
        root_farms: [{ id: 'farm-1', name: 'Vườn xoài Cao Lãnh' }],
        event_count: 1,
      }),
      { headers: { 'Content-Type': 'application/json' } },
    ),
  )
  routes.set(
    `GET /api/v1/events/lots/${lot.id}/history`,
    new Response(
      JSON.stringify({
        events: [],
        total: 0,
        next_cursor: null,
        integrity: { valid: true, checked_events: 0 },
      }),
      { headers: { 'Content-Type': 'application/json' } },
    ),
  )
  for (const path of [
    'GET /api/v1/handovers/incoming',
    'GET /api/v1/handovers/outgoing',
    'GET /api/v1/handovers/organizations',
  ]) {
    routes.set(path, new Response('[]', { headers: { 'Content-Type': 'application/json' } }))
  }
}

test('N3-72: tên tệp PDF dùng mã lô và chỉ giữ ký tự an toàn', async () => {
  const { lotReportFileName } = await server.ssrLoadModule('/src/utils/report.ts')

  assert.equal(lotReportFileName(lot), 'ho-so-truy-xuat-XOAI-001.pdf')
  assert.equal(
    lotReportFileName({ id: 'abcdef12-3456-7890-abcd-ef1234567890', lot_code: null }),
    'ho-so-truy-xuat-abcdef12.pdf',
  )
  assert.equal(
    lotReportFileName({ id: 'x', lot_code: 'A B/../C' }),
    'ho-so-truy-xuat-A-B-C.pdf',
  )
})

test('N3-72: nút Xuất hồ sơ PDF tải tệp đúng endpoint và báo thành công', async () => {
  seedDetails()
  routes.set(
    `GET /api/v1/lots/${lot.id}/report.pdf`,
    new Response(new Blob(['%PDF-1.4']), {
      headers: { 'Content-Type': 'application/pdf' },
    }),
  )

  await mount('LotDetailPanel', detailProps)
  await waitFor(() => button('Xuất hồ sơ PDF'))
  await click(button('Xuất hồ sơ PDF'))
  await waitFor(() => document.body.textContent.includes('Đã xuất hồ sơ truy xuất PDF'))

  assert.ok(
    calls.some((item) => item.path === `/api/v1/lots/${lot.id}/report.pdf`),
    'report endpoint was not requested',
  )
  assert.deepEqual(downloads, ['ho-so-truy-xuat-XOAI-001.pdf'])
})

test('N3-72: lỗi khi xuất hồ sơ được hiển thị cho người dùng', async () => {
  seedDetails()
  routes.set(
    `GET /api/v1/lots/${lot.id}/report.pdf`,
    new Response(JSON.stringify({ detail: 'Không tìm thấy lô hàng.' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

  await mount('LotDetailPanel', detailProps)
  await waitFor(() => button('Xuất hồ sơ PDF'))
  await click(button('Xuất hồ sơ PDF'))
  await waitFor(() => document.body.textContent.includes('Không tìm thấy lô hàng.'))

  assert.deepEqual(downloads, [])
})
