// Synthetic transport for the separate visual QA entry only. Never imported by src/main.tsx.
import { hasPermission, type Farm, type FarmPayload, type RoleCode, type SessionUser } from '../src/types/index.ts'

const ORGANIZATIONS = ['a0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000002', 'c0000000-0000-4000-8000-000000000003']
export const PREVIEW_USERS: SessionUser[] = [
  { id: '10000000-0000-4000-8000-000000000001', email: 'grower@caudat.vn', full_name: 'Nông hộ minh họa', organization_id: ORGANIZATIONS[0], organization_name: 'Cầu Đất · dữ liệu QA', organization_type: 'farm', role: 'grower' },
  { id: '20000000-0000-4000-8000-000000000002', email: 'admin@mocchau.vn', full_name: 'Quản trị minh họa', organization_id: ORGANIZATIONS[1], organization_name: 'Mộc Châu · dữ liệu QA', organization_type: 'cooperative', role: 'organization_admin' },
  { id: '30000000-0000-4000-8000-000000000003', email: 'inspector@chicuc.gov.vn', full_name: 'Thanh tra minh họa', organization_id: ORGANIZATIONS[2], organization_name: 'Kiểm định · dữ liệu QA', organization_type: 'inspection', role: 'inspector' },
]
export const PREVIEW_FARMS: Farm[] = [
  { id: 'f1000000-0000-4000-8000-000000000001', organization_id: ORGANIZATIONS[0], name: 'Đồi dâu Cầu Đất · mẫu QA', area_ha: '3.2500', latitude: '11.924850', longitude: '108.497210' },
  { id: 'f2000000-0000-4000-8000-000000000002', organization_id: ORGANIZATIONS[0], name: 'Vườn rau Trại Mát · mẫu QA', area_ha: '5.4000', latitude: '11.950210', longitude: '108.469410' },
  { id: 'f3000000-0000-4000-8000-000000000003', organization_id: ORGANIZATIONS[0], name: 'Phân khu Suối Vàng · mẫu QA', area_ha: '2.1000', latitude: '11.969400', longitude: '108.458820' },
  { id: 'f4000000-0000-4000-8000-000000000004', organization_id: ORGANIZATIONS[1], name: 'Bản Áng Mộc Châu · mẫu QA', area_ha: '4.5000', latitude: '20.828640', longitude: '104.661520' },
]

const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
export function createPreviewTransport(initialRole: RoleCode | null = null) {
  let session = PREVIEW_USERS.find((user) => user.role === initialRole) ?? null
  let farms = PREVIEW_FARMS.map((farm) => ({ ...farm }))
  let failure = false
  return {
    setFailure(value: boolean) { failure = value },
    async fetch(input: string | URL | Request, init: RequestInit = {}): Promise<Response> {
      const request = input instanceof Request ? input : null
      const url = new URL(request?.url ?? String(input), 'http://preview.invalid')
      const method = init.method ?? request?.method ?? 'GET'
      const path = url.pathname
      if (failure) return response({ detail: 'Lỗi 503 tổng hợp cho kiểm thử giao diện.' }, 503)
      const body = init.body ? JSON.parse(String(init.body)) : {}
      if (path === '/') return response({ status: 'ok', message: 'SYNTHETIC PREVIEW ONLY' })
      if (path === '/api/v1/auth/login' || path === '/api/v1/auth/demo-login') {
        if (path.endsWith('/login') && !body.password) return response({ detail: 'Preview cần một giá trị thử trong ô mật khẩu; không dùng mật khẩu thật.' }, 401)
        const next = PREVIEW_USERS.find((user) => user.email === body.email)
        if (!next) return response({ detail: 'Email không thuộc ba danh tính QA.' }, 401)
        session = { ...next }
        return response(session)
      }
      if (path === '/api/v1/auth/me') return session ? response(session) : response({ detail: 'Chưa có phiên QA.' }, 401)
      if (path === '/api/v1/auth/logout') { session = null; return new Response(null, { status: 204 }) }
      if (!path.startsWith('/api/v1/farms/')) return response({ detail: 'Endpoint không có trong transport QA.' }, 404)
      if (!session) return response({ detail: 'Phiên QA chưa xác thực.' }, 401)
      if (!hasPermission(session.role, method === 'GET' ? 'farms:read' : 'farms:write')) return response({ detail: 'Vai trò QA không có quyền farms.' }, 403)
      if (method === 'GET') return response(farms.filter((farm) => farm.organization_id === session!.organization_id))
      const payload = body as FarmPayload
      if (!payload.name?.trim() || !Number.isFinite(Number(payload.area_ha)) || Number(payload.area_ha) <= 0 || !Number.isFinite(Number(payload.latitude)) || Math.abs(Number(payload.latitude)) > 90 || !Number.isFinite(Number(payload.longitude)) || Math.abs(Number(payload.longitude)) > 180) return response({ detail: 'Payload QA không hợp lệ.' }, 422)
      const fields = { name: payload.name.trim(), area_ha: String(payload.area_ha), latitude: String(payload.latitude), longitude: String(payload.longitude) }
      if (method === 'POST') {
        const farm = { ...fields, id: crypto.randomUUID(), organization_id: session.organization_id }
        farms = [...farms, farm]
        return response(farm, 201)
      }
      if (method === 'PUT') {
        const id = path.split('/').filter(Boolean).at(-1)
        const current = farms.find((farm) => farm.id === id && farm.organization_id === session!.organization_id)
        if (!current) return response({ detail: 'Không tìm thấy bản ghi trong tenant QA.' }, 404)
        const saved = { ...current, ...fields }
        farms = farms.map((farm) => farm.id === id ? saved : farm)
        return response(saved)
      }
      return response({ detail: 'Method không được hỗ trợ.' }, 405)
    },
  }
}
