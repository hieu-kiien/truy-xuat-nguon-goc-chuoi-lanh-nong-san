import { test, expect } from 'playwright/test'

// These exercise the real React components against an explicitly synthetic transport.
// They do not establish backend authentication, RBAC or PostgreSQL RLS correctness.
const go = async (page, role = 'grower', project) => {
  const theme = project.use.colorScheme === 'dark' ? 'dark' : 'light'
  await page.goto(`/preview.html?role=${role}&theme=${theme}`)
  await expect(page.locator('.workspace-shell')).toBeVisible()
  await expect(page.locator('.lens-seal')).toContainText('Seal hợp lệ')
}
const navigate = async (page, name) => {
  await page.getByRole('button', { name, exact: true }).click()
  await expect(page.locator('main h1')).toBeFocused()
}
const capture = async (page, info, name) => {
  await page.screenshot({ path: info.outputPath(`${name}.png`), fullPage: true, animations: 'disabled' })
  await info.attach(name, { path: info.outputPath(`${name}.png`), contentType: 'image/png' })
}
const noPageOverflow = async (page) => {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy()
}

test('major screens: composition, theme, viewport and console errors', async ({ page }, info) => {
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  await go(page, 'grower', info.project)
  await noPageOverflow(page)
  await capture(page, info, 'trace')
  for (const [name, screen] of [['Farm Atlas', 'atlas'], ['Cold Chain', 'journey'], ['Forensics', 'forensics'], ['Security X-Ray', 'security'], ['Demo mode', 'field-guide']]) {
    await navigate(page, name)
    if (screen === 'security') {
      await page.getByRole('button', { name: 'Gửi GET thực', exact: true }).click()
      await expect(page.locator('.xray-result')).toContainText('200 OK')
    }
    await noPageOverflow(page)
    await capture(page, info, screen)
  }
  expect(errors).toEqual([])
})

test('a time cursor preserves the nearest event across spatial, time and hash lenses', async ({ page }, info) => {
  await go(page, 'grower', info.project)
  const range = page.getByRole('slider', { name: 'Con trỏ thời gian' })
  await range.fill('700')
  await expect(page.locator('.lens-event-number')).toHaveText('03')
  await expect(page.locator('.time-control-label')).toContainText('11:36 UTC')
  await page.getByRole('button', { name: 'Thời gian', exact: true }).click()
  await expect(page.getByRole('slider', { name: 'Con trỏ thời gian' })).toHaveValue('700')
  await page.getByRole('button', { name: 'Bằng chứng', exact: true }).click()
  await expect(page.locator('.chain-block-selected .chain-block-index')).toHaveText('BLOCK / 03')
  await page.getByRole('button', { name: 'Mô phỏng sửa trường temp_c' }).click()
  await expect(page.locator('.chain-block-mismatch')).toHaveCount(1)
  await expect(page.locator('.chain-block-broken')).toHaveCount(1)
  await expect(page.locator('.diff-after')).toContainText('99.9')
  await capture(page, info, 'tamper-diff')
  await page.locator('.chain-block').last().click()
  await expect(page.locator('.ancestry-row').nth(2)).toContainText('FRACTURED')
  await expect(page.locator('.ancestry-row').nth(3)).toContainText('NO ANCESTOR')
  await page.getByRole('button', { name: 'Khôi phục fixture gốc' }).click()
  await expect(page.locator('.integrity-overview')).toContainText('4 / 4')
  await page.getByRole('button', { name: 'Phát toàn bộ xác minh' }).click()
  await expect(page.locator('.verification-progress')).toContainText('STEP 4 OF 4')
  await expect(page.getByRole('button', { name: 'Phát toàn bộ xác minh' })).toBeVisible()
})

test('temperature excursion is independent from cryptographic tampering', async ({ page }, info) => {
  await go(page, 'grower', info.project)
  await navigate(page, 'Cold Chain')
  await page.getByRole('button', { name: 'Tạo ngoại lệ nhiệt cục bộ' }).click()
  await page.getByRole('slider', { name: 'Con trỏ thời gian' }).fill('563')
  await expect(page.locator('.journey-reading')).toContainText('9.9')
  await expect(page.locator('.lens-seal')).toContainText('Seal hợp lệ')
  await page.getByRole('button', { name: 'Bằng chứng', exact: true }).click()
  await expect(page.locator('.integrity-overview')).toContainText('4 / 4')
  await expect(page.locator('.integrity-separation')).toContainText('không phải lỗi toàn vẹn')
})

