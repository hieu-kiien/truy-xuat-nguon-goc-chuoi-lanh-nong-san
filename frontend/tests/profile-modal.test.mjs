import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

// Môi trường kiểm thử render tĩnh phía máy chủ
const server = await createServer({
  root: fileURLToPath(new URL('..', import.meta.url)),
  cacheDir: fileURLToPath(new URL('../node_modules/.vite-profile-tests', import.meta.url)),
  configFile: false,
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false, ws: false },
})
after(() => server.close())

globalThis.window = { location: { search: '' } }
const load = async (name) => (await server.ssrLoadModule(`/src/components/${name}.tsx`))[name]
const html = (component, props) => renderToStaticMarkup(React.createElement(component, props))

const makeUser = (role, full_name = 'Nguyễn Văn Nông', org = 'Nông trại An Bình', orgType = 'farm') => ({
  id: 'usr-demo-001',
  email: 'farmer@nongtrai.vn',
  full_name,
  organization_id: 'org-demo-001',
  organization_name: org,
  organization_type: orgType,
  role,
})

test('topbar renders accessible avatar trigger button for current user', async () => {
  const WorkspaceTopbar = await load('WorkspaceTopbar')
  const output = html(WorkspaceTopbar, {
    user: makeUser('grower', 'Trần Thị Thu'),
    activeTab: 'lots',
    canReadFarms: true,
    searchQuery: '',
    isDark: false,
    onToggleSidebar: () => {},
    onSearchChange: () => {},
    onRefresh: () => {},
    onToggleTheme: () => {},
  })

  // Có nút avatar, có aria-haspopup="dialog" và aria-label chứa tên người dùng
  assert.match(output, /class="topbar-avatar-btn"/)
  assert.match(output, /aria-haspopup="dialog"/)
  assert.match(output, /aria-label="Hồ sơ người dùng Trần Thị Thu"/)
  // Ký tự viết tắt chữ cái đầu
  assert.match(output, />T<\/span>/)
})

test('ProfileModal renders full name, email, Vietnamese role label and organization', async () => {
  const ProfileModal = await load('ProfileModal')
  const output = html(ProfileModal, {
    user: makeUser('grower', 'Lê Văn Trồng', 'Hợp tác xã Rau Sạch', 'cooperative'),
    onClose: () => {},
  })

  // Thẻ dialog có aria-labelledby trỏ tới id tiêu đề
  assert.match(output, /<dialog[^>]*aria-labelledby="profile-modal-title"/)
  assert.match(output, /id="profile-modal-title"[^>]*>Hồ sơ tài khoản<\/h2>/)

  // Hiển thị đầy đủ họ tên và email
  assert.match(output, /Lê Văn Trồng/)
  assert.match(output, /farmer@nongtrai\.vn/)

  // Nhãn vai trò tiếng Việt trang trọng: Nông hộ
  assert.match(output, /Nông hộ/)
  assert.match(output, /Hợp tác xã Rau Sạch/)

  // Nút đóng hộp thoại có aria-label
  assert.match(output, /aria-label="Đóng hộp thoại hồ sơ"/)
})

test('ProfileModal maps each role code to polite Vietnamese label', async () => {
  const ProfileModal = await load('ProfileModal')

  const rolesToTest = [
    { role: 'grower', expectedLabel: 'Nông hộ' },
    { role: 'cooperative', expectedLabel: 'Hợp tác xã' },
    { role: 'transporter', expectedLabel: 'Vận chuyển' },
    { role: 'distributor', expectedLabel: 'Phân phối' },
    { role: 'inspector', expectedLabel: 'Thanh tra' },
    { role: 'organization_admin', expectedLabel: 'Quản trị đơn vị' },
    { role: 'system_admin', expectedLabel: 'Quản trị hệ thống' },
  ]

  for (const item of rolesToTest) {
    const output = html(ProfileModal, {
      user: makeUser(item.role),
      onClose: () => {},
    })
    assert.match(
      output,
      new RegExp(item.expectedLabel),
      `Vai trò ${item.role} phải được dịch thành "${item.expectedLabel}"`
    )
  }
})

test('DashboardHomePanel renders real role-aware KPIs without hardcoded fake fleet or humidity', async () => {
  const DashboardHomePanel = await load('DashboardHomePanel')
  const output = html(DashboardHomePanel, {
    user: makeUser('system_admin', 'Vũ Hải Đăng', 'Cục Quản trị Hệ thống Chuỗi lạnh Quốc gia', 'administration'),
    onTabChange: () => {},
    onOpenLot: () => {},
  })

  assert.match(output, /Xin chào, Vũ Hải Đăng/)
  assert.match(output, /LÔ ĐANG LƯU HÀNH/)
  assert.match(output, /TIẾP NHẬN &amp; BÀN GIAO/)
  assert.match(output, /CHUỖI LẠNH VẬN CHUYỂN/)
  assert.match(output, /TOÀN VẸN CHUỖI BĂM/)
  assert.doesNotMatch(output, /29C-882\.14/)
  assert.doesNotMatch(output, /51D-334\.89/)
  assert.doesNotMatch(output, /Độ ẩm/)
})

test('LoginView and PublicTracePage offer real seeded lot codes without vaporware buttons', async () => {
  const LoginView = await load('LoginView')
  const PublicTracePage = await load('PublicTracePage')

  const loginHtml = html(LoginView, {
    backendOnline: true,
    isDark: false,
    onToggleTheme: () => {},
    onLoginSuccess: () => {},
    onNotify: () => {},
  })
  assert.match(loginHtml, /XRVT7PXY/)
  assert.match(loginHtml, /BZ84PFZ3/)
  assert.match(loginHtml, /JQMB7MZ9/)
  assert.doesNotMatch(loginHtml, /Sắp ra mắt/)
  assert.doesNotMatch(loginHtml, /Quên mật khẩu\?/)

  const traceHtml = html(PublicTracePage, {})
  assert.match(traceHtml, /XRVT7PXY/)
  assert.match(traceHtml, /BZ84PFZ3/)
  assert.match(traceHtml, /JQMB7MZ9/)
  assert.match(traceHtml, /DB99A7YK/)
})
