"""Service layer for managing product recalls, lineage reporting, confirmations, and blocking affected lots."""

import logging
from collections import defaultdict, deque
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, contains_eager

from app.core.auth import Principal
from app.core.lot_codes import generate_lot_code
from app.core.tenancy import get_tenant_record, lot_is_historical
from app.models.identity import Organization, User
from app.models.location import Location
from app.models.lot import Lot
from app.models.lot_relation import LotRelation
from app.models.product import Product
from app.models.recall_order import (
    DEFAULT_RECALL_REASON,
    RecallConfirmation,
    RecallOrder,
    RecallOrderLot,
)
from app.schemas.location import LocationRead
from app.schemas.recall import (
    RecallConfirmationRead,
    RecallConfirmCreate,
    RecallCreate,
    RecallLotItem,
    RecallNotificationRead,
    RecallOrderCreate,
    RecallOrderLotRead,
    RecallOrderRead,
    RecallOrganizationProgress,
    RecallReport,
    RecallSummary,
)
from app.services import email_service, event_service, public_trace_cache
from app.services.traversal_service import _roots_and_check_cycle

logger = logging.getLogger(__name__)

ZERO_QUANTITY = Decimal("0.000")


def _generate_recall_code(db: Session) -> str:
    """Generate a collision-resistant human-readable recall code."""
    year = datetime.now(UTC).year
    for _ in range(5):
        candidate = f"RC-{year}-{generate_lot_code()[:6]}"
        exists = db.scalar(
            select(RecallOrder.id).where(RecallOrder.recall_code == candidate)
        )
        if not exists:
            return candidate
    raise RuntimeError("Không thể tạo mã thu hồi duy nhất, vui lòng thử lại.")


def get_blocking_recall(db: Session, lot_id: UUID) -> RecallOrder | None:
    """Return the recall order currently blocking this lot, or None."""
    explicit_entry = db.execute(
        select(RecallOrder, RecallOrderLot)
        .join(RecallOrderLot, RecallOrderLot.recall_order_id == RecallOrder.id)
        .where(RecallOrderLot.lot_id == lot_id)
        .order_by(RecallOrder.created_at.desc())
    ).first()

    if explicit_entry is not None:
        order, lot_entry = explicit_entry
        if order.status == "open" or (
            order.status == "completed" and lot_entry.incident_flag
        ):
            return order
        return None

    ancestor_stmt = text("""
        WITH RECURSIVE ancestors(id) AS (
            SELECT CAST(:lot_id AS uuid)
            UNION
            SELECT r.parent_lot_id
            FROM lot_relations r
            JOIN ancestors a ON r.child_lot_id = a.id
        )
        SELECT ro.id
        FROM recall_orders ro
        WHERE ro.status = 'open'
          AND ro.root_lot_id IN (SELECT id FROM ancestors)
        ORDER BY ro.created_at DESC
        LIMIT 1
    """)
    blocking_id = db.execute(ancestor_stmt, {"lot_id": lot_id}).scalar()
    if blocking_id is not None:
        return db.get(RecallOrder, blocking_id)
    return None


def raise_if_recall_blocked(db: Session, lot_id: UUID) -> None:
    """Raise 409 with the recall order code if the lot is blocked."""
    blocking = get_blocking_recall(db, lot_id)
    if blocking is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Lô đang bị thu hồi. Mã lệnh thu hồi: {blocking.recall_code}. "
                "Vui lòng liên hệ quản trị viên."
            ),
        )


