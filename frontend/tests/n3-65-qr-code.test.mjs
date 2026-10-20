import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import QRCode from 'qrcode'

const server = await createServer({
  root: fileURLToPath(new URL('..', import.meta.url)),
  cacheDir: fileURLToPath(new URL('../node_modules/.vite-task-tests-qr', import.meta.url)),
  configFile: false,
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false },
})
after(() => server.close())

globalThis.window = {
  location: {
    origin: 'https://agrochain.vn',
    pathname: '/truy-xuat',
    search: '',
  },
  setTimeout: (callback, delay) => setTimeout(callback, delay),
}

const load = async (name) => (await server.ssrLoadModule(`/src/components/${name}.tsx`))[name]
const html = (component, props) => renderToStaticMarkup(React.createElement(component, props))

test('N3-65: URL công khai dùng mã lô trên trang /truy-xuat, không dùng ID tự tăng', async () => {
  const { displayLotCode, getLotPublicUrl } = await server.ssrLoadModule('/src/utils/qr.ts')

  const lotWithCode = { id: '987fcdeb-51a2-4c3d-be78-0123456789ab', lot_code: 'K3M7P2QZ' }
  assert.equal(displayLotCode(lotWithCode), 'K3M7P2QZ')
  assert.equal(getLotPublicUrl(lotWithCode), 'https://agrochain.vn/truy-xuat?code=K3M7P2QZ')

  // Lô cũ chưa có lot_code: dùng 8 ký tự đầu UUID, không dùng ID số tự tăng.
  const lotWithoutCode = { id: 'a1b2c3d4-5678-90ab-cdef-1234567890ab', lot_code: null }
  assert.equal(displayLotCode(lotWithoutCode), 'a1b2c3d4')
  assert.equal(getLotPublicUrl(lotWithoutCode), 'https://agrochain.vn/truy-xuat?code=a1b2c3d4')

  // Mã đặc biệt (nếu backend đổi định dạng) vẫn phải được encode an toàn.
  const lotWithUnsafeCode = { id: 'a1b2c3d4-5678-90ab-cdef-1234567890ab', lot_code: 'A B&1' }
  assert.equal(getLotPublicUrl(lotWithUnsafeCode), 'https://agrochain.vn/truy-xuat?code=A%20B%261')
})

test('N3-65: SVG được gắn kích thước in 30mm và giữ nguyên viewBox', async () => {
  const { applyPrintSize, QR_PRINT_SIZE_MM } = await server.ssrLoadModule('/src/utils/qr.ts')
  assert.equal(QR_PRINT_SIZE_MM, 30)

  const svg = await QRCode.toString('https://agrochain.vn/truy-xuat?code=K3M7P2QZ', {
    type: 'svg',
    margin: 4,
    errorCorrectionLevel: 'Q',
  })
  const printSvg = applyPrintSize(svg)

  assert.match(printSvg, /^<svg[^>]*width="30mm"[^>]*height="30mm"/)
  assert.match(printSvg, /viewBox="0 0 [0-9]+ [0-9]+"/)
  assert.doesNotMatch(printSvg, /width="350"/)
  assert.match(printSvg, /<\/svg>\s*$/)
})

test('N3-65: mã QR dùng quiet zone 4 module, mức sửa lỗi Q và PNG đủ nét để in 3cm', async () => {
  const { QR_ERROR_CORRECTION, QR_PNG_SIZE_PX, QR_QUIET_ZONE_MODULES } =
    await server.ssrLoadModule('/src/utils/qr.ts')

  assert.equal(QR_QUIET_ZONE_MODULES, 4)
  assert.equal(QR_ERROR_CORRECTION, 'Q')
  // 1024px trên 30mm ≈ 867 DPI, vượt xa ngưỡng 300 DPI khi in tem.
  assert.ok(QR_PNG_SIZE_PX / (30 / 25.4) >= 300)

  const url = 'https://agrochain.vn/truy-xuat?code=K3M7P2QZ'
  const png = await QRCode.toDataURL(url, {
    width: QR_PNG_SIZE_PX,
    margin: QR_QUIET_ZONE_MODULES,
    errorCorrectionLevel: QR_ERROR_CORRECTION,
  })
  assert.match(png, /^data:image\/png;base64,/)
  assert.ok(png.length > 5000)

  const svg = await QRCode.toString(url, {
    type: 'svg',
    margin: QR_QUIET_ZONE_MODULES,
    errorCorrectionLevel: QR_ERROR_CORRECTION,
  })
  // 4 module mỗi phía: viewBox rộng = số module của mã + 8.
  const [, viewBoxWidth] = /viewBox="0 0 (\d+) \d+"/.exec(svg)
  assert.ok(Number(viewBoxWidth) > 8)
  assert.equal((Number(viewBoxWidth) - 8 - 1) % 4, 0) // 21 + 4*(version-1)
})

test('N3-65: LotQrPanel hiển thị mã lô, URL công khai, kích thước in và nút tải PNG/SVG', async () => {
  const LotQrPanel = await load('LotQrPanel')
  const output = html(LotQrPanel, {
    lot: {
      id: '89d69962-fa86-59d7-8adf-26cb56fa9ef4',
      lot_code: 'K3M7P2QZ',
      name: 'Xoài Cát Chu',
      product: { name: 'Xoài Cát Chu', unit: 'kg' },
    },
  })

  assert.match(output, /aria-label="Sinh mã QR cho lô hàng"/)
  assert.match(output, /K3M7P2QZ/)
  assert.match(output, /https:\/\/agrochain\.vn\/truy-xuat\?code=K3M7P2QZ/)
  assert.match(output, /30 × 30 mm/)
  assert.match(output, /aria-label="Tải mã QR định dạng PNG"/)
  assert.match(output, /aria-label="Tải mã QR định dạng SVG"/)
  assert.doesNotMatch(output, /Lô chưa có mã công khai/)
})

test('N3-65: LotQrPanel cảnh báo khi lô chưa có mã công khai', async () => {
  const LotQrPanel = await load('LotQrPanel')
  const output = html(LotQrPanel, {
    lot: {
      id: '89d69962-fa86-59d7-8adf-26cb56fa9ef4',
      lot_code: null,
      name: 'Thanh Long',
    },
  })

  assert.match(output, /Lô chưa có mã công khai/)
  assert.match(output, /89d69962/)
})

test('N3-65: trang /truy-xuat tự điền mã lô từ tham số ?code= khi quét tem', async () => {
  const PublicTracePage = await load('PublicTracePage')

  window.location.search = '?code=k3m7p2qz'
  const withCode = html(PublicTracePage, {})
  assert.match(withCode, /id="public-lot-code"/)
  assert.match(withCode, /value="K3M7P2QZ"/)

  window.location.search = ''
  const withoutCode = html(PublicTracePage, {})
  assert.match(withoutCode, /value=""/)

  // Mã không hợp lệ trong URL không được đẩy vào ô nhập.
  window.location.search = '?code=ab!'
  const withInvalid = html(PublicTracePage, {})
  assert.match(withInvalid, /value=""/)
})
