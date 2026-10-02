import test from 'node:test'
import assert from 'node:assert/strict'
import { createPreviewTransport, PREVIEW_USERS, PREVIEW_FARMS } from '../qa/mockBackend.ts'
const post = (body) => ({ method: 'POST', body: JSON.stringify(body) })

test('synthetic QA sessions support login, role gating and tenant fixtures independently', async () => {
  const server = createPreviewTransport()
  assert.equal((await server.fetch('/api/v1/farms/')).status, 401)
  for (const user of PREVIEW_USERS) {
    assert.equal((await server.fetch('/api/v1/auth/demo-login', post({ email: user.email }))).status, 200)
    const response = await server.fetch('/api/v1/farms/')
    if (user.role === 'inspector') assert.equal(response.status, 403)
    else {
      assert.equal(response.status, 200)
      const visible = await response.json()
      assert.ok(visible.length > 0)
      assert.ok(visible.every((farm) => farm.organization_id === user.organization_id))
    }
  }
  await server.fetch('/api/v1/auth/logout', { method: 'POST' })
  assert.equal((await server.fetch('/api/v1/auth/me')).status, 401)
})

test('synthetic create/edit keeps UUID and cannot update another tenant record', async () => {
  const server = createPreviewTransport('grower')
  const payload = { name: 'Vùng QA mới', area_ha: '1.2', latitude: '11.92', longitude: '108.49' }
  const created = await (await server.fetch('/api/v1/farms/', post(payload))).json()
  const updated = await (await server.fetch(`/api/v1/farms/${created.id}`, { method: 'PUT', body: JSON.stringify({ ...payload, name: 'Vùng QA đổi tên' }) })).json()
  assert.equal(updated.id, created.id)
  assert.equal(updated.name, 'Vùng QA đổi tên')
  assert.equal((await server.fetch(`/api/v1/farms/${PREVIEW_FARMS[3].id}`, { method: 'PUT', body: JSON.stringify(payload) })).status, 404)
  assert.equal((await server.fetch('/api/v1/farms/', post({ ...payload, area_ha: '-1' }))).status, 422)
  server.setFailure(true)
  assert.equal((await server.fetch('/api/v1/farms/')).status, 503)
})