def _compute_lineage_report(
    db: Session,
    principal: Principal,
    lot_id: UUID,
    *,
    is_active_recall_view: bool = False,
) -> RecallReport:
    """Dynamically compute the full descendant graph and summary from lot_relations (N3-50 & N3-51)."""
    db.execute(text("SET LOCAL jit = off"))
    if not is_active_recall_view:
        get_tenant_record(db, Lot, lot_id, principal, allow_historical=True)

    statement = text("""WITH RECURSIVE visible_edges AS MATERIALIZED (
      SELECT * FROM lot_relations
    ), walk(id) AS (
      SELECT CAST(:lot_id AS uuid)
      UNION SELECT r.child_lot_id FROM visible_edges r JOIN walk w ON r.parent_lot_id = w.id
    ) SELECT * FROM visible_edges WHERE child_lot_id IN (SELECT id FROM walk)
    """)

    all_edges = list(
        db.scalars(
            select(LotRelation).from_statement(statement), {"lot_id": lot_id}
        ).all()
    )

    ids = {lot_id}
    for edge in all_edges:
        ids.add(edge.child_lot_id)

    edges = [
        edge
        for edge in all_edges
        if edge.parent_lot_id in ids and edge.child_lot_id in ids
    ]

    _roots_and_check_cycle(db, ids, edges)

    visible_organizations = (
        select(Organization).cte("recall_organizations").prefix_with("MATERIALIZED")
    )
    organization = aliased(Organization, visible_organizations)
    origin_organization = aliased(Organization, name="origin_organizations")

    rows = db.execute(
        select(
            Lot,
            Product,
            Location,
            lot_is_historical(Lot, principal),
            origin_organization.name,
            origin_organization.organization_type,
        )
        .outerjoin(Product, Product.id == Lot.product_id)
        .outerjoin(Location, Location.id == Lot.current_location_id)
        .outerjoin(organization, Lot.current_holder_organization_id == organization.id)
        .outerjoin(origin_organization, Lot.organization_id == origin_organization.id)
        .options(contains_eager(Lot.current_holder_organization, alias=organization))
        .where(Lot.id.in_(ids))
        .order_by(Lot.id)
    ).all()

    if len(rows) != len(ids):
        raise HTTPException(
            403, "Không đủ quyền truy cập toàn bộ phả hệ thu hồi của lô."
        )

    parents: dict[UUID, list[UUID]] = defaultdict(list)
    children: dict[UUID, list[UUID]] = defaultdict(list)
    all_parents: dict[UUID, list[UUID]] = defaultdict(list)
    for edge in all_edges:
        all_parents[edge.child_lot_id].append(edge.parent_lot_id)
    for edge in edges:
        parents[edge.child_lot_id].append(edge.parent_lot_id)
        children[edge.parent_lot_id].append(edge.child_lot_id)

    tiers: dict[UUID, int] = {lot_id: 1}
    multi_source_merge: dict[UUID, bool] = {lot_id: len(all_parents[lot_id]) > 1}

    indegree = {node_id: len(parents[node_id]) for node_id in ids}
    queue: deque[UUID] = deque([lot_id])
    topo_order: list[UUID] = []

    while queue:
        current = queue.popleft()
        topo_order.append(current)
        for child_id in children[current]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                queue.append(child_id)

    for node_id in topo_order:
        if node_id == lot_id:
            continue
        node_parents = parents[node_id]
        if node_parents:
            tiers[node_id] = max(tiers.get(p, 1) for p in node_parents) + 1
            is_multi = len(all_parents[node_id]) > 1 or any(
                multi_source_merge.get(p, False) for p in node_parents
            )
            multi_source_merge[node_id] = is_multi
        else:
            tiers[node_id] = 2
            multi_source_merge[node_id] = len(all_parents[node_id]) > 1

    lot_items: dict[UUID, RecallLotItem] = {}
    involved_org_names: set[str] = set()

    for lot, product, location, historical, origin_org_name, _origin_org_type in rows:
        unit = product.unit if product else "kg"
        status_val = lot.status
        tier = tiers.get(lot.id, 1)
        is_multi = multi_source_merge.get(lot.id, False)

        if status_val == "consumed":
            rem_qty = ZERO_QUANTITY
            cons_qty = (
                Decimal(str(lot.quantity))
                if lot.quantity is not None
                else ZERO_QUANTITY
            )
            rec_qty = ZERO_QUANTITY
        elif status_val == "closed":
            rem_qty = ZERO_QUANTITY
            cons_qty = ZERO_QUANTITY
            rec_qty = ZERO_QUANTITY
        else:
            rem_qty = Decimal(str(lot.remaining_quantity))
            cons_qty = ZERO_QUANTITY
            rec_qty = rem_qty

        holder_org_name = (
            lot.current_holder_organization.name
            if lot.current_holder_organization
            else None
        )
        holder_org_type = (
            lot.current_holder_organization.organization_type
            if lot.current_holder_organization
            else None
        )
        if holder_org_name:
            involved_org_names.add(holder_org_name)
        if origin_org_name:
            involved_org_names.add(origin_org_name)

        loc_read = LocationRead.model_validate(location) if location else None

        effective_historical = bool(historical and not is_active_recall_view)

        item = RecallLotItem(
            id=lot.id,
            lot_code=lot.lot_code,
            name=lot.name,
            tier=tier,
            status=status_val,
            is_multi_source_merge=is_multi,
            organization_id=lot.organization_id,
            current_holder_organization_id=lot.current_holder_organization_id,
            current_holder_organization_name=holder_org_name,
            holder_org_type=holder_org_type,
            current_location_id=lot.current_location_id,
            current_location=loc_read,
            quantity=Decimal(str(lot.quantity)) if lot.quantity is not None else None,
            remaining_quantity=rem_qty,
            consumed_quantity=cons_qty,
            recoverable_quantity=rec_qty,
            unit=unit,
            harvested_on=lot.harvested_on,
            historical_only=effective_historical,
            parent_lot_ids=all_parents[lot.id],
        )

        if effective_historical:
            item.remaining_quantity = ZERO_QUANTITY
            item.recoverable_quantity = ZERO_QUANTITY
            item.current_holder_organization_id = None
            item.current_holder_organization_name = None
            item.holder_org_type = None
            item.current_location_id = None
            item.current_location = None
            item.status = "transferred"

        lot_items[lot.id] = item

    root_item = lot_items[lot_id]
    descendants = [
        lot_items[nid] for nid in topo_order if nid != lot_id and nid in lot_items
    ]

    total_recoverable = sum(d.recoverable_quantity for d in descendants)
    if root_item.status == "active":
        total_recoverable += root_item.recoverable_quantity

    total_consumed = sum(d.consumed_quantity for d in descendants)
    if root_item.status == "consumed":
        total_consumed += root_item.consumed_quantity

    has_multi = any(d.is_multi_source_merge for d in descendants)
    has_consumed = any(d.status == "consumed" for d in descendants)

    summary = RecallSummary(
        root_lot_id=root_item.id,
        root_lot_code=root_item.lot_code,
        root_lot_name=root_item.name,
        initial_quantity=root_item.quantity,
        unit=root_item.unit,
        total_affected_lots=len(ids),
        total_descendants_count=len(descendants),
        total_recoverable_kg=total_recoverable,
        total_consumed_kg=total_consumed,
        involved_organizations_count=len(involved_org_names),
        involved_organizations=sorted(involved_org_names),
        has_multi_source_merge=has_multi,
        has_consumed_lot=has_consumed,
    )

    return RecallReport(
        root_lot=root_item,
        summary=summary,
        descendants=descendants,
        affected_lots=[root_item, *descendants],
    )


