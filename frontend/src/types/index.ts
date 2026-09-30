export type RoleCode =
  | 'grower'
  | 'cooperative'
  | 'transporter'
  | 'distributor'
  | 'inspector'
  | 'organization_admin'
  | 'system_admin'

export type OrganizationType =
  | 'farm'
  | 'cooperative'
  | 'transport'
  | 'distribution'
  | 'inspection'
  | 'administration'

export interface HealthResponse {
  status: string
  message: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface SessionUser {
  id: string
  email: string
  full_name: string
  organization_id: string
  organization_name: string
  organization_type: OrganizationType
  role: RoleCode
}

export interface Farm {
  id: string
  organization_id: string
  name: string
  area_ha: string
  latitude: string
  longitude: string
}

export interface FarmPayload {
  name: string
  area_ha: number | string
  latitude: number | string
  longitude: number | string
}

export const ROLE_LABELS: Record<RoleCode, string> = {
  grower: 'Nông hộ / Trang trại',
  cooperative: 'Hợp tác xã',
  transporter: 'Đơn vị vận chuyển',
  distributor: 'Nhà phân phối',
  inspector: 'Thanh tra viên',
  organization_admin: 'Quản trị đơn vị',
  system_admin: 'Quản trị hệ thống',
}

export const ORG_TYPE_LABELS: Record<OrganizationType, string> = {
  farm: 'Nông trại sản xuất',
  cooperative: 'Hợp tác xã',
  transport: 'Vận tải chuỗi lạnh',
  distribution: 'Trung tâm phân phối',
  inspection: 'Cơ quan thanh tra',
  administration: 'Quản trị vận hành',
}

export const ROLE_PERMISSIONS: Record<RoleCode, string[]> = {
  grower: ['auth:session', 'farms:read', 'farms:write'],
  cooperative: ['auth:session'],
  transporter: ['auth:session'],
  distributor: ['auth:session'],
  inspector: ['auth:session', 'lots:read_all'],
  organization_admin: ['auth:session', 'farms:read', 'farms:write'],
  system_admin: ['auth:session'],
}

export function hasPermission(role: RoleCode, permission: string): boolean {
  const perms = ROLE_PERMISSIONS[role] ?? []
  if (perms.includes(permission)) {
    return true
  }
  return permission === 'lots:read' && perms.includes('lots:read_all')
}

export interface DemoAccount {
  shortName: string
  label: string
  organization: string
  roleText: string
  email: string
  password: string
  description: string
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    shortName: 'Cầu Đất (Grower)',
    label: 'Nông hộ Cầu Đất — Tổ chức A',
    organization: 'Nông trại Cầu Đất Đà Lạt',
    roleText: 'grower · Quyền: farms:read, farms:write',
    email: 'grower@caudat.vn',
    password: 'Password123!',
    description:
      'Quản lý danh mục thửa đất Đà Lạt. Chỉ nhìn thấy vùng trồng thuộc Tổ chức A.',
  },
  {
    shortName: 'Mộc Châu (Admin)',
    label: 'Quản trị HTX Mộc Châu — Tổ chức B',
    organization: 'Hợp tác xã Nông sản Mộc Châu',
    roleText: 'organization_admin · Cô lập dữ liệu đa tổ chức (RLS)',
    email: 'admin@mocchau.vn',
    password: 'Password123!',
    description:
      'Kiểm chứng PostgreSQL Row-Level Security: Chỉ hiển thị vùng trồng của Mộc Châu.',
  },
  {
    shortName: 'Thanh tra (Inspector)',
    label: 'Thanh tra viên — Cơ quan Kiểm định',
    organization: 'Chi cục Quản lý Chất lượng Nông lâm sản',
    roleText: 'inspector · Quyền: lots:read_all (Chặn farms:read)',
    email: 'inspector@chicuc.gov.vn',
    password: 'Password123!',
    description:
      'Kiểm chứng RBAC chặn truy cập trái phép (403 Forbidden) khi gọi API vùng trồng.',
  },
]