test('Atlas create and edit preserve the target UUID while another marker is focused', async ({ page }, info) => {
  await go(page, 'grower', info.project)
  await navigate(page, 'Farm Atlas')
  const originalId = await page.locator('.identity-seal code').textContent()
  await page.getByRole('button', { name: 'Sửa bản ghi vùng trồng' }).click()
  await expect(page.getByLabel('Tên vùng trồng', { exact: false })).toBeFocused()
  await page.locator('.farm-marker').nth(1).focus()
  await page.getByLabel('Tên vùng trồng', { exact: false }).fill('Vùng đổi tên trong QA')
  await page.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
  await expect(page.locator('.atlas-inspector h2')).toHaveText('Vùng đổi tên trong QA')
  await expect(page.locator('.identity-seal code')).toHaveText(originalId)
  await page.getByRole('button', { name: 'Thêm thửa', exact: true }).click()
  await page.getByLabel('Tên vùng trồng', { exact: false }).fill('Thửa mới QA')
  await page.getByLabel('Diện tích / ha', { exact: false }).fill('1.25')
  await page.getByLabel('Vĩ độ', { exact: false }).fill('11.9')
  await page.getByLabel('Kinh độ', { exact: false }).fill('108.4')
  await page.getByRole('button', { name: 'Tạo vùng trồng', exact: true }).click()
  await expect(page.locator('.atlas-inspector h2')).toHaveText('Thửa mới QA')
  await expect(page.locator('.identity-seal code')).not.toHaveText(originalId)
  await capture(page, info, 'atlas-created')
  await page.getByRole('button', { name: 'Danh sách', exact: true }).click()
  await expect(page.getByRole('table')).toContainText('Thửa mới QA')
  await page.getByRole('button', { name: 'So sánh', exact: true }).click()
  await page.locator('.compare-pick').nth(0).click()
  await page.locator('.compare-pick').nth(1).click()
  await expect(page.locator('.compare-card')).toHaveCount(2)
  await capture(page, info, 'atlas-compare')
})

for (const [role, result, count] of [['grower', '200 OK', 3], ['organization_admin', '200 OK', 1], ['inspector', '403 Forbidden', 0]]) {
  test(`synthetic ${role} request follows its actual HTTP outcome`, async ({ page }, info) => {
    await go(page, role, info.project)
    await navigate(page, 'Security X-Ray')
    await page.getByRole('button', { name: 'Gửi GET thực', exact: true }).click()
    await expect(page.locator('.xray-result')).toContainText(result)
    await expect(page.locator('.tenant-result-records article')).toHaveCount(count)
    if (role === 'inspector') {
      await expect(page.locator('.xray-layer-blocked strong')).toHaveText('RBAC')
      await expect(page.locator('.xray-layer-stopped')).toHaveCount(3)
    }
    await capture(page, info, `security-${role}`)
    await page.getByRole('checkbox', { name: 'API 503 tổng hợp' }).check()
    await page.getByRole('button', { name: 'Gửi GET thực', exact: true }).click()
    await expect(page.locator('.xray-result')).toContainText('HTTP 503')
  })
}

test('command palette and guided mode trap focus and allow keyboard exit', async ({ page }, info) => {
  await go(page, 'grower', info.project)
  await page.keyboard.press('Control+k')
  const dialog = page.getByRole('dialog', { name: 'Command palette' })
  await expect(dialog).toBeVisible()
  await expect(page.getByRole('combobox')).toBeFocused()
  await page.getByRole('combobox').fill('Farm Atlas')
  await page.keyboard.press('Enter')
  await expect(dialog).toBeHidden()
  await expect(page.locator('main h1')).toBeFocused()
  await navigate(page, 'Demo mode')
  await page.getByRole('button', { name: 'Bắt đầu dẫn chuyện', exact: false }).click()
  const guide = page.getByRole('dialog')
  await expect(guide).toBeVisible()
  await page.keyboard.press('Shift+Tab')
  expect(await guide.evaluate((element) => element.contains(document.activeElement))).toBeTruthy()
  await page.keyboard.press('Escape')
  await expect(guide).toBeHidden()
  await expect(page.locator('.workspace-shell')).not.toHaveAttribute('inert', '')
})

test('native reduced-motion preference disables choreography', async ({ page }, info) => {
  test.skip(info.project.name !== 'reduced-motion', 'Native motion emulation project only')
  await go(page, 'grower', info.project)
  expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBeTruthy()
  expect(parseFloat(await page.locator('.journey-map-camera').evaluate((element) => getComputedStyle(element).transitionDuration))).toBeLessThanOrEqual(.001)
  await navigate(page, 'Forensics')
  await page.getByRole('button', { name: 'Phát toàn bộ xác minh' }).click()
  await expect(page.locator('.verification-progress')).toContainText('STEP 4 OF 4')
})