def _compute_involved_organizations(
    db: Session,
    order: RecallOrder,
    report: RecallReport,
) -> tuple[
    list[RecallOrganizationProgress],
    list[RecallConfirmationRead],
    dict[UUID, list[RecallLotItem]],
]:
    """Compute the involved organizations, their affected lots, and confirmation progress (N3-52 & N3-55)."""
    org_lots: dict[UUID, list[RecallLotItem]] = defaultdict(list)
    seen_org_lot: set[tuple[UUID, UUID]] = set()
    org_ids: set[UUID] = set()

    for item in report.affected_lots:
        if item.current_holder_organization_id:
            org_ids.add(item.current_holder_organization_id)
            key = (item.current_holder_organization_id, item.id)
            if key not in seen_org_lot:
                seen_org_lot.add(key)
                org_lots[item.current_holder_organization_id].append(item)
        if item.organization_id:
            org_ids.add(item.organization_id)
            key = (item.organization_id, item.id)
            if key not in seen_org_lot:
                seen_org_lot.add(key)
                org_lots[item.organization_id].append(item)

    for entry in order.lot_entries:
        if entry.lot and entry.lot.current_holder_organization_id:
            holder_id = entry.lot.current_holder_organization_id
            org_ids.add(holder_id)

    confirmations_rows = db.execute(
        select(RecallConfirmation, Organization.name, User.full_name)
        .outerjoin(Organization, Organization.id == RecallConfirmation.organization_id)
        .outerjoin(User, User.id == RecallConfirmation.confirmed_by_user_id)
        .where(RecallConfirmation.recall_order_id == order.id)
        .order_by(RecallConfirmation.confirmed_at.asc())
    ).all()

    confirmations_by_org: dict[UUID, RecallConfirmationRead] = {}
    confirmation_reads: list[RecallConfirmationRead] = []
    for conf, org_name, user_name in confirmations_rows:
        org_ids.add(conf.organization_id)
        conf_read = RecallConfirmationRead(
            id=conf.id,
            recall_order_id=conf.recall_order_id,
            organization_id=conf.organization_id,
            organization_name=org_name,
            confirmed_by_user_id=conf.confirmed_by_user_id,
            confirmed_by_user_name=user_name,
            note=conf.note,
            confirmed_at=conf.confirmed_at,
        )
        confirmations_by_org[conf.organization_id] = conf_read
        confirmation_reads.append(conf_read)

    orgs_map: dict[UUID, Organization] = {}
    if org_ids:
        for org_row in db.scalars(
            select(Organization).where(Organization.id.in_(org_ids))
        ).all():
            orgs_map[org_row.id] = org_row

    progress_list: list[RecallOrganizationProgress] = []
    for org_id in org_ids:
        org_obj = orgs_map.get(org_id)
        org_name = org_obj.name if org_obj else f"Tổ chức {str(org_id)[:8]}"
        org_type = org_obj.organization_type if org_obj else None
        conf_item = confirmations_by_org.get(org_id)
        items_for_org = org_lots.get(org_id, [])
        held_recoverable = sum(
            (
                i.recoverable_quantity
                for i in items_for_org
                if i.current_holder_organization_id == org_id
            ),
            ZERO_QUANTITY,
        )
        progress_list.append(
            RecallOrganizationProgress(
                organization_id=org_id,
                organization_name=org_name,
                organization_type=org_type,
                status="confirmed" if conf_item is not None else "pending",
                confirmed_at=conf_item.confirmed_at if conf_item else None,
                confirmed_by_user_id=(
                    conf_item.confirmed_by_user_id if conf_item else None
                ),
                confirmed_by_user_name=(
                    conf_item.confirmed_by_user_name if conf_item else None
                ),
                note=conf_item.note if conf_item else None,
                affected_lot_ids=[i.id for i in items_for_org],
                affected_lot_codes=[i.lot_code or i.name for i in items_for_org],
                recoverable_quantity=held_recoverable,
            )
        )

    progress_list.sort(key=lambda p: (p.organization_name, str(p.organization_id)))
    return progress_list, confirmation_reads, org_lots


