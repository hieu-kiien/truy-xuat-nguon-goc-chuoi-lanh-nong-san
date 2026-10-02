import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '../src/App'
import { createPreviewTransport, PREVIEW_USERS } from './mockBackend'
import '../src/styles/tokens.css'
import '../src/styles/base.css'
import '../src/styles/shell.css'
import '../src/styles/gateway.css'
import '../src/styles/gateway-journey.css'
import '../src/styles/visualizations.css'
import '../src/styles/responsive.css'
import '../src/styles/journey.css'
import '../src/styles/evidence.css'
import '../src/styles/atlas.css'
import '../src/styles/motion.css'
import './preview.css'

const params = new URLSearchParams(location.search)
const role = PREVIEW_USERS.find((user) => user.role === params.get('role'))?.role ?? null
const transport = createPreviewTransport(role)
// Deliberate test double: never delegates to real network, regardless of configured API URL.
window.fetch = transport.fetch
if (params.get('theme')) localStorage.setItem('ttcs_theme', params.get('theme') === 'dark' ? 'dark' : 'light')
if (params.get('motion') === 'reduce') {
  document.documentElement.dataset.qaReducedMotion = 'true'
  const nativeMatchMedia = window.matchMedia.bind(window)
  window.matchMedia = (query) => { const media = nativeMatchMedia(query); if (query === '(prefers-reduced-motion: reduce)') Object.defineProperty(media, 'matches', { value: true }); return media }
}

export function Controls() {
  return <aside className="qa-banner" aria-label="Visual QA controls"><div><strong>VISUAL QA / DỮ LIỆU TỔNG HỢP</strong><p>Không kết nối backend. CRUD chỉ trong bộ nhớ. Không nhập mật khẩu thật. Đây không phải chứng minh RBAC/RLS của PostgreSQL.</p></div><nav aria-label="Chọn trạng thái QA"><a href="preview.html">Gateway</a>{PREVIEW_USERS.map((user) => <a key={user.role} href={`preview.html?role=${user.role}`}>{user.role}</a>)}<a href={`preview.html?role=${role ?? ''}&theme=dark`}>Dark</a><a href={`preview.html?role=${role ?? ''}&theme=light&motion=reduce`}>Giảm motion (QA)</a></nav><label><input type="checkbox" onChange={(event) => transport.setFailure(event.target.checked)} />API 503 tổng hợp</label></aside>
}
ReactDOM.createRoot(document.getElementById('preview-controls')!).render(<Controls />)
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
