import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

// Offline rendering only: no browser, HTTP listener, API or effects are run.
const server = await createServer({root: fileURLToPath(new URL('..', import.meta.url)), cacheDir: fileURLToPath(new URL('../node_modules/.vite-task-tests', import.meta.url)), configFile: false, optimizeDeps: {noDiscovery: true, include: []}, server: {middlewareMode: true, hmr: false}})
after(() => server.close())
globalThis.window = {location: {search: ''}}
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

test('cold chain statistics panel offers the reporting windows', async () => {
  const output = html(await load('ColdChainStatsPanel'))
  assert.match(output, /Thống kê vi phạm chuỗi lạnh/)
  assert.match(output, />7 ngày</)
  assert.match(output, />30 ngày</)
  assert.match(output, />90 ngày</)
  assert.match(output, />Tất cả</)
})

test('cold chain statistics panel explains the reporting window', async () => {
  const output = html(await load('ColdChainStatsPanel'))
  assert.match(output, /Khoảng thời gian tính theo thời điểm/)
})

test('sidebar shows the cold chain statistics entry for a transporter', async () => {
  const output = html(await load('WorkspaceSidebar'), {
    user: user('transporter'),
    activeTab: 'lots',
    sidebarOpen: false,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })
  assert.match(output, /Thống kê chuỗi lạnh/)
})

test('sidebar hides the cold chain statistics entry from a grower', async () => {
  const output = html(await load('WorkspaceSidebar'), {
    user: {...user('grower'), organization_type: 'farm'},
    activeTab: 'lots',
    sidebarOpen: false,
    onCloseSidebar: () => {},
    onTabChange: () => {},
    onLogout: () => {},
  })
  assert.doesNotMatch(output, /Thống kê chuỗi lạnh/)
})
