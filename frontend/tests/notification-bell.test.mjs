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
  organization_type: 'farm',
  role,
})

test('notification bell is hidden without the notifications permission', async () => {
  const output = html(await load('NotificationBell'), {canRead: false})
  assert.equal(output, '')
})

test('notification bell renders the accessible trigger without a badge', async () => {
  const output = html(await load('NotificationBell'), {canRead: true})
  assert.match(output, /aria-label="Thông báo, không có thông báo chưa đọc"/)
  assert.doesNotMatch(output, /notification-bell-badge/)
})

test('workspace topbar shows the notification bell for a grower', async () => {
  const output = html(await load('WorkspaceTopbar'), {
    user: user('grower'),
    activeTab: 'lots',
    canReadFarms: true,
    searchQuery: '',
    isDark: false,
    onToggleSidebar: () => {},
    onSearchChange: () => {},
    onRefresh: () => {},
    onToggleTheme: () => {},
  })
  assert.match(output, /notification-bell-btn/)
  assert.match(output, /Thông báo/)
})
