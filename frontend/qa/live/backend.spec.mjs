import { test, expect } from 'playwright/test'
import { readFileSync } from 'node:fs'

const credentials = () => JSON.parse(readFileSync(new URL('../.live-credentials.json', import.meta.url), 'utf8'))
const api = 'http://127.0.0.1:8000'
const organizations = { grower: '11111111-1111-4111-8111-111111111111', organization_admin: '22222222-2222-4222-8222-222222222222' }
const demo = async (page, index) => {
  await page.goto('/')
  await page.getByRole('button', { name: /^Vào demo/ }).nth(index).click()
  await expect(page.locator('.workspace-shell')).toBeVisible()
}
const navigate = async (page, name) => {
  await page.getByRole('button', { name, exact: true }).click()
  await expect(page.locator('main h1')).toBeFocused()
}

test('real credential login, session reload, server logout and unauthenticated read', async ({ page }, info) => {
  await page.goto('/')
  const data = credentials()
  await page.getByLabel('Email tổ chức', { exact: false }).fill(data.email)
  await page.getByLabel('Mật khẩu', { exact: false }).fill(data.password)
  const response = page.waitForResponse((r) => r.url().endsWith('/auth/login'))
  await page.getByRole('button', { name: 'Mở workspace', exact: true }).click()
  expect((await response).status()).toBe(200)
  await expect(page.locator('.workspace-shell')).toBeVisible()
  await page.reload()
  await expect(page.locator('.workspace-shell')).toBeVisible()
  if (info.project.use.viewport.width < 680) await page.getByLabel('Tài khoản và phiên làm việc').click()
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page.locator('.secure-gateway')).toBeVisible()
  await page.reload()
  await expect(page.locator('.secure-gateway')).toBeVisible()
  const status = await page.evaluate(async (base) => (await fetch(`${base}/api/v1/farms/`, { credentials: 'include' })).status, api)
  expect(status).toBe(401)
})

for (const [index, role, status] of [[0, 'grower', 200], [1, 'organization_admin', 200], [2, 'inspector', 403]]) {
  test(`real demo ${role}: farm permission and tenant response`, async ({ page }, info) => {
    await demo(page, index)
    await navigate(page, 'Security X-Ray')
    const response = page.waitForResponse((r) => r.url().endsWith('/api/v1/farms/'))
    await page.getByRole('button', { name: 'Gửi GET thực', exact: true }).click()
    const actual = await response
    expect(actual.status()).toBe(status)
    await expect(page.locator('.xray-result')).toContainText(String(status))
    if (status === 200) {
      const records = await actual.json()
      expect(records.length).toBeGreaterThan(0)
      expect(records.every((record) => record.organization_id === organizations[role])).toBeTruthy()
    } else {
      await expect(page.locator('.xray-layer-blocked strong')).toHaveText('RBAC')
      await navigate(page, 'Farm Atlas')
      await expect(page.getByRole('button', { name: 'Thêm thửa', exact: true })).toHaveCount(0)
    }
    await page.screenshot({ path: info.outputPath(`real-${role}.png`), fullPage: true, animations: 'disabled' })
  })
}

test('real farm create/edit persists stable UUID; other tenant cannot list or access it', async ({ page, playwright }) => {
  await demo(page, 0)
  await navigate(page, 'Farm Atlas')
  const name = `Browser QA ${crypto.randomUUID().slice(0, 8)}`
  await page.getByRole('button', { name: 'Thêm thửa', exact: true }).click()
  await page.getByLabel('Tên vùng trồng', { exact: false }).fill(name)
  await page.getByLabel('Diện tích / ha', { exact: false }).fill('1.2500')
  await page.getByLabel('Vĩ độ', { exact: false }).fill('11.900000')
  await page.getByLabel('Kinh độ', { exact: false }).fill('108.400000')
  const createdResponse = page.waitForResponse((r) => r.url().endsWith('/api/v1/farms/') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Tạo vùng trồng', exact: true }).click()
  const createdHttp = await createdResponse
  expect(createdHttp.status()).toBe(201)
  const created = await createdHttp.json()
  await expect(page.locator('.identity-seal code')).toHaveText(created.id)
  await page.getByRole('button', { name: 'Sửa bản ghi vùng trồng', exact: false }).click()
  await page.getByLabel('Tên vùng trồng', { exact: false }).fill(`${name} updated`)
  await page.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
  await expect(page.locator('.atlas-inspector h2')).toHaveText(`${name} updated`)
  await expect(page.locator('.identity-seal code')).toHaveText(created.id)
  await page.reload()
  await navigate(page, 'Farm Atlas')
  await page.getByRole('button', { name: 'Danh sách', exact: true }).click()
  await expect(page.getByRole('table')).toContainText(`${name} updated`)
  const other = await playwright.request.newContext({ baseURL: api })
  try {
    const login = await other.post('/api/v1/auth/demo-login', { data: { email: 'admin@mocchau.vn' } })
    expect(login.status()).toBe(200)
    const token = login.headers()['x-session-token']
    const list = await other.get('/api/v1/farms/', { headers: { 'X-Session-Token': token } })
    expect(list.status()).toBe(200)
    expect((await list.json()).some((farm) => farm.id === created.id)).toBeFalsy()
    const access = await other.get(`/api/v1/farms/${created.id}`, { headers: { 'X-Session-Token': token } })
    expect(access.status()).toBe(403)
  } finally { await other.dispose() }
})
