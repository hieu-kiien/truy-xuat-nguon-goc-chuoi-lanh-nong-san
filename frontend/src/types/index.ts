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

export interface Lot {
  id: string
  organization_id: string
  farm_id: string | null
  name: string
  lot_code: string | null
  product_id: string | null
  harvested_on: string | null
  quantity: string | null
  remaining_quantity: string
  current_holder_organization_id: string
  current_holder_organization_name: string
  current_location_id: string | null
  current_location: DistributionLocation | null
  status: 'active' | 'pending_handover' | 'closed' | 'consumed'
  product: Product | null
}

export interface DistributionLocation {
  id: string
  organization_id: string
  name: string
  address: string
}

export function canManageDistribution(user: SessionUser): boolean {
  return user.organization_type === 'distribution' && (user.role === 'distributor' || user.role === 'organization_admin')
}

export function lotStatusLabel(status: Lot['status'] | 'transferred'): string {
  return ({active: 'Đang lưu hành', pending_handover: 'Chờ bàn giao', closed: 'Đã đóng', consumed: 'Đã tiêu thụ', transferred: 'Đã bàn giao'})[status]
}

export interface LotPage {
  items: Lot[]
  next_cursor: string | null
}

export interface LotRelation {
  id: string
  parent_lot_id: string
  child_lot_id: string
  quantity: string
  operation: 'split' | 'merge'
}

export interface Lineage {
  selected_lot_id: string
  direction: 'ancestors' | 'descendants'
  nodes: GraphLot[]
  edges: LotRelation[]
  roots: string[]
  root_farms: Farm[]
}

export interface RecallLotItem {
  id: string
  lot_code: string | null
  name: string
  tier: number
  status: 'active' | 'pending_handover' | 'closed' | 'consumed' | 'transferred'
  is_multi_source_merge: boolean
  organization_id: string | null
  current_holder_organization_id: string | null
  current_holder_organization_name: string | null
  holder_org_type: OrganizationType | null
  current_location_id: string | null
  current_location: DistributionLocation | null
  quantity: string | null
  remaining_quantity: string
  consumed_quantity: string
  recoverable_quantity: string
  unit: string | null
  harvested_on: string | null
  historical_only: boolean
  parent_lot_ids: string[]
}

export interface RecallSummary {
  root_lot_id: string
  root_lot_code: string | null
  root_lot_name: string
  initial_quantity: string | null
  unit: string | null
  total_affected_lots: number
  total_descendants_count: number
  total_recoverable_kg: string
  total_consumed_kg: string
  involved_organizations_count: number
  involved_organizations: string[]
  has_multi_source_merge: boolean
  has_consumed_lot: boolean
}

export interface RecallReport {
  root_lot: RecallLotItem
  summary: RecallSummary
  descendants: RecallLotItem[]
  affected_lots: RecallLotItem[]
}

export interface RecallOrganizationProgress {
  organization_id: string
  organization_name: string
  organization_type: OrganizationType | string | null
  status: 'confirmed' | 'pending'
  confirmed_at: string | null
  confirmed_by_user_id: string | null
  confirmed_by_user_name: string | null
  note: string | null
  affected_lot_ids: string[]
  affected_lot_codes: string[]
  recoverable_quantity: string
}

export interface RecallConfirmationRecord {
  id: string
  recall_order_id: string
  organization_id: string
  organization_name: string | null
  confirmed_by_user_id: string
  confirmed_by_user_name: string | null
  note: string
  confirmed_at: string
}

export interface RecallOrder {
  id: string
  recall_code: string
  root_lot_id: string
  opened_by_user_id: string
  opened_by_organization_id: string
  reason: string
  status: 'open' | 'completed'
  created_at: string
  completed_at: string | null
  root_lot: RecallLotItem | null
  summary: RecallSummary | null
  descendants: RecallLotItem[]
  affected_lots: RecallLotItem[]
  total_organizations_count: number
  confirmed_organizations_count: number
  progress_text: string
  pending_organizations: string[]
  confirmed_organizations: string[]
  organizations_progress: RecallOrganizationProgress[]
  confirmations: RecallConfirmationRecord[]
}

export interface RecallNotification {
  recall_id: string
  recall_code: string
  root_lot_id: string
  root_lot_code: string | null
  root_lot_name: string
  reason: string
  status: 'open' | 'completed'
  created_at: string
  organization_id: string
  organization_name: string
  handling_status: 'confirmed' | 'pending'
  confirmed_at: string | null
  note: string | null
  total_organizations_count: number
  confirmed_organizations_count: number
  progress_text: string
  affected_lots: RecallLotItem[]
}

