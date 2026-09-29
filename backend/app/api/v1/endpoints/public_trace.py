from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.catalog import Product
from app.models.farm import Farm
from app.models.identity import Organization
from app.models.traceability import Lot, LotEvent, LotLineage
from app.schemas.traceability import (
    PublicTraceEvent,
    PublicTraceLink,
    PublicTraceNode,
    PublicTraceRead,
)

router = APIRouter()
MAX_PUBLIC_EVENTS_PER_LOT = 50


@router.get("/{public_code}", response_model=PublicTraceRead)
def get_public_trace(
    public_code: str,
    db: Annotated[Session, Depends(get_db)],
) -> PublicTraceRead:
    if not 24 <= len(public_code) <= 80:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã truy xuất.")

    db.execute(
        select(func.set_config("app.public_trace_code", public_code, True))
    )
    visible_ids = db.execute(
        text(
            "SELECT lot_id, depth FROM public_trace_lot_ids(:trace_code) "
            "ORDER BY depth DESC, lot_id"
        ),
        {"trace_code": public_code},
    ).all()
    if not visible_ids:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã truy xuất.")

    depth_by_id = {lot_id: depth for lot_id, depth in visible_ids}
    lot_ids = list(depth_by_id)
    lots = list(db.scalars(select(Lot).where(Lot.id.in_(lot_ids))).all())
    root = next((lot for lot in lots if lot.public_code == public_code), None)
    if root is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã truy xuất.")

    products = {
        product.id: product
        for product in db.scalars(
            select(Product).where(Product.id.in_({lot.product_id for lot in lots}))
        ).all()
    }
    farms = {
        farm.id: farm
        for farm in db.scalars(
            select(Farm).where(Farm.id.in_({lot.origin_farm_id for lot in lots}))
        ).all()
    }
    organizations = {
        organization.id: organization
        for organization in db.scalars(
            select(Organization).where(
                Organization.id.in_({lot.origin_organization_id for lot in lots})
            )
        ).all()
    }

    ranked_events = (
        select(
            LotEvent.lot_id.label("lot_id"),
            LotEvent.event_type.label("event_type"),
            LotEvent.occurred_at.label("occurred_at"),
            LotEvent.public_note.label("public_note"),
            func.row_number()
            .over(
                partition_by=LotEvent.lot_id,
                order_by=(LotEvent.occurred_at.desc(), LotEvent.id.desc()),
            )
            .label("event_rank"),
        )
        .where(LotEvent.lot_id.in_(lot_ids))
        .subquery()
    )
    event_rows = db.execute(
        select(
            ranked_events.c.lot_id,
            ranked_events.c.event_type,
            ranked_events.c.occurred_at,
            ranked_events.c.public_note,
        )
        .where(ranked_events.c.event_rank <= MAX_PUBLIC_EVENTS_PER_LOT)
        .order_by(ranked_events.c.lot_id, ranked_events.c.occurred_at.desc())
    ).all()
    events_by_lot: dict = defaultdict(list)
    for row in event_rows:
        events_by_lot[row.lot_id].append(
            PublicTraceEvent(
                event_type=row.event_type,
                occurred_at=row.occurred_at,
                public_note=row.public_note,
            )
        )

    nodes_by_id = {}
    for lot in lots:
        product = products.get(lot.product_id)
        farm = farms.get(lot.origin_farm_id)
        organization = organizations.get(lot.origin_organization_id)
        if product is None or farm is None or organization is None:
            continue
        nodes_by_id[lot.id] = PublicTraceNode(
            depth=depth_by_id[lot.id],
            lot_number=lot.lot_number,
            quantity=lot.quantity,
            unit=lot.unit,
            status=lot.status,
            harvested_at=lot.harvested_at,
            created_at=lot.created_at,
            organization_name=organization.name,
            product_name=product.name,
            product_category=product.category,
            farm_name=farm.name,
            events=events_by_lot[lot.id],
        )

    root_node = nodes_by_id.get(root.id)
    if root_node is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu truy xuất.")

    edge_rows = db.execute(
        select(
            LotLineage.source_lot_id,
            LotLineage.target_lot_id,
            LotLineage.relation_type,
            LotLineage.source_quantity,
            LotLineage.unit,
        ).where(
            LotLineage.source_lot_id.in_(lot_ids),
            LotLineage.target_lot_id.in_(lot_ids),
        )
    ).all()
    lineage = [
        PublicTraceLink(
            source_lot_number=next(
                (lot.lot_number for lot in lots if lot.id == edge.source_lot_id), None
            ),
            target_lot_number=next(
                (lot.lot_number for lot in lots if lot.id == edge.target_lot_id), None
            ),
            relation_type=edge.relation_type,
            source_quantity=edge.source_quantity,
            unit=edge.unit,
        )
        for edge in edge_rows
    ]
    ancestry = sorted(
        (node for lot_id, node in nodes_by_id.items() if lot_id != root.id),
        key=lambda node: node.depth,
        reverse=True,
    )
    return PublicTraceRead(lot=root_node, ancestry=ancestry, lineage=lineage)