def send_recall_notices(
    db: Session,
    order: RecallOrder,
    progress_list: list[RecallOrganizationProgress],
    *,
    sender_organization_id: UUID,
) -> int:
    """Send the recall notice to every organization involved (N3-57).

    The notice names the recall code and the path to the order only. It never
    lists the affected lots, because the recipient opens the order to see
    them. Organizations without a contact address are skipped.
    """
    delivered = 0
    for progress in progress_list:
        organization = db.get(Organization, progress.organization_id)
        if organization is None or not organization.contact_email:
            continue
        delivery = email_service.deliver_email(
            db,
            recipient_email=organization.contact_email,
            subject=f"[{order.recall_code}] Lệnh thu hồi lô hàng liên quan",
            body=email_service.recall_notice_body(
                order.recall_code,
                order.root_lot_id,
                organization_name=organization.name,
            ),
            kind=email_service.RECALL_NOTICE_KIND,
            organization_id=sender_organization_id,
            related_id=str(order.id),
        )
        if delivery.delivered:
            delivered += 1
        else:
            logger.warning(
                "Recall notice for %s could not be delivered to organization %s: %s",
                order.recall_code,
                progress.organization_id,
                delivery.error,
            )
    return delivered


def enrich_recall_order(
    db: Session, principal: Principal, order: RecallOrder
) -> RecallOrder:
    """Attach dynamically computed descendant lots, summary, and organization confirmation progress onto order."""
    report = _compute_lineage_report(
        db, principal, order.root_lot_id, is_active_recall_view=True
    )
    progress_list, confirmations_list, _ = _compute_involved_organizations(
        db, order, report
    )

    lot_reads = [
        RecallOrderLotRead(
            id=entry.id,
            lot_id=entry.lot_id,
            lot_code=entry.lot.lot_code if entry.lot else None,
            lot_name=entry.lot.name if entry.lot else "",
            incident_flag=entry.incident_flag,
        )
        for entry in order.lot_entries
    ]

    total_orgs = len(progress_list)
    confirmed_orgs_names = [
        p.organization_name for p in progress_list if p.status == "confirmed"
    ]
    pending_orgs_names = [
        p.organization_name for p in progress_list if p.status == "pending"
    ]
    confirmed_count = len(confirmed_orgs_names)

    order.lots = lot_reads  # type: ignore[attr-defined]
    order.root_lot_item = report.root_lot  # type: ignore[attr-defined]
    order.summary = report.summary  # type: ignore[attr-defined]
    order.descendants = report.descendants  # type: ignore[attr-defined]
    order.affected_lots = report.affected_lots  # type: ignore[attr-defined]
    order.total_organizations_count = total_orgs  # type: ignore[attr-defined]
    order.confirmed_organizations_count = confirmed_count  # type: ignore[attr-defined]
    order.progress_text = f"{confirmed_count}/{total_orgs}"  # type: ignore[attr-defined]
    order.pending_organizations = pending_orgs_names  # type: ignore[attr-defined]
    order.confirmed_organizations = confirmed_orgs_names  # type: ignore[attr-defined]
    order.organizations_progress = progress_list  # type: ignore[attr-defined]
    order.confirmations_read = confirmations_list  # type: ignore[attr-defined]
    return order


