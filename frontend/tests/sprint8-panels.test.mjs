import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { JSDOM } from 'jsdom'

// Offline rendering only: no browser, HTTP listener, API or effects are run.
// The map component pulls in Leaflet, which needs a DOM as soon as it loads.
const dom = new JSDOM('<!doctype html><html><body></body></html>', {
  url: 'https://test.local',
})
globalThis.window = dom.window
globalThis.document = dom.window.document
globalThis.Element = dom.window.Element
globalThis.HTMLElement = dom.window.HTMLElement
globalThis.SVGElement = dom.window.SVGElement
globalThis.Node = dom.window.Node
Object.defineProperty(globalThis, 'navigator', {
  value: dom.window.navigator,
  configurable: true,
})

const server = await createServer({root: fileURLToPath(new URL('..', import.meta.url)), cacheDir: fileURLToPath(new URL('../node_modules/.vite-task-tests', import.meta.url)), configFile: false, optimizeDeps: {noDiscovery: true, include: []}, server: {middlewareMode: true, hmr: false}})
after(() => server.close())
const load = async (name) => (await server.ssrLoadModule(`/src/components/${name}.tsx`))[name]
const html = (component, props) => renderToStaticMarkup(React.createElement(component, props))

const user = (role) => ({
  id: 'u-1',
  email: 'test@example.com',
  full_name: 'Test User',
  organization_id: 'o-1',
  organization_name: 'Test Org',
  organization_type: 'transport',
  role,
})

const sidebar = async (role) =>
  html(await load('WorkspaceSidebar'), {
    user: role === 'grower' ? {...user(role), organization_type: 'farm'} : user(role),
    activeTab: 'lots',
    sidebarOpen: false,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })

test('input lots panel offers the declaration fields of a lot', async () => {
  const output = html(await load('LotInputLotsPanel'), {
    lotId: 'lot-1',
    canDeclare: true,
  })
  assert.match(output, /Vật tư đã dùng cho lô/)
  assert.match(output, /Vật tư/)
  assert.match(output, /Liều lượng/)
  assert.match(output, /Ngày dùng/)
  assert.match(output, /Đang tải danh sách vật tư/)
})

test('processing steps panel offers the step and parameter fields', async () => {
  const output = html(await load('ProcessingStepsPanel'), {
    lotId: 'lot-1',
    canRecord: true,
  })
  assert.match(output, /Công đoạn chế biến của lô/)
  assert.match(output, /Công đoạn/)
  assert.match(output, /Tham số/)
  assert.match(output, /Ghi công đoạn/)
})

test('processing steps panel hides the form without the permission', async () => {
  const output = html(await load('ProcessingStepsPanel'), {
    lotId: 'lot-1',
    canRecord: false,
  })
  assert.match(output, /Công đoạn chế biến của lô/)
  assert.doesNotMatch(output, /Ghi công đoạn/)
})

test('route map exposes the stop points as an image region', async () => {
  const output = html(await load('RouteMap'), {
    route: {
      precision_note: 'Vị trí lấy từ vùng trồng đã khai.',
      points: [
        {
          order: 1,
          name: 'Vùng trồng xuất phát',
          kind: 'origin',
          latitude: 10.1,
          longitude: 106.1,
        },
        {
          order: 2,
          name: 'Kho trung gian',
          kind: 'stop',
          latitude: 10.2,
          longitude: 106.2,
        },
      ],
    },
    lotCode: 'LOT-1',
  })
  assert.match(output, /Bản đồ các điểm dừng của hành trình/)
  assert.match(output, /Bản đồ hành trình/)
  assert.match(output, /Kho trung gian/)
})

test('route map stays hidden when the route has no point', async () => {
  const output = html(await load('RouteMap'), {
    route: {precision_note: '', points: []},
    lotCode: 'LOT-1',
  })
  assert.equal(output, '')
})

test('shipment temperature panel explains the hourly aggregation', async () => {
  const output = html(await load('ShipmentTemperaturePanel'))
  assert.match(output, /Chuỗi nhiệt độ theo giờ/)
  assert.match(output, /Chuyến vận chuyển/)
  assert.match(output, /Đang tải chuyến vận chuyển/)
})

test('hourly aggregate list announces the loading state', async () => {
  const output = html(await load('HourlyAggregateList'), {shipmentId: 'ship-1'})
  assert.match(output, /Đang tải chuỗi tổng hợp/)
})

test('organization admin panel shows the contact address and the invitation form', async () => {
  const output = html(await load('OrganizationAdminPanel'), {canManage: true})
  assert.match(output, /Quản trị tổ chức/)
  assert.match(output, /Email đầu mối/)
  assert.match(output, /Mời thành viên mới/)
  assert.match(output, /Gửi lời mời/)
})

test('organization admin panel hides the management actions without the permission', async () => {
  const output = html(await load('OrganizationAdminPanel'), {canManage: false})
  assert.match(output, /Quản trị tổ chức/)
  assert.doesNotMatch(output, /Gửi lời mời/)
  assert.doesNotMatch(output, /Email đầu mối/)
})

test('sidebar shows the temperature series entry for a transporter', async () => {
  assert.match(await sidebar('transporter'), /Chuỗi nhiệt độ/)
})

test('sidebar hides the temperature series entry from a grower', async () => {
  assert.doesNotMatch(await sidebar('grower'), /Chuỗi nhiệt độ/)
})

test('sidebar shows the organization entry for every member', async () => {
  assert.match(await sidebar('grower'), /Quản trị tổ chức/)
  assert.match(await sidebar('organization_admin'), /Quản trị tổ chức/)
})