export interface LotDetail extends Lot {
  parents: GraphLot[]
  children: GraphLot[]
  direct_farms: Farm[]
  root_farms: Farm[]
  event_count: number
}

export interface GraphLot extends Omit<Lot, 'remaining_quantity' | 'current_holder_organization_id' | 'current_holder_organization_name' | 'status'> {
  remaining_quantity: string | null
  current_holder_organization_id: string | null
  current_holder_organization_name: string | null
  status: Lot['status'] | 'transferred'
  historical_only: boolean
}

export type ProductUnit = 'kg' | 'tấn' | 'thùng'

export interface Product {
  id: string
  name: string
  unit: ProductUnit
  description: string | null
  price: number
  quantity: number | null
}

export interface ProductPayload {
  name: string
  unit: ProductUnit
  description?: string | null
  price?: number
  quantity?: number
}

export interface OrganizationOption {
  id: string
  name: string
}

export interface Handover {
  id: string
  lot_id: string
  lot_code: string | null
  lot_name: string
  from_organization_id: string
  from_organization_name: string
  to_organization_id: string
  to_organization_name: string
  status: 'pending' | 'accepted' | 'rejected'
  note: string | null
  rejection_reason: string | null
  created_at: string
  overdue_at: string | null
  has_cold_chain_violation?: boolean
}

export interface ColdChainViolation {
  id?: string
  shipment_id?: string
  violation_type: 'high_temp' | 'low_temp' | string
  started_at: string
  ended_at?: string | null
  duration_minutes?: number | null
  peak_temperature_celsius: number
  is_settled?: boolean
}


export interface HandoverPayload {
  lot_id: string
  to_organization_id: string
  note?: string
}

export interface LotPayload {
  farm_id: string
  product_id: string
  harvested_on: string
  quantity: string
}

export interface LotListParams {
  q?: string
  product_id?: string
  cursor?: string
  page_size?: number
}

export interface LotEvent {
  id: string
  organization_id: string
  lot_id: string
  sequence_number: number
  event_type: string
  recorded_at: string
  payload: Record<string, unknown>
  payload_redacted?: boolean
  prev_hash: string
  event_hash: string
  organization_name: string
}

export interface IntegrityIssue {
  sequence_number: number
  kind: string
}

export interface IntegrityReport {
  valid: boolean
  checked_events: number
  first_invalid_sequence: number | null
  issues: IntegrityIssue[]
}

export interface IntegrityCheckRecord extends IntegrityReport {
  id: string
  lot_id: string
  checked_at: string
}

export interface EventHistory {
  events: LotEvent[]
  integrity: IntegrityReport
  next_cursor?: number | null
  total?: number
}