def serialize_recall_order(
    db: Session, principal: Principal, order: RecallOrder
) -> RecallOrderRead:
    """Serialize a RecallOrder into RecallOrderRead with full dynamic lineage and progress."""
    enrich_recall_order(db, principal, order)
    return RecallOrderRead(
        id=order.id,
        recall_code=order.recall_code,
        root_lot_id=order.root_lot_id,
        opened_by_user_id=order.opened_by_user_id,
        opened_by_organization_id=order.opened_by_organization_id,
        reason=order.reason,
        status=order.status,
        created_at=order.created_at,
        completed_at=order.completed_at,
        lots=getattr(order, "lots", []),
        root_lot=getattr(order, "root_lot_item", None),
        summary=getattr(order, "summary", None),
        descendants=getattr(order, "descendants", []),
        affected_lots=getattr(order, "affected_lots", []),
        total_organizations_count=getattr(order, "total_organizations_count", 0),
        confirmed_organizations_count=getattr(
            order, "confirmed_organizations_count", 0
        ),
        progress_text=getattr(order, "progress_text", "0/0"),
        pending_organizations=getattr(order, "pending_organizations", []),
        confirmed_organizations=getattr(order, "confirmed_organizations", []),
        organizations_progress=getattr(order, "organizations_progress", []),
        confirmations=getattr(order, "confirmations_read", []),
    )


def open_recall(
    db: Session,
    principal: Principal,
    payload: RecallCreate,
) -> RecallOrder:
    """Open a new recall order for a compromised lot (N3-49)."""
    if principal.role not in {"inspector", "system_admin", "organization_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ cán bộ kiểm tra hoặc quản trị tổ chức đang giữ lô được mở lệnh thu hồi.",
        )

    lot = db.get(Lot, payload.lot_id)
    if lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lô hàng yêu cầu thu hồi.",
        )

    if principal.role == "organization_admin":
        if lot.current_holder_organization_id != principal.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Quản trị viên chỉ được mở lệnh thu hồi cho lô do tổ chức mình đang giữ.",
            )

    if lot.status == "consumed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể mở lệnh thu hồi trực tiếp trên lô đã tiêu thụ hết.",
        )

    existing_open = db.scalar(
        select(RecallOrder).where(
            RecallOrder.root_lot_id == lot.id,
            RecallOrder.status == "open",
        )
    )
    if existing_open is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RECALL_ALREADY_OPEN",
                "message": f"Lô này đã có lệnh thu hồi đang mở ({existing_open.recall_code}).",
                "recall_id": str(existing_open.id),
                "recall_code": existing_open.recall_code,
            },
        )

    recall_code = _generate_recall_code(db)
    order = RecallOrder(
        recall_code=recall_code,
        root_lot_id=lot.id,
        opened_by_user_id=principal.user_id,
        opened_by_organization_id=principal.organization_id,
        reason=payload.reason,
        status="open",
    )
    db.add(order)
    db.flush()

    db.add(
        RecallOrderLot(
            recall_order_id=order.id,
            organization_id=principal.organization_id,
            lot_id=lot.id,
            incident_flag=True,
        )
    )
    db.flush()

    event_service.append_event(
        db,
        principal,
        lot.id,
        event_type="recall_opened",
        payload={
            "recall_id": str(order.id),
            "recall_code": order.recall_code,
            "reason": order.reason,
            "opened_by_role": principal.role,
            "opened_by_organization_id": str(principal.organization_id),
        },
    )

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        conflict = db.scalar(
            select(RecallOrder).where(
                RecallOrder.root_lot_id == lot.id,
                RecallOrder.status == "open",
            )
        )
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "RECALL_ALREADY_OPEN",
                    "message": f"Lô này đã có lệnh thu hồi đang mở ({conflict.recall_code}).",
                    "recall_id": str(conflict.id),
                    "recall_code": conflict.recall_code,
                },
            ) from exc
        raise

    db.refresh(order)
    # Trang công khai phải phản ánh thu hồi ngay, không chờ cache hết hạn (S-50).
    public_trace_cache.invalidate_all()
    enriched = enrich_recall_order(db, principal, order)
    # N3-57: gửi thông báo tới mọi tổ chức liên quan qua dịch vụ gửi thư.
    send_recall_notices(
        db,
        order,
        list(getattr(enriched, "organizations_progress", []) or []),
        sender_organization_id=principal.organization_id,
    )
    return enriched


