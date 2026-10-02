import { ROLE_LABELS, ROLE_PERMISSIONS, type RoleCode, type SessionUser } from '../types'
import { API_BASE_URL } from '../services/api'
import { Icon } from './Icons'

export type AccessProbeState =
  | { status: 'idle' }
  | { status: 'pending' }
  | { status: 'allowed'; httpStatus: 200; visibleRows: number; records: Array<{ id: string; name: string; organization_id: string }> }
  | { status: 'blocked'; httpStatus: 403; message: string }
  | { status: 'unauthenticated'; httpStatus: 401; message: string }
  | { status: 'error'; httpStatus: number | null; message: string }

interface SecurityXrayProps {
  user: SessionUser
  probe: AccessProbeState
  onProbe: () => void
  demoLoginEnabled: boolean
}

const ROLES: RoleCode[] = [
  'grower',
  'organization_admin',
  'inspector',
  'cooperative',
  'transporter',
  'distributor',
  'system_admin',
]

const LAYERS = [
  { id: 'identity', name: 'User', detail: 'Identity' },
  { id: 'session', name: 'Session', detail: 'HttpOnly cookie' },
  { id: 'fastapi', name: 'FastAPI', detail: 'GET /api/v1/farms/' },
  { id: 'rbac', name: 'RBAC', detail: 'farms:read' },
  { id: 'tenant', name: 'Tenant context', detail: 'organization_id' },
  { id: 'rls', name: 'PostgreSQL RLS', detail: 'tenant filter' },
  { id: 'result', name: 'Result', detail: 'visible rows' },
]

function nodeState(id: string, probe: AccessProbeState): string {
  if (probe.status === 'idle') return 'idle'
  if (probe.status === 'pending') return id === 'identity' ? 'passed' : 'pending'
  if (probe.status === 'blocked') {
    if (['identity', 'session', 'fastapi'].includes(id)) return 'passed'
    if (id === 'rbac') return 'blocked'
    return 'stopped'
  }
  if (probe.status === 'unauthenticated') {
    if (id === 'identity') return 'passed'
    if (id === 'session') return 'blocked'
    return 'stopped'
  }
  if (probe.status === 'allowed') return 'passed'
  return id === 'identity' ? 'passed' : 'error'
}

