import { test, expect } from 'playwright/test'
const visit = async (page) => {
  await page.goto('/')
  await expect(page.locator('meta[name="agrochain-build"]')).toHaveAttribute('content', process.env.EXPECTED_COMMIT)
  await expect(page.getByRole('heading', { name: 'Bắt đầu từ nguồn gốc.' })).toBeVisible({ timeout: 90000 })
}
test('deployed Gateway, real Web Crypto and independent heat/tamper', async ({ page }, info) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await visit(page)
  await page.getByRole('button', { name: 'Cho nhiệt độ tăng', exact: true }).click()
  await expect(page.locator('.playground-evidence-heading')).toContainText('Bằng chứng hợp lệ')
  await page.getByRole('button', { name: 'Thử sửa dữ liệu', exact: true }).click()
  await expect(page.locator('.playground-evidence-heading')).toContainText('Hash không khớp')
  await page.locator('.playground-hash-detail summary').click()
  const hashes = await page.locator('.hash-reading code').allTextContents()
  expect(hashes).toHaveLength(2)
  expect(hashes[0]).toMatch(/^[a-f0-9]{64}$/)
  expect(hashes[1]).not.toBe(hashes[0])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy()
  expect(errors).toEqual([])
  await page.screenshot({ path: info.outputPath('gateway-live.png'), fullPage: true, animations: 'disabled' })
})
for (const [index, role, status] of [[0,'grower',200], [1,'organization_admin',200], [2,'inspector',403]]) {
  test('deployed demo '+role+' and farm request', async ({ page }, info) => {
    await visit(page)
    const demo = page.getByRole('button', { name: /^Vào demo/ })
    test.skip((await demo.count()) === 0, 'Demo disabled by the deployed frontend configuration; no credentials are invented.')
    await demo.nth(index).click()
    await expect(page.locator('.workspace-shell')).toBeVisible()
    await page.getByRole('button', { name: 'Security X-Ray', exact: true }).click()
    const response = page.waitForResponse(r => r.url().endsWith('/api/v1/farms/'))
    await page.getByRole('button', { name: 'Gửi GET thực', exact: true }).click()
    expect((await response).status()).toBe(status)
    await expect(page.locator('.xray-result')).toContainText(String(status))
    await page.screenshot({ path: info.outputPath(role+'-live.png'), fullPage: true, animations: 'disabled' })
  })
}