def create_recall_order(
    db: Session, principal: Principal, payload: RecallOrderCreate
) -> RecallOrder:
    """Create a recall order with explicit code and lot list (N3-53)."""
    existing = db.scalar(
        select(RecallOrder).where(RecallOrder.recall_code == payload.code)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mã lệnh thu hồi {payload.code} đã tồn tại.",
        )

    lots = list(
        db.scalars(
            select(Lot).where(
                Lot.id.in_(payload.lot_ids),
                Lot.current_holder_organization_id == principal.organization_id,
            )
        ).all()
    )
    if len(lots) != len(payload.lot_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Một hoặc nhiều lô không thuộc tổ chức đang giữ.",
        )

    reason_text = (payload.note or "").strip()
    if len(reason_text) < 20:
        reason_text = DEFAULT_RECALL_REASON

    order = RecallOrder(
        recall_code=payload.code,
        root_lot_id=lots[0].id,
        opened_by_user_id=principal.user_id,
        opened_by_organization_id=principal.organization_id,
        reason=reason_text,
        status="open",
    )
    db.add(order)
    db.flush()

    for lot in lots:
        db.add(
            RecallOrderLot(
                recall_order_id=order.id,
                organization_id=principal.organization_id,
                lot_id=lot.id,
                incident_flag=True,
            )
        )

    db.flush()
    for lot in lots:
        event_service.append_event(
            db,
            principal,
            lot.id,
            event_type="recall_opened",
            payload={
                "recall_id": str(order.id),
                "recall_code": order.recall_code,
                "reason": order.reason,
                "opened_by_role": principal.role,
                "opened_by_organization_id": str(principal.organization_id),
            },
        )
    db.commit()
    db.refresh(order)
    public_trace_cache.invalidate_all()
    enriched = enrich_recall_order(db, principal, order)
    # N3-57: gửi thông báo tới mọi tổ chức liên quan qua dịch vụ gửi thư.
    send_recall_notices(
        db,
        order,
        list(getattr(enriched, "organizations_progress", []) or []),
        sender_organization_id=principal.organization_id,
    )
    return enriched


def _is_org_involved_in_order(
    db: Session, organization_id: UUID, order: RecallOrder
) -> bool:
    """Return True if organization_id is the opener, holds/created a lot in the recall tree, or is in recall_order_lots."""
    if order.opened_by_organization_id == organization_id:
        return True

    check_stmt = text("""
        WITH RECURSIVE tree(id) AS (
            SELECT CAST(:root_lot_id AS uuid)
            UNION
            SELECT r.child_lot_id
            FROM lot_relations r
            JOIN tree t ON r.parent_lot_id = t.id
        )
        SELECT 1
        FROM lots l
        WHERE l.id IN (SELECT id FROM tree)
          AND (
              l.current_holder_organization_id = CAST(:org_id AS uuid)
              OR l.organization_id = CAST(:org_id AS uuid)
          )
        UNION
        SELECT 1
        FROM recall_order_lots rol
        WHERE rol.recall_order_id = CAST(:order_id AS uuid)
          AND rol.organization_id = CAST(:org_id AS uuid)
        LIMIT 1
    """)
    found = db.execute(
        check_stmt,
        {
            "root_lot_id": order.root_lot_id,
            "org_id": organization_id,
            "order_id": order.id,
        },
    ).scalar()
    return found is not None


def list_recalls(
    db: Session, principal: Principal, *, status_filter: str | None = None
) -> list[RecallOrder]:
    """List recall orders visible to the principal, enriched with dynamic lineage and progress."""
    stmt = select(RecallOrder).order_by(RecallOrder.created_at.desc())
    if status_filter:
        stmt = stmt.where(RecallOrder.status == status_filter)

    candidates = list(db.scalars(stmt).all())
    results: list[RecallOrder] = []
    for order in candidates:
        if principal.role not in {"inspector", "system_admin"}:
            if not _is_org_involved_in_order(db, principal.organization_id, order):
                continue
        enrich_recall_order(db, principal, order)
        results.append(order)
    return results


def list_recall_orders(
    db: Session, principal: Principal, *, status_filter: str | None = None
) -> list[RecallOrder]:
    """Alias for list_recalls supporting status_filter."""
    return list_recalls(db, principal, status_filter=status_filter)


