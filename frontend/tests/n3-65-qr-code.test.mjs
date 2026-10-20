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
    search: '',
  },
}

const load = async (name) => (await server.ssrLoadModule(`/src/components/${name}.tsx`))[name]
const html = (component, props) => renderToStaticMarkup(React.createElement(component, props))

test('N3-65: getLotPublicUrl uses lot_code without auto-increment id', async () => {
  const { getLotPublicUrl, displayLotCode } = await server.ssrLoadModule('/src/utils/qr.ts')
  
  // Test với lot có mã lot_code
  const lotWithCode = { id: '987fcdeb-51a2-4c3d-be78-0123456789ab', lot_code: 'LOT-N3-2026-X01', name: 'Xoài Cát' }
  assert.equal(displayLotCode(lotWithCode), 'LOT-N3-2026-X01')
  assert.equal(getLotPublicUrl(lotWithCode), 'https://agrochain.vn/trace/LOT-N3-2026-X01')
  
  // Test với lot chưa có lot_code (dùng 8 ký tự đầu UUID, không dùng ID số tự tăng)
  const lotWithoutCode = { id: 'a1b2c3d4-5678-90ab-cdef-1234567890ab', lot_code: null, name: 'Thanh Long' }
  assert.equal(displayLotCode(lotWithoutCode), 'a1b2c3d4')
  assert.equal(getLotPublicUrl(lotWithoutCode), 'https://agrochain.vn/trace/a1b2c3d4')

  // Đảm bảo không chứa số nguyên tự tăng
  assert.doesNotMatch(getLotPublicUrl(lotWithCode), /\/trace\/\d+$/)
})

test('N3-65: QRCode library generates high-resolution PNG and scalable vector SVG', async () => {
  const testUrl = 'https://agrochain.vn/trace/LOT-N3-2026-X01'

  // 1. Kiểm tra sinh ảnh PNG với độ phân giải 1024x1024 (~867 DPI ở khổ 3cm, vượt xa chuẩn in ấn 300 DPI)
  const pngDataUrl = await QRCode.toDataURL(testUrl, {
    width: 1024,
    margin: 2,
    errorCorrectionLevel: 'M',
  })
  assert.match(pngDataUrl, /^data:image\/png;base64,/)
  assert.ok(pngDataUrl.length > 5000, 'PNG DataURL phải chứa dữ liệu hình ảnh độ nét cao')

  // 2. Kiểm tra sinh SVG vector (vô hạn độ phân giải khi in)
  const svgOutput = await QRCode.toString(testUrl, {
    type: 'svg',
    margin: 2,
    errorCorrectionLevel: 'M',
  })
  assert.match(svgOutput, /<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)
  assert.match(svgOutput, /viewBox=/)
  assert.match(svgOutput, /<\/svg>\s*$/)
})

test('N3-65: LotQrPanel renders accessible buttons for PNG, SVG downloads and 3cm print recommendation', async () => {
  const LotQrPanel = await load('LotQrPanel')
  const lot = {
    id: '89d69962-fa86-59d7-8adf-26cb56fa9ef4',
    lot_code: 'S34-MANGO-01',
    name: 'Xoài Cát Chu',
    product: { name: 'Xoài Cát Chu', unit: 'kg' },
  }

  const output = html(LotQrPanel, { lot })

  // Tiêu đề và vùng chứa
  assert.match(output, /Sinh mã QR cho lô hàng/)
  assert.match(output, /aria-label="Sinh mã QR cho lô hàng"/)

  // Mã lô và đường dẫn công khai
  assert.match(output, /<code>S34-MANGO-01<\/code>/)
  assert.match(output, /https:\/\/agrochain\.vn\/trace\/S34-MANGO-01/)

  // Hướng dẫn kích thước in 3 cm
  assert.match(output, /3 cm × 3 cm/)

  // Nút tải tệp PNG
  assert.match(output, /Tải về tệp PNG \(Chuẩn in ấn 3cm\)/)
  assert.match(output, /aria-label="Tải về tệp ảnh PNG cho mã QR"/)

  // Nút tải tệp SVG
  assert.match(output, /Tải về tệp SVG \(Vector không vỡ hình\)/)
  assert.match(output, /aria-label="Tải về tệp đồ họa vector SVG cho mã QR"/)
})
