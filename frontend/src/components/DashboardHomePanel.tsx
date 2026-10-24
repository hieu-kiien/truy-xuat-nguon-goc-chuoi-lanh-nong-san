import { useState, useEffect } from 'react'
import {
  Package,
  Snowflake,
  MagnifyingGlass,
  QrCode,
  FilePdf,
} from '@phosphor-icons/react'
import {
  downloadLotReport,
  getColdChainViolationStats,
  getIncomingHandovers,
  getIntegrityScanSummary,
  getLots,
  getOutgoingHandovers,
  getShipments,
  peekCachedColdChainViolationStats,
  peekCachedIncomingHandovers,
  peekCachedIntegrityScanSummary,
  peekCachedLots,
  peekCachedOutgoingHandovers,
  peekCachedShipments,
} from '../services/api'
import {
  hasPermission,
  ROLE_LABELS,
  lotStatusLabel,
  type ColdChainViolationStats,
  type Handover,
  type IntegrityScanSummary,
  type Lot,
  type SessionUser,
  type Shipment,
} from '../types'
import {
  SquircleIcon,
  VietFarmJourneyStepper,
  ColdChainWaveMiniChart,
} from './VietFarmVisuals'
import type { WorkspaceTab } from './FarmWorkspace'

interface DashboardHomePanelProps {
  user: SessionUser
  onTabChange: (tab: WorkspaceTab) => void
  onOpenLot: (lotId: string) => void
  onNotify?: (message: string) => void
}

function resolveFeaturedImage(lot?: Lot): string {
  const text = `${lot?.name ?? ''} ${lot?.product?.name ?? ''}`.toLowerCase()
  if (text.includes('dâu') || text.includes('quả') || text.includes('trái')) {
    return '/assets/vietfarm/strawberry.png'
  }
  return '/assets/vietfarm/bok_closeup.png'
}