export interface CreateEventRequest {
  lot_id: string
  event_type: string
  payload?: Record<string, unknown>
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
  grower: [
    'organizations:read',

    'auth:session',
    'processing_steps:read',
    'input_lots:create',
    'input_lots:read',
    'notifications:read',
    'farms:read',
    'farms:write',
    'products:read',
    'lots:read',
    'lots:create',
    'events:read',
    'events:create',
    'handovers:create',
    'handovers:resolve',
    'recalls:read',
    'recalls:confirm',
  ],
  cooperative: [
    'organizations:read',

    'lots:transform',
    'auth:session',
    'processing_steps:read',
    'processing_steps:create',
    'input_lots:create',
    'input_lots:read',
    'notifications:read',
    'products:read',
    'lots:read',
    'events:read',
    'events:create',
    'handovers:create',
    'handovers:resolve',
    'recalls:read',
    'recalls:confirm',
    'shipments:create',
    'shipments:read',
    'shipments:complete',
    'telemetry:ingest',
    'telemetry:read',
  ],
  transporter: [
    'organizations:read',

    'auth:session',
    'processing_steps:read',
    'notifications:read',
    'products:read',
    'lots:read',
    'events:read',
    'events:create',
    'handovers:create',
    'handovers:resolve',
    'recalls:read',
    'recalls:confirm',
    'shipments:create',
    'shipments:read',
    'shipments:complete',
    'telemetry:ingest',
    'telemetry:read',
  ],
  distributor: [
    'organizations:read',

    'locations:manage',
    'lots:consume',
    'lots:transform',
    'auth:session',
    'processing_steps:read',
    'processing_steps:create',
    'notifications:read',
    'products:read',
    'lots:read',
    'events:read',
    'events:create',
    'handovers:create',
    'handovers:resolve',
    'recalls:read',
    'recalls:confirm',
    'shipments:create',
    'shipments:read',
    'shipments:complete',
    'telemetry:ingest',
    'telemetry:read',
  ],
  inspector: [
    'organizations:read',

    'auth:session',
    'processing_steps:read',
    'input_lots:read',
    'notifications:read',
    'products:read',
    'lots:read_all',
    'events:read_all',
    'events:verify',
    'recalls:open',
    'recalls:manage',
    'recalls:read',
    'recalls:read_all',
    'shipments:read',
    'shipments:read_all',
    'telemetry:read',
    'telemetry:read_all',
  ],
  organization_admin: [
    'organizations:manage',
    'organizations:read',

    'locations:manage',
    'lots:consume',
    'lots:transform',
    'auth:session',
    'processing_steps:read',
    'processing_steps:create',
    'input_lots:create',
    'input_lots:read',
    'notifications:read',
    'farms:read',
    'farms:write',
    'products:read',
    'lots:read',
    'lots:create',
    'events:read',
    'events:create',
    'handovers:create',
    'handovers:resolve',
    'recalls:open',
    'recalls:manage',
    'recalls:read',
    'recalls:confirm',
    'shipments:create',
    'shipments:read',
    'shipments:complete',
    'telemetry:ingest',
    'telemetry:read',
  ],
  system_admin: [
    'organizations:manage',
    'organizations:read',

    'auth:session',
    'processing_steps:read',
    'processing_steps:create',
    'processing_steps:manage',
    'input_lots:read',
    'notifications:read',
    'farms:read',
    'farms:write',
    'farms:read_all',
    'lots:read',
    'lots:read_all',
    'events:read',
    'events:read_all',
    'events:verify',
    'products:read',
    'products:write',
    'products:read_all',
    'security:read',
    'recalls:open',
    'recalls:manage',
    'recalls:read',
    'recalls:read_all',
    'recalls:confirm',
    'shipments:create',
    'shipments:read',
    'shipments:complete',
    'shipments:read_all',
    'telemetry:ingest',
    'telemetry:read',
    'telemetry:read_all',
  ],
}

export function hasPermission(role: RoleCode, permission: string): boolean {
  const perms = ROLE_PERMISSIONS[role] ?? []
  if (perms.includes(permission)) {
    return true
  }
  if (permission === 'farms:read' && perms.includes('farms:read_all')) {
    return true
  }
  if (permission === 'lots:read' && perms.includes('lots:read_all')) {
    return true
  }
  if (permission === 'events:read' && perms.includes('events:read_all')) {
    return true
  }
  if (permission === 'products:read' && perms.includes('products:read_all')) {
    return true
  }
  if (permission === 'recalls:read' && perms.includes('recalls:read_all')) {
    return true
  }
  if (permission === 'shipments:read' && perms.includes('shipments:read_all')) {
    return true
  }
  if (permission === 'telemetry:read' && perms.includes('telemetry:read_all')) {
    return true
  }
  return false
}

export interface PublicTrace {
  processing_summary?: string | null
  lot_code: string | null
  product_name: string | null
  product_unit: string | null
  harvested_on: string | null
  farm_name: string | null
  origin_organization_type: string | null
  status: string | null
  recall_active: boolean
  cold_chain_violation: boolean
}

export interface PublicTraceWarning {
  code: 'recall' | 'cold_chain'
  level: 'danger' | 'note'
  message: string
}

export interface PublicTraceResponse {
  trace: PublicTrace
  warnings: PublicTraceWarning[]
}

export interface RoutePoint {
  order: number
  name: string
  kind: 'origin' | 'stop'
  latitude: number
  longitude: number
}

export interface PublicRoute {
  points: RoutePoint[]
  precision_note: string
}

export interface ProcessingStep {
  id: string
  code: string
  name: string
  parameter_schema: Record<string, { type?: string; label?: string }>
}

export interface ProcessingStepRecord {
  id: string
  lot_id: string
  processing_step_id: string
  processing_step_code: string
  processing_step_name: string
  parameters: Record<string, unknown>
  occurred_at: string
  organization_id: string
  created_at: string
}