export function SecurityXray({ user, probe, onProbe, demoLoginEnabled }: SecurityXrayProps) {
  const currentPermissions = ROLE_PERMISSIONS[user.role] ?? []
  const resultCopy =
    probe.status === 'allowed'
      ? `200 OK · API trả ${probe.visibleRows} bản ghi; đối chiếu organization bên dưới.`
      : probe.status === 'blocked'
        ? `403 Forbidden · request dừng ở RBAC trước khi truy vấn bảng farms. ${probe.message}`
        : probe.status === 'unauthenticated'
          ? `401 Unauthorized · không tạo tenant query. ${probe.message}`
          : probe.status === 'error'
            ? `${probe.httpStatus ? `HTTP ${probe.httpStatus}` : 'Request lỗi'} · ${probe.message}`
            : probe.status === 'pending'
              ? 'Đang gửi request thực tới backend…'
              : 'Chạy GET thực; sơ đồ bên trong mô tả kiến trúc từ code backend.'

  return (
    <section className="view-stack" data-demo-target="security" aria-labelledby="security-title">
      <div className="view-heading view-heading-spread">
        <div><p className="eyebrow">Mission 04 / Security X-Ray</p><h1 id="security-title">Một request. Bảy lớp kiểm tra.</h1><p className="view-intro">Theo dõi kết quả request thực. Đường xử lý nội bộ là mô hình kiến trúc, không phải từng span đo trực tiếp.</p></div>
        <span className="security-stamp"><Icon name="shield" size={16} />SESSION ACTIVE · {user.role.toUpperCase()}</span>
      </div>

      <section className="surface xray-surface" aria-labelledby="xray-heading">
        <div className="section-heading"><div><span className="micro-label">LIVE REQUEST / READ ONLY</span><h2 id="xray-heading">User → Session → FastAPI → RBAC → Tenant → RLS → Result</h2></div><a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer" className="text-action">OpenAPI <Icon name="arrow" size={14} /></a></div>
        <ol className={`xray-flow xray-${probe.status}`} aria-label="Các lớp xử lý request theo thứ tự">
          {LAYERS.map((layer, index) => {
            const state = nodeState(layer.id, probe)
            const stopHere = (probe.status === 'blocked' && layer.id === 'rbac') || (probe.status === 'unauthenticated' && layer.id === 'session')
            return <li key={layer.id} className={`xray-layer xray-layer-${state} ${stopHere ? 'xray-stop' : ''}`}>
              <div className="xray-node"><span className="xray-node-index">0{index + 1}</span><span className="xray-node-icon">{state === 'passed' ? <Icon name="check" size={16} /> : layer.id === 'tenant' ? <Icon name="atlas" size={17} /> : layer.id === 'rbac' || layer.id === 'rls' ? <Icon name="shield" size={17} /> : layer.id === 'result' ? <Icon name="layers" size={17} /> : <Icon name="journey" size={17} />}</span><strong>{layer.name}</strong><small>{layer.detail}</small>{stopHere && <b className="xray-stop-tag">{probe.status === 'unauthenticated' ? '401' : '403'} · STOP</b>}{state === 'stopped' && <b className="xray-stop-tag">NOT REACHED</b>}</div>
              {index < LAYERS.length - 1 && <span className={`xray-connector xray-connector-${state}`} aria-hidden="true"><Icon name="arrow" size={16} /></span>}
            </li>
          })}
        </ol>

        <div className={`xray-result xray-result-${probe.status}`} role="status" aria-live="polite"><span className="xray-result-mark">{probe.status === 'allowed' ? <Icon name="check" size={18} /> : probe.status === 'blocked' || probe.status === 'unauthenticated' ? <Icon name="close" size={18} /> : <Icon name="journey" size={18} />}</span><div><strong>{resultCopy}</strong><small>{probe.status === 'blocked' ? 'RBAC kiểm tra quyền farms:read ở route dependency. Truy vấn farms theo tenant không được thực thi; vị trí dừng được suy ra từ route dependency trong backend.' : probe.status === 'allowed' ? `Tenant: ${user.organization_id} · Đây là rows nhận từ API; cần test database riêng để chứng minh RLS isolation.` : 'Request không bị trì hoãn để tạo animation; sơ đồ đổi theo response thật.'}</small></div><button type="button" className="button button-primary" onClick={onProbe} disabled={probe.status === 'pending'}><Icon name="play" size={15} />{probe.status === 'pending' ? 'Đang gửi…' : 'Gửi GET thực'}</button></div>
      </section>

      <section className="tenant-membranes" aria-label="Kết quả request và ranh giới tenant"><div className="tenant-current"><span className="micro-label">TENANT HIỆN TẠI</span><h2>{user.organization_name}</h2><code>{user.organization_id}</code><div className="tenant-result-records">{probe.status === 'allowed' ? probe.records.length ? probe.records.map((record) => <article key={record.id}><Icon name="agro" size={18} /><div><strong>{record.name}</strong><code>{record.id}</code><small>{record.organization_id === user.organization_id ? 'Organization khớp phiên hiện tại' : 'CẢNH BÁO: organization khác phiên hiện tại'}</small></div></article>) : <p>API trả danh sách rỗng.</p> : <p>{probe.status === 'blocked' ? '403: không nhận được dữ liệu farms.' : probe.status === 'pending' ? 'Đang chờ response…' : 'Chưa có kết quả GET hợp lệ.'}</p>}</div></div><div className="tenant-other"><Icon name="shield" size={28} /><h2>Phía ngoài tenant</h2><p>Không tải dữ liệu tổ chức khác để minh họa. Ranh giới này mô tả chính sách đã đọc trong backend.</p><span>RBAC + TENANT CONTEXT + RLS</span></div></section>
      <div className="security-lower-grid">
        <section className="surface session-context" aria-labelledby="session-heading">
          <div className="section-heading"><div><span className="micro-label">SESSION CONTEXT</span><h2 id="session-heading">Danh tính và tenant</h2></div><span className="state-pill state-normal">Authenticated</span></div>
          <dl className="detail-list"><div><dt>Người dùng</dt><dd>{user.full_name}<small>{user.email}</small></dd></div><div><dt>Vai trò</dt><dd>{ROLE_LABELS[user.role]} <code>{user.role}</code></dd></div><div><dt>Tổ chức</dt><dd>{user.organization_name}<small>{user.organization_type}</small></dd></div><div><dt>Tenant ID</dt><dd><code>{user.organization_id}</code></dd></div><div><dt>Quyền hiện tại</dt><dd className="permission-list">{currentPermissions.map((permission) => <code key={permission}>{permission}</code>)}</dd></div></dl>
          <p className="security-footnote">Bảng kiểm tra không hiển thị session token. Phiên do backend phát hành; quyền được kiểm tra ở mỗi request.</p>
        </section>

        <section className="surface permission-surface" aria-labelledby="permission-heading">
          <div className="section-heading"><div><span className="micro-label">ROLE / PERMISSION MAP</span><h2 id="permission-heading">Ma trận farms</h2></div><span className="list-count">7 vai trò</span></div>
          <div className="permission-table-wrap"><table className="permission-table"><thead><tr><th scope="col">Role</th><th scope="col">Phạm vi</th><th scope="col">farms:read</th><th scope="col">farms:write</th></tr></thead><tbody>{ROLES.map((role) => { const permissions = ROLE_PERMISSIONS[role] ?? []; const selected = role === user.role; return <tr key={role} className={selected ? 'permission-row-current' : ''}><th scope="row"><code>{role}</code>{selected && <span>Phiên này</span>}</th><td>{ROLE_LABELS[role]}</td><td><span className={`permission-cell ${permissions.includes('farms:read') ? 'permission-granted' : 'permission-denied'}`}><i />{permissions.includes('farms:read') ? 'Được cấp' : 'Bị chặn'}</span></td><td><span className={`permission-cell ${permissions.includes('farms:write') ? 'permission-granted' : 'permission-denied'}`}><i />{permissions.includes('farms:write') ? 'Được cấp' : 'Bị chặn'}</span></td></tr> })}</tbody></table></div>
          {!demoLoginEnabled && <p className="security-footnote">Chuyển vai trò demo cần cấu hình demo login cùng backend; không có mật khẩu demo trong frontend.</p>}
        </section>
      </div>
    </section>
  )
}