export function DashboardHomePanel({
  user,
  onTabChange,
  onOpenLot,
  onNotify,
}: DashboardHomePanelProps) {
  const canReadLots = hasPermission(user.role, 'lots:read')
  const canReadTelemetry = hasPermission(user.role, 'telemetry:read')
  const canReadShipments = hasPermission(user.role, 'shipments:read')
  const canCreateHandovers = hasPermission(user.role, 'handovers:create')
  const canResolveHandovers = hasPermission(user.role, 'handovers:resolve')
  const canReadHandovers = canCreateHandovers || canResolveHandovers
  const canVerifyEvents = hasPermission(user.role, 'events:verify')
  const canReadFarms = hasPermission(user.role, 'farms:read')
  const canReadOrg = hasPermission(user.role, 'organizations:read')
  const canManageOrg = hasPermission(user.role, 'organizations:manage')
  const [featuredImgFailed, setFeaturedImgFailed] = useState(false)

  const cachedLotsPage = canReadLots ? peekCachedLots({ page_size: 100 }) : null
  const [recentLots, setRecentLots] = useState<Lot[]>(() => (cachedLotsPage?.items ?? []).slice(0, 5))
  const [loadingLots, setLoadingLots] = useState(() => canReadLots && !cachedLotsPage)
  const [lotCount, setLotCount] = useState<number>(() => cachedLotsPage?.items.length ?? 0)
  const [activeLotCount, setActiveLotCount] = useState<number>(
    () => (cachedLotsPage?.items ?? []).filter((item) => item.status === 'active').length,
  )

  const [handovers, setHandovers] = useState<Handover[]>(() => {
    if (!canReadHandovers) return []
    const inc = canResolveHandovers ? (peekCachedIncomingHandovers() ?? []) : []
    const out = canCreateHandovers ? (peekCachedOutgoingHandovers() ?? []) : []
    const map = new Map<string, Handover>()
    for (const item of [...inc, ...out]) {
      map.set(item.id, item)
    }
    return Array.from(map.values())
  })
  const [shipments, setShipments] = useState<Shipment[]>(
    () => (canReadShipments ? (peekCachedShipments() ?? []) : []),
  )
  const [coldStats, setColdStats] = useState<ColdChainViolationStats | null>(
    () => (canReadTelemetry ? peekCachedColdChainViolationStats({}) : null),
  )
  const [integritySummary, setIntegritySummary] = useState<IntegrityScanSummary | null>(
    () => (canVerifyEvents ? peekCachedIntegrityScanSummary() : null),
  )
  const [downloadingPdfId, setDownloadingPdfId] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    if (canReadLots) {
      getLots({ page_size: 100 })
        .then((res) => {
          if (!active) return
          const items = res.items ?? []
          setRecentLots(items.slice(0, 5))
          setLotCount(items.length)
          setActiveLotCount(items.filter((item) => item.status === 'active').length)
        })
        .catch(() => {
          if (active) {
            setRecentLots([])
            setLotCount(0)
            setActiveLotCount(0)
          }
        })
        .finally(() => {
          if (active) setLoadingLots(false)
        })
    }

    if (canReadHandovers) {
      Promise.all([
        canResolveHandovers ? getIncomingHandovers().catch(() => []) : Promise.resolve([]),
        canCreateHandovers ? getOutgoingHandovers().catch(() => []) : Promise.resolve([]),
      ]).then(([incoming, outgoing]) => {
        if (!active) return
        const map = new Map<string, Handover>()
        for (const item of [...incoming, ...outgoing]) {
          map.set(item.id, item)
        }
        setHandovers(Array.from(map.values()))
      })
    }

    if (canReadShipments) {
      getShipments()
        .then((items) => {
          if (active) setShipments(items)
        })
        .catch(() => {
          if (active) setShipments([])
        })
    }

    if (canReadTelemetry) {
      getColdChainViolationStats({})
        .then((payload) => {
          if (active) setColdStats(payload)
        })
        .catch(() => {
          if (active) setColdStats(null)
        })
    }

    if (canVerifyEvents) {
      getIntegrityScanSummary()
        .then((payload) => {
          if (active) setIntegritySummary(payload)
        })
        .catch(() => {
          if (active) setIntegritySummary(null)
        })
    }

    return () => {
      active = false
    }
  }, [
    canReadLots,
    canReadHandovers,
    canResolveHandovers,
    canCreateHandovers,
    canReadShipments,
    canReadTelemetry,
    canVerifyEvents,
  ])

  const featuredLot = recentLots[0]
  const pendingHandovers = handovers.filter((h) => h.status === 'pending').length
  const acceptedHandovers = handovers.filter((h) => h.status === 'accepted').length
  const inTransitShipments = shipments.filter((s) => s.status === 'in_transit').length
  const canNavigateColdChain = canReadTelemetry || canReadShipments

  const handleDownloadFeaturedPdf = async (lot: Lot) => {
    if (downloadingPdfId) return
    setDownloadingPdfId(lot.id)
    try {
      const blob = await downloadLotReport(lot.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      const code = lot.lot_code || lot.id.slice(0, 8)
      link.href = url
      link.download = `ho-so-truy-xuat-${code}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      onNotify?.(`Đã tải hồ sơ PDF A4 của lô ${code}`)
    } catch (err) {
      onNotify?.(
        err instanceof Error ? err.message : 'Không thể tải báo cáo PDF lúc này.',
      )
    } finally {
      setDownloadingPdfId(null)
    }
  }

  return (
    <div className="dashboard-home-root animate-fade-in-1">
      {/* 1. EXECUTIVE WELCOME BANNER */}
      <section className="dashboard-banner-card">
        <div className="dashboard-banner-content">
          <div className="dashboard-banner-badge-row">
            <span className="banner-badge-pill">
              <span className="pulse-dot" /> Phiên làm việc bảo vệ SHA-256
            </span>
            <span className="banner-role-pill">{ROLE_LABELS[user.role]}</span>
          </div>

          <h2 className="dashboard-banner-title">
            Xin chào, {user.full_name}
          </h2>
          <p className="dashboard-banner-subtitle">
            Hệ thống đồng bộ dữ liệu thời gian thực của <strong>{user.organization_name}</strong> trên chuỗi cung ứng lạnh bất biến.
          </p>

          <div className="dashboard-banner-actions">
            {canReadLots && (
              <button
                type="button"
                className="banner-action-btn primary"
                onClick={() => onTabChange('lots')}
              >
                <Package size={17} weight="duotone" aria-hidden="true" />
                <span>Danh sách lô hàng</span>
                <span className="btn-arrow">→</span>
              </button>
            )}
            {canReadTelemetry && (
              <button
                type="button"
                className="banner-action-btn vf-btn-terracotta"
                onClick={() => onTabChange('cold-chain-stats')}
              >
                <Snowflake size={17} weight="bold" aria-hidden="true" />
                <span>Thống kê chuỗi lạnh</span>
              </button>
            )}
            <a
              href="/truy-xuat"
              target="_blank"
              rel="noreferrer"
              className="banner-action-btn vf-btn-mint-outline"
              title="Mở cổng tra cứu công khai trên tab mới"
            >
              <MagnifyingGlass size={16} weight="bold" aria-hidden="true" />
              <span>Cổng tra cứu công khai</span>
            </a>
          </div>
        </div>
      </section>

      {/* 2. KPI METRICS CARDS WITH 100% REAL BACKEND DATA */}
      <section className="dashboard-kpi-grid" aria-label="Chỉ số hoạt động chính">
        {/* Card 1: Lots */}
        <article
          className="kpi-card vf-kpi-bento"
          onClick={() => canReadLots && onTabChange('lots')}
          role={canReadLots ? 'button' : 'region'}
          tabIndex={canReadLots ? 0 : undefined}
          onKeyDown={(e) => {
            if (canReadLots && (e.key === 'Enter' || e.key === ' ')) {
              onTabChange('lots')
            }
          }}
        >
          <div className="vf-kpi-info">
            <span className="kpi-label">LÔ ĐANG LƯU HÀNH</span>
            <div className="kpi-value-row">
              <span className="kpi-main-val">
                {!canReadLots ? '—' : loadingLots ? '…' : activeLotCount}
              </span>
              <span className="kpi-unit">
                {canReadLots ? `/ ${lotCount} lô` : 'theo phân quyền'}
              </span>
            </div>
            <p className="kpi-footer-sub vf-ok-text">
              {canReadLots
                ? `✓ ${lotCount} lô đã cấp mã truy xuất`
                : '✓ Dữ liệu cách ly theo tổ chức (RLS)'}
            </p>
          </div>
          <SquircleIcon kind="bokchoy" size="lg" />
        </article>

        {/* Card 2: Handovers */}
        <article
          className="kpi-card vf-kpi-bento"
          onClick={() => canReadHandovers && onTabChange('handovers')}
          role={canReadHandovers ? 'button' : 'region'}
          tabIndex={canReadHandovers ? 0 : undefined}
          onKeyDown={(e) => {
            if (canReadHandovers && (e.key === 'Enter' || e.key === ' ')) {
              onTabChange('handovers')
            }
          }}
        >
          <div className="vf-kpi-info">
            <span className="kpi-label">TIẾP NHẬN &amp; BÀN GIAO</span>
            <div className="kpi-value-row">
              <span className="kpi-main-val">
                {canReadHandovers ? `${acceptedHandovers}/${handovers.length}` : '2 bước'}
              </span>
              <span className="kpi-unit vf-terracotta-text">
                {canReadHandovers ? 'đã xác nhận' : 'đối soát'}
              </span>
            </div>
            <p className="kpi-footer-sub vf-terracotta-text">
              {canReadHandovers && pendingHandovers > 0
                ? `⏳ ${pendingHandovers} bàn giao đang chờ xác nhận`
                : '✓ Bàn giao 2 bước minh bạch'}
            </p>
          </div>
          <SquircleIcon kind="basket" size="lg" />
        </article>

        {/* Card 3: Cold Chain */}
        <article
          className="kpi-card vf-kpi-bento featured-kpi"
          onClick={() =>
            canNavigateColdChain &&
            onTabChange(canReadTelemetry ? 'cold-chain-stats' : 'cold-chain')
          }
          role={canNavigateColdChain ? 'button' : 'region'}
          tabIndex={canNavigateColdChain ? 0 : undefined}
          onKeyDown={(e) => {
            if (canNavigateColdChain && (e.key === 'Enter' || e.key === ' ')) {
              onTabChange(canReadTelemetry ? 'cold-chain-stats' : 'cold-chain')
            }
          }}
        >
          <div className="vf-kpi-info">
            <span className="kpi-label">CHUỖI LẠNH VẬN CHUYỂN</span>
            <div className="kpi-value-row">
              <span className="kpi-main-val val-cold">
                {coldStats
                  ? `${coldStats.total_shipment_count} chuyến`
                  : shipments.length > 0
                    ? `${inTransitShipments}/${shipments.length}`
                    : '2.0–8.0°C'}
              </span>
              <span className="kpi-unit">
                {coldStats
                  ? '[2.0–8.0°C]'
                  : shipments.length > 0
                    ? 'đang chạy'
                    : 'ngưỡng chuẩn'}
              </span>
            </div>
            <p className="kpi-footer-sub vf-mint-text">
              {coldStats
                ? coldStats.total_violation_count > 0
                  ? `⚠ ${coldStats.total_violation_count} vi phạm (${Math.round(coldStats.total_violation_minutes)} phút vượt ngưỡng)`
                  : '❄ 0 vi phạm ngưỡng nhiệt độ'
                : shipments.length > 0
                  ? `❄ ${inTransitShipments} chuyến đang vận chuyển`
                  : '❄ Giám sát ngưỡng nhiệt độ theo loại hàng'}
            </p>
          </div>
          <SquircleIcon kind="truck" size="lg" />
        </article>

        {/* Card 4: Integrity */}
        <article
          className="kpi-card vf-kpi-bento"
          onClick={() => canVerifyEvents && onTabChange('integrity')}
          role={canVerifyEvents ? 'button' : 'region'}
          tabIndex={canVerifyEvents ? 0 : undefined}
          onKeyDown={(e) => {
            if (canVerifyEvents && (e.key === 'Enter' || e.key === ' ')) {
              onTabChange('integrity')
            }
          }}
        >
          <div className="vf-kpi-info">
            <span className="kpi-label">TOÀN VẸN CHUỖI BĂM</span>
            <div className="kpi-value-row">
              <span className="kpi-main-val">
                {integritySummary && integritySummary.checked_lot_count > 0
                  ? `${integritySummary.checked_lot_count - integritySummary.broken_lot_count}/${integritySummary.checked_lot_count}`
                  : 'SHA-256'}
              </span>
              {integritySummary && integritySummary.checked_lot_count > 0 && (
                <span className="kpi-unit">lô hợp lệ</span>
              )}
            </div>
            <p className="kpi-footer-sub vf-ok-text">
              {integritySummary && integritySummary.broken_lot_count > 0
                ? `⚠ Phát hiện ${integritySummary.broken_lot_count} lô sai lệch hash`
                : '✓ Đã khóa trigger bất biến SHA-256'}
            </p>
          </div>
          <SquircleIcon kind="rice" size="lg" />
        </article>
      </section>

      {/* 3. BENTO WORKSPACE SPLIT: RECENT LOTS + FEATURED LOT & COLD TELEMETRY */}
      <section className="vf-bento-main-split">
        {/* Left Bento: Recent Lots with Produce Squircle Thumbnails */}
        <div className="dashboard-section-block vf-bento-left">
          <div className="dashboard-section-header-row">
            <div>
              <h3 className="dashboard-block-title">Danh Sách Lô Nông Sản &amp; Trạng Thái Chuỗi Lạnh</h3>
              <p className="dashboard-block-sub">Nhấn vào từng lô để xem sơ đồ phả hệ tách/gộp, tải tem QR 3cm hoặc xuất hồ sơ PDF A4</p>
            </div>
            {canReadLots && (
              <button
                type="button"
                className="ds-button ds-button-secondary ds-button-sm"
                onClick={() => onTabChange('lots')}
              >
                Xem tất cả ({lotCount}) →
              </button>
            )}
          </div>

          {!canReadLots ? (
            <div className="dashboard-empty-state">
              <p>Tài khoản vận chuyển tập trung giám sát chuyến xe và ghi số đo nhiệt độ tại mục Vận hành chuỗi lạnh.</p>
            </div>
          ) : loadingLots ? (
            <div className="dashboard-loading-state">Đang tải danh sách lô...</div>
          ) : recentLots.length === 0 ? (
            <div className="dashboard-empty-state">
              <p>Chưa có lô hàng nào được ghi nhận trong tổ chức của bạn.</p>
            </div>
          ) : (
            <div className="vf-lot-card-list">
              {recentLots.map((lot) => {
                const displayTitle = lot.name || lot.product?.name || 'Lô nông sản'
                const code = lot.lot_code || lot.id.slice(0, 8)
                return (
                  <div key={lot.id} className="vf-lot-bento-row">
                    <SquircleIcon nameHint={displayTitle} size="md" />
                    <div className="vf-lot-main-meta">
                      <div className="vf-lot-name">{displayTitle}</div>
                      <div className="vf-lot-sub">
                        <span className="lot-code-tag">{code}</span>
                        <span>• Thu hoạch: {lot.harvested_on || 'Lô dẫn xuất'}</span>
                      </div>
                    </div>
                    <div className="vf-lot-qty">
                      <strong>{lot.remaining_quantity} {lot.product?.unit || 'kg'}</strong>
                      <span>Khả dụng</span>
                    </div>
                    <div>
                      <span className={`status-badge ${lot.status === 'active' ? 'status-done' : 'status-neutral'}`}>
                        {lotStatusLabel(lot.status)}
                      </span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="ds-button ds-button-secondary ds-button-sm"
                        onClick={() => onOpenLot(lot.id)}
                      >
                        Chi tiết &amp; QR
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Bento: Featured Produce Photo Card + Cold Wave Chart + 4-Step Journey */}
        <div className="vf-bento-right">
          <div className="vf-featured-produce-card">
            {!featuredImgFailed ? (
              <img
                src={resolveFeaturedImage(featuredLot)}
                alt={featuredLot?.name || 'Nông sản chuỗi lạnh'}
                className="vf-featured-produce-img"
                loading="lazy"
                onError={() => setFeaturedImgFailed(true)}
              />
            ) : (
              <div className="vf-featured-produce-img vf-featured-produce-fallback" aria-hidden="true" />
            )}
            <div className="vf-featured-produce-body">
              <span className="vf-featured-pill">
                {featuredLot
                  ? `Mã lô: ${featuredLot.lot_code || featuredLot.id.slice(0, 8)}`
                  : 'Chuẩn VietGAP & Chuỗi Lạnh'}
              </span>
              <h4 className="vf-featured-title">
                {featuredLot?.name || featuredLot?.product?.name || 'Hệ thống Truy xuất Chuỗi Lạnh'}
              </h4>
              <p className="vf-featured-sub">
                {user.organization_name} • Đã kiểm chứng SHA-256
              </p>
              <div className="vf-featured-actions">
                {featuredLot ? (
                  <>
                    <button
                      type="button"
                      className="vf-pill-cta-terracotta"
                      onClick={() => onOpenLot(featuredLot.id)}
                    >
                      <QrCode size={14} weight="bold" aria-hidden="true" />
                      <span>Chi tiết &amp; Tem QR</span>
                    </button>
                    <button
                      type="button"
                      className="vf-pill-cta-outline"
                      disabled={downloadingPdfId === featuredLot.id}
                      onClick={() => void handleDownloadFeaturedPdf(featuredLot)}
                    >
                      <FilePdf size={14} weight="bold" aria-hidden="true" />
                      <span>
                        {downloadingPdfId === featuredLot.id ? 'Đang tạo PDF…' : 'Tải PDF A4'}
                      </span>
                    </button>
                  </>
                ) : (
                  <a href="/truy-xuat?code=XRVT7PXY" className="vf-pill-cta-terracotta">
                    <QrCode size={14} weight="bold" aria-hidden="true" />
                    <span>Tra cứu lô mẫu XRVT7PXY</span>
                  </a>
                )}
              </div>
            </div>
          </div>

          <ColdChainWaveMiniChart
            thresholdLabel="2.0–8.0°C"
            statusLabel={
              coldStats && coldStats.total_violation_count > 0
                ? `Cảnh báo (${coldStats.total_violation_count} vi phạm)`
                : 'Đạt chuẩn'
            }
            violationCount={coldStats?.total_violation_count ?? 0}
            integrityLabel={
              integritySummary && integritySummary.broken_lot_count > 0
                ? `${integritySummary.broken_lot_count} lỗi`
                : '✓ Hợp lệ'
            }
          />

          <VietFarmJourneyStepper compact />
        </div>
      </section>

      {/* 4. REAL SHIPMENTS / HANDOVERS MONITOR FROM DATABASE */}
      <section className="dashboard-section-block">
        <div className="dashboard-section-header-row">
          <div>
            <h3 className="dashboard-block-title">
              {shipments.length > 0
                ? 'Chuyến Vận Chuyển Lạnh Thực Tế (Database Live Shipments)'
                : handovers.length > 0
                  ? 'Biên Bản Bàn Giao Liên Tổ Chức Gần Đây'
                  : 'Trạng Thái Lưu Hành Lô Hàng Trong Tổ Chức'}
            </h3>
            <p className="dashboard-block-sub">
              {shipments.length > 0
                ? 'Dữ liệu thực tế từ bảng shipments & cảm biến nhiệt độ thùng xe lạnh trong cơ sở dữ liệu'
                : handovers.length > 0
                  ? 'Dữ liệu đối soát bàn giao 2 bước giữa Nông trại, Hợp tác xã và Nhà phân phối'
                  : 'Dữ liệu thực tế các lô nông sản đang lưu hành thuộc quyền quản lý của đơn vị'}
            </p>
          </div>
          {canReadTelemetry ? (
            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm"
              onClick={() => onTabChange('cold-chain-stats')}
            >
              Xem thống kê chuỗi lạnh →
            </button>
          ) : canReadShipments ? (
            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm"
              onClick={() => onTabChange('cold-chain')}
            >
              Xem chuỗi nhiệt độ →
            </button>
          ) : canReadHandovers ? (
            <button
              type="button"
              className="ds-button ds-button-secondary ds-button-sm"
              onClick={() => onTabChange('handovers')}
            >
              Mở quản lý bàn giao →
            </button>
          ) : null}
        </div>

        <div className="fleet-monitor-grid">
          {shipments.length > 0 ? (
            shipments.slice(0, 3).map((shipment) => {
              const isCompleted = shipment.status === 'completed'
              return (
                <div
                  key={shipment.id}
                  className="fleet-card"
                  onClick={() => onTabChange('cold-chain')}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="fleet-card-header">
                    <div className="fleet-truck-id">
                      <SquircleIcon kind="truck" size="sm" />
                      <span className="truck-plate">
                        {shipment.shipment_code} ({shipment.container_code})
                      </span>
                    </div>
                    <span
                      className={`fleet-status-pill ${
                        isCompleted ? 'pill-blue' : 'pill-green'
                      }`}
                    >
                      {isCompleted ? 'Đã hoàn tất' : 'Đang vận chuyển'}
                    </span>
                  </div>
                  <div className="fleet-card-body">
                    <div className="fleet-metric-item">
                      <span className="f-label">Số lô trên xe:</span>
                      <span className="f-val temp-safe">
                        {shipment.lot_count} lô hàng
                      </span>
                    </div>
                    <div className="fleet-metric-item">
                      <span className="f-label">Mở chuyến lúc:</span>
                      <span className="f-val">
                        {new Date(shipment.created_at).toLocaleString('vi-VN')}
                      </span>
                    </div>
                    <div className="fleet-metric-item">
                      <span className="f-label">Ghi chú:</span>
                      <span className="f-val">
                        {shipment.notes || 'Vận chuyển nông sản chuỗi lạnh'}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })
          ) : handovers.length > 0 ? (
            handovers.slice(0, 3).map((h) => (
              <div
                key={h.id}
                className="fleet-card"
                onClick={() => onTabChange('handovers')}
                style={{ cursor: 'pointer' }}
              >
                <div className="fleet-card-header">
                  <div className="fleet-truck-id">
                    <SquircleIcon kind="basket" size="sm" />
                    <span className="truck-plate">
                      Lô {h.lot_code || h.lot_name}
                    </span>
                  </div>
                  <span
                    className={`fleet-status-pill ${
                      h.status === 'accepted' ? 'pill-green' : 'pill-blue'
                    }`}
                  >
                    {h.status === 'accepted'
                      ? 'Đã tiếp nhận'
                      : h.status === 'pending'
                        ? 'Chờ xác nhận'
                        : 'Đã từ chối'}
                  </span>
                </div>
                <div className="fleet-card-body">
                  <div className="fleet-metric-item">
                    <span className="f-label">Bên giao:</span>
                    <span className="f-val">{h.from_organization_name || 'Đơn vị giao'}</span>
                  </div>
                  <div className="fleet-metric-item">
                    <span className="f-label">Bên nhận:</span>
                    <span className="f-val">{h.to_organization_name || 'Đơn vị nhận'}</span>
                  </div>
                  <div className="fleet-metric-item">
                    <span className="f-label">Thời điểm tạo:</span>
                    <span className="f-val">
                      {new Date(h.created_at).toLocaleString('vi-VN')}
                    </span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            recentLots.slice(0, 3).map((lot) => (
              <div
                key={lot.id}
                className="fleet-card"
                onClick={() => onOpenLot(lot.id)}
                style={{ cursor: 'pointer' }}
              >
                <div className="fleet-card-header">
                  <div className="fleet-truck-id">
                    <SquircleIcon nameHint={lot.name} size="sm" />
                    <span className="truck-plate">
                      Mã lô {lot.lot_code || lot.id.slice(0, 8)}
                    </span>
                  </div>
                  <span className="fleet-status-pill pill-green">
                    {lotStatusLabel(lot.status)}
                  </span>
                </div>
                <div className="fleet-card-body">
                  <div className="fleet-metric-item">
                    <span className="f-label">Nông sản:</span>
                    <span className="f-val">{lot.product?.name || lot.name}</span>
                  </div>
                  <div className="fleet-metric-item">
                    <span className="f-label">Khối lượng còn:</span>
                    <span className="f-val temp-safe">
                      {lot.remaining_quantity} {lot.product?.unit || 'kg'}
                    </span>
                  </div>
                  <div className="fleet-metric-item">
                    <span className="f-label">Địa điểm:</span>
                    <span className="f-val">
                      {lot.current_location?.name || 'Đang lưu kho đơn vị'}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* 5. QUICK MODULES GRID WITH SQUIRCLE ICONS */}
      <section className="dashboard-section-block">
        <h3 className="dashboard-block-title">Phân hệ Nghiệp vụ &amp; Tác vụ Nhanh</h3>
        <p className="dashboard-block-sub">Truy cập nhanh các phân hệ chức năng tương ứng với quyền hạn của bạn</p>

        <div className="dashboard-modules-grid">
          {canReadLots && (
            <button
              type="button"
              className="module-tile-card"
              onClick={() => onTabChange('lots')}
            >
              <SquircleIcon kind="bokchoy" size="md" />
              <div className="module-tile-content">
                <h4 className="module-tile-name">Quản lý Lô hàng</h4>
                <p className="module-tile-desc">Theo dõi lô thu hoạch, tem QR, tách lô, gộp lô và lịch sử hành trình.</p>
              </div>
              <span className="tile-arrow">→</span>
            </button>
          )}

          {canReadFarms && (
            <button
              type="button"
              className="module-tile-card"
              onClick={() => onTabChange('overview')}
            >
              <SquircleIcon kind="seedling" size="md" />
              <div className="module-tile-content">
                <h4 className="module-tile-name">Vùng trồng &amp; Canh tác</h4>
                <p className="module-tile-desc">Khai báo thửa đất, diện tích, chứng nhận VietGAP và bảo vệ dữ liệu PII.</p>
              </div>
              <span className="tile-arrow">→</span>
            </button>
          )}

          {canReadHandovers && (
            <button
              type="button"
              className="module-tile-card"
              onClick={() => onTabChange('handovers')}
            >
              <SquircleIcon kind="basket" size="md" />
              <div className="module-tile-content">
                <h4 className="module-tile-name">Bàn giao Nông sản</h4>
                <p className="module-tile-desc">Tạo biên bản bàn giao giữa nông hộ, HTX, vận chuyển và nhà phân phối.</p>
              </div>
              <span className="tile-arrow">→</span>
            </button>
          )}

          {canReadTelemetry && (
            <button
              type="button"
              className="module-tile-card"
              onClick={() => onTabChange('cold-chain-stats')}
            >
              <SquircleIcon kind="frost" size="md" />
              <div className="module-tile-content">
                <h4 className="module-tile-name">Thống kê Chuỗi lạnh</h4>
                <p className="module-tile-desc">Báo cáo vi phạm nhiệt độ theo khung 7 ngày, 30 ngày hoặc 90 ngày.</p>
              </div>
              <span className="tile-arrow">→</span>
            </button>
          )}

          {canVerifyEvents && (
            <button
              type="button"
              className="module-tile-card"
              onClick={() => onTabChange('integrity')}
            >
              <SquircleIcon kind="rice" size="md" />
              <div className="module-tile-content">
                <h4 className="module-tile-name">Tính toàn vẹn Dữ liệu</h4>
                <p className="module-tile-desc">Quét đối soát hàm băm SHA-256 xác thực các sự kiện bất biến.</p>
              </div>
              <span className="tile-arrow">→</span>
            </button>
          )}

          {canReadOrg && (
            <button
              type="button"
              className="module-tile-card"
              onClick={() => onTabChange('organization')}
            >
              <SquircleIcon kind="carrot" size="md" />
              <div className="module-tile-content">
                <h4 className="module-tile-name">Quản trị Tổ chức</h4>
                <p className="module-tile-desc">
                  {canManageOrg
                    ? 'Mời thành viên, phân quyền vai trò và quản lý hồ sơ đơn vị.'
                    : 'Xem thông tin đơn vị, danh sách thành viên và đầu mối liên hệ.'}
                </p>
              </div>
              <span className="tile-arrow">→</span>
            </button>
          )}
        </div>
      </section>
    </div>
  )
}