export interface CarrierViolationStats {
  carrier_organization_id: string
  carrier_organization_name: string
  carrier_organization_type: string
  shipment_count: number
  shipment_with_violation_count: number
  violation_count: number
  high_temp_violation_count: number
  low_temp_violation_count: number
  total_violation_minutes: number
  violation_shipment_rate: number
}

export interface ColdChainViolationStats {
  period_start: string | null
  period_end: string
  carriers: CarrierViolationStats[]
  total_shipment_count: number
  total_shipment_with_violation_count: number
  total_violation_count: number
  total_violation_minutes: number
  violation_shipment_rate: number
}

export interface IntegrityAlert {
  id: string
  lot_id: string
  lot_code: string | null
  organization_id: string
  detected_at: string
  first_invalid_sequence: number | null
  issue_count: number
  checked_events: number
}

export interface IntegrityScanSummary {
  generated_at: string
  last_checked_at: string | null
  checked_lot_count: number
  broken_lot_count: number
  broken_lots: IntegrityAlert[]
  recent_alerts: IntegrityAlert[]
}

export interface NotificationItem {
  id: string
  kind: 'handover_pending' | 'recall_affected' | 'cold_chain_violation'
  title: string
  body: string
  link_path: string
  lot_id: string | null
  lot_code: string | null
  created_at: string
  read_at: string | null
}

export interface NotificationList {
  items: NotificationItem[]
  unread_count: number
  generated_at: string
}

export interface LotInputLot {
  id: string
  lot_id: string
  product_id: string
  product_name: string
  quantity: string
  used_on: string
  organization_id: string
  created_at: string
}

export interface LotInputLotPayload {
  product_id: string
  quantity: string
  used_on: string
}

export interface Shipment {
  id: string
  shipment_code: string
  organization_id: string
  created_by_user_id: string
  container_code: string
  status: string
  notes: string | null
  created_at: string
  completed_at: string | null
  lot_count: number
}

export interface ShipmentTemperatureReading {
  id: string
  shipment_id: string
  container_code: string
  temperature_celsius: string
  recorded_at: string
  ingested_at: string
}

export interface ShipmentHourlyAggregate {
  id: string
  shipment_id: string
  container_code: string
  bucket_start: string
  reading_count: number
  min_temperature_celsius: string | null
  max_temperature_celsius: string | null
  avg_temperature_celsius: string | null
  is_gap: boolean
}

export interface OrganizationProfile {
  id: string
  name: string
  organization_type: string
  contact_email: string | null
}

export interface OrganizationInvitation {
  id: string
  organization_id: string
  organization_name: string
  email: string
  role_code: string
  status: string
  created_at: string
  expires_at: string
  accepted_at: string | null
  revoked_at: string | null
}

export interface OrganizationMember {
  id: string
  email: string
  full_name: string
  role_code: string
  is_active: boolean
  locked_until: string | null
}

export interface OrganizationInvitationCreated extends OrganizationInvitation {
  /** The single-use link, handed over only when the invitation is made. */
  invitation_url: string
}

export interface ShipmentColdChainLimits {
  shipment_id: string
  shipment_code: string
  min_temp_celsius: string
  max_temp_celsius: string
  delay_minutes: number
  from_snapshot: boolean
  config_resolved_at: string | null
  sources: ProductColdChainLimitSource[]
}

export interface ProductColdChainLimitSource {
  product_id: string | null
  product_name: string | null
  configured: boolean
  min_temp_celsius: string
  max_temp_celsius: string
  delay_minutes: number
}

export interface ProductColdChainConfig {
  id: string
  product_id: string
  product_name: string
  min_temp_celsius: string
  max_temp_celsius: string
  delay_minutes: number
  updated_by_user_id: string | null
  created_at: string
  updated_at: string
}

export interface ShipmentViolation {
  id: string | null
  shipment_id: string | null
  violation_type: string
  started_at: string
  ended_at: string
  duration_minutes: number
  peak_temperature_celsius: number
  is_settled: boolean
}

export interface TelemetryIngestResult {
  container_code: string
  shipment_id: string
  shipment_code: string
  ingested_count: number
  duplicate_count: number
  total_readings: number
  violations_detected: number
  violations: ShipmentViolation[]
  applied_limits: AppliedColdChainLimits
}

export interface AppliedColdChainLimits {
  min_temp_celsius: string
  max_temp_celsius: string
  delay_minutes: number
  from_snapshot: boolean
}