def get_recall(db: Session, principal: Principal, recall_id: UUID) -> RecallOrder:
    """Get details of a single recall order with dynamic lineage and confirmation progress."""
    order = db.get(RecallOrder, recall_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lệnh thu hồi.",
        )

    if principal.role not in {"inspector", "system_admin"}:
        if not _is_org_involved_in_order(db, principal.organization_id, order):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xem lệnh thu hồi này.",
            )

    return enrich_recall_order(db, principal, order)


def list_recall_notifications(
    db: Session,
    principal: Principal,
    *,
    include_completed: bool = False,
) -> list[RecallNotificationRead]:
    """Return recall notifications for the caller's organization (N3-55 AC1)."""
    orders = list_recalls(
        db,
        principal,
        status_filter=None if include_completed else "open",
    )
    notifications: list[RecallNotificationRead] = []

    for order in orders:
        progress_list: list[RecallOrganizationProgress] = getattr(
            order, "organizations_progress", []
        )
        org_progress = next(
            (
                p
                for p in progress_list
                if p.organization_id == principal.organization_id
            ),
            None,
        )
        if org_progress is None and principal.role not in {"inspector", "system_admin"}:
            continue

        all_affected: list[RecallLotItem] = getattr(order, "affected_lots", [])
        if principal.role in {"inspector", "system_admin"} and org_progress is None:
            org_lots = all_affected
            handling_status = "confirmed" if order.status == "completed" else "pending"
            confirmed_at = order.completed_at
            note = None
        else:
            org_lots = [
                item
                for item in all_affected
                if item.current_holder_organization_id == principal.organization_id
                or item.organization_id == principal.organization_id
            ]
            handling_status = org_progress.status if org_progress else "pending"
            confirmed_at = org_progress.confirmed_at if org_progress else None
            note = org_progress.note if org_progress else None

        root_item: RecallLotItem | None = getattr(order, "root_lot_item", None)
        notifications.append(
            RecallNotificationRead(
                recall_id=order.id,
                recall_code=order.recall_code,
                root_lot_id=order.root_lot_id,
                root_lot_code=root_item.lot_code if root_item else None,
                root_lot_name=root_item.name if root_item else "",
                reason=order.reason,
                status=order.status,
                created_at=order.created_at,
                organization_id=principal.organization_id,
                organization_name=principal.organization_name,
                handling_status=handling_status,  # type: ignore[arg-type]
                confirmed_at=confirmed_at,
                note=note,
                total_organizations_count=getattr(
                    order, "total_organizations_count", 0
                ),
                confirmed_organizations_count=getattr(
                    order, "confirmed_organizations_count", 0
                ),
                progress_text=getattr(order, "progress_text", "0/0"),
                affected_lots=org_lots,
            )
        )

    return notifications


def confirm_recall_handling(
    db: Session,
    principal: Principal,
    recall_id: UUID,
    payload: RecallConfirmCreate,
) -> RecallOrder:
    """Confirm that the caller's organization has handled its affected lots in a recall order (N3-55 & N3-52).

    - Append-only: Once confirmed, an organization's confirmation cannot be overwritten or deleted.
    - Auto-completion: When the last remaining involved organization confirms, the recall order
      automatically transitions to 'completed' and appends an immutable 'recall_completed' event.
    """
    order = db.scalar(
        select(RecallOrder)
        .where(RecallOrder.id == recall_id)
        .with_for_update(of=RecallOrder)
        .execution_options(populate_existing=True)
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lệnh thu hồi.",
        )

    report = _compute_lineage_report(
        db, principal, order.root_lot_id, is_active_recall_view=True
    )
    progress_list, _, org_lots = _compute_involved_organizations(db, order, report)

    org_progress = next(
        (p for p in progress_list if p.organization_id == principal.organization_id),
        None,
    )
    if org_progress is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tổ chức của bạn không có lô hàng liên quan trong lệnh thu hồi này.",
        )

    existing_confirmation = db.scalar(
        select(RecallConfirmation).where(
            RecallConfirmation.recall_order_id == order.id,
            RecallConfirmation.organization_id == principal.organization_id,
        )
    )
    if existing_confirmation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xác nhận xử lý thu hồi là sự kiện bất biến (append-only): tổ chức của bạn đã xác nhận trước đó và không thể ghi đè.",
        )

    if order.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lệnh thu hồi này đã hoàn tất.",
        )

    confirmation = RecallConfirmation(
        recall_order_id=order.id,
        organization_id=principal.organization_id,
        confirmed_by_user_id=principal.user_id,
        note=payload.note,
    )
    try:
        with db.begin_nested():
            db.add(confirmation)
            db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xác nhận xử lý thu hồi là sự kiện bất biến (append-only): tổ chức của bạn đã xác nhận trước đó.",
        ) from exc

    org_affected_items = org_lots.get(principal.organization_id, [])
    target_lot_id = (
        org_affected_items[0].id if org_affected_items else order.root_lot_id
    )

    event_service.append_event(
        db,
        principal,
        target_lot_id,
        event_type="recall_confirmed",
        payload={
            "recall_id": str(order.id),
            "recall_code": order.recall_code,
            "organization_id": str(principal.organization_id),
            "confirmed_by_user_id": str(principal.user_id),
            "note": payload.note,
            "affected_lot_codes": [i.lot_code or i.name for i in org_affected_items],
        },
    )

    # Re-evaluate progress after adding this confirmation (N3-52 AC2)
    updated_progress, _, _ = _compute_involved_organizations(db, order, report)
    all_confirmed = bool(updated_progress) and all(
        p.status == "confirmed" for p in updated_progress
    )

    if all_confirmed and order.status != "completed":
        completed_time = datetime.now(UTC)
        order.status = "completed"
        order.completed_at = completed_time
        db.flush()

        event_service.append_event(
            db,
            principal,
            order.root_lot_id,
            event_type="recall_completed",
            payload={
                "recall_id": str(order.id),
                "recall_code": order.recall_code,
                "completed_at": completed_time.isoformat(),
                "total_organizations_count": len(updated_progress),
                "confirmed_organizations_count": len(updated_progress),
                "completed_by_organization_id": str(principal.organization_id),
            },
        )

    db.commit()
    db.refresh(order)
    # Trang công khai phải phản ánh thu hồi ngay, không chờ cache hết hạn (S-50).
    public_trace_cache.invalidate_all()
    return enrich_recall_order(db, principal, order)


def complete_recall_order(
    db: Session, principal: Principal, recall_order_id: UUID
) -> RecallOrder:
    """Mark a recall order as completed."""
    order = get_recall(db, principal, recall_order_id)
    if order.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lệnh thu hồi đã hoàn tất từ trước.",
        )

    completed_time = datetime.now(UTC)
    order.status = "completed"
    order.completed_at = completed_time
    db.flush()

    event_service.append_event(
        db,
        principal,
        order.root_lot_id,
        event_type="recall_completed",
        payload={
            "recall_id": str(order.id),
            "recall_code": order.recall_code,
            "completed_at": completed_time.isoformat(),
            "completed_by_organization_id": str(principal.organization_id),
        },
    )
    db.commit()
    db.refresh(order)
    public_trace_cache.invalidate_all()
    return enrich_recall_order(db, principal, order)


def update_incident_flag(
    db: Session,
    principal: Principal,
    recall_order_id: UUID,
    lot_id: UUID,
    incident_flag: bool,
) -> None:
    """Update the incident flag for a lot within a recall order."""
    order = db.get(RecallOrder, recall_order_id)
    if order is None or (
        principal.role not in {"inspector", "system_admin"}
        and order.opened_by_organization_id != principal.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kh?ng t?m th?y l?nh thu h?i.",
        )

    entry = db.scalar(
        select(RecallOrderLot).where(
            RecallOrderLot.recall_order_id == recall_order_id,
            RecallOrderLot.lot_id == lot_id,
        )
    )
    if entry is None:
        report = _compute_lineage_report(
            db, principal, order.root_lot_id, is_active_recall_view=True
        )
        matched_lot = next(
            (item for item in report.affected_lots if item.id == lot_id),
            None,
        )
        if matched_lot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kh?ng t?m th?y l? trong l?nh thu h?i.",
            )
        entry = RecallOrderLot(
            recall_order_id=recall_order_id,
            organization_id=order.opened_by_organization_id,
            lot_id=lot_id,
            incident_flag=incident_flag,
        )
        db.add(entry)
    else:
        entry.incident_flag = incident_flag

    db.commit()
    db.refresh(order)
    public_trace_cache.invalidate_all()


# --- N3-51: Recall Lineage Reporting ---


def get_recall_report(db: Session, principal: Principal, lot_id: UUID) -> dict:
    """Traverse all descendant lots to generate a comprehensive recall report."""
    report = _compute_lineage_report(db, principal, lot_id, is_active_recall_view=False)
    return report.model_dump()
