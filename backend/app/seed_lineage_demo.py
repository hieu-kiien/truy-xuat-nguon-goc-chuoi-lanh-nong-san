"""Explicit, atomic seed of simulated provenance for manual acceptance."""

import argparse
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.config import settings
from app.core.security import hash_password
from app.models.farm import Farm
from app.models.handover import Handover
from app.models.identity import Organization, User
from app.models.lot import Lot
from app.models.lot_relation import LotRelation
from app.models.product import Product, ProductUnit
from app.services.event_service import append_event

NAMESPACE = UUID("3ed203db-1f54-4eae-b739-83ab0a2d705a")
STOCK = {
    "R1": (100, 30),
    "R2": (80, 30),
    "A": (40, 20),
    "B": (30, 5),
    "C": (30, 20),
    "D": (20, 10),
    "E": (30, 10),
    "F": (10, 5),
    "G": (15, 15),
    "H": (15, 15),
    "I": (12, 12),
    "J": (8, 8),
}
# Explicit fixture topology; expected reachability lives separately in docs/tests.
OPERATIONS = [
    ("split", [("R1", "A", 40), ("R1", "B", 30)]),
    ("split", [("R2", "C", 30), ("R2", "D", 20)]),
    ("merge", [("A", "E", 20), ("C", "E", 10)]),
    ("split", [("B", "F", 10), ("B", "G", 15)]),
    ("merge", [("D", "H", 10), ("F", "H", 5)]),
    ("split", [("E", "I", 12), ("E", "J", 8)]),
]


def _lock_seed(db: Session, namespace: UUID) -> None:
    db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": namespace.int % (2**63 - 1)}
    )


def seed_graph(db: Session, principals: list[Principal], namespace: UUID = NAMESPACE):
    """Insert fixture under maintenance ownership. Caller owns transaction."""

    def identifier(label: str) -> UUID:
        return uuid5(namespace, label)

    # Serialize repeated CLI invocations without taking a database-wide lock.
    _lock_seed(db, namespace)
    ids = {label: identifier(label) for label in STOCK}
    existing = set(db.scalars(select(Lot.id).where(Lot.id.in_(ids.values()))))
    if existing:
        if existing != set(ids.values()):
            raise RuntimeError("Bộ mẫu bị thiếu lô; không tự sửa hoặc ghi đè.")
        return ids

    farm = Farm(
        id=identifier("farm"),
        organization_id=principals[0].organization_id,
        name="Thửa bắp cải Trại Mát",
        area_ha=Decimal("1"),
        latitude=Decimal("10"),
        longitude=Decimal("106"),
    )
    product = Product(
        id=identifier("product"),
        name="Bắp cải trắng"
        if namespace == NAMESPACE
        else f"Bắp cải trắng (mẫu {namespace.hex[:8]})",
        description="Bắp cải tươi dùng để minh họa thu hoạch, tách lô, gộp lô và bàn giao. Dữ liệu mẫu.",
        unit=ProductUnit.KG,
        price=Decimal("0"),
        quantity=0,
    )
    db.add_all([farm, product])
    db.flush()
    for label, (quantity, remaining) in STOCK.items():
        origin = 0 if label.startswith("R") else 2 if label in {"I", "J"} else 1
        holder = 2 if label in {"E", "G", "H", "I", "J"} else 1
        db.add(
            Lot(
                id=ids[label],
                organization_id=principals[origin].organization_id,
                current_holder_organization_id=principals[holder].organization_id,
                farm_id=farm.id if origin == 0 else None,
                name=f"Bắp cải trắng — lô {label}",
                lot_code=f"S34-{label}"
                if namespace == NAMESPACE
                else f"{namespace.hex[:7]}-{label}",
                product_id=product.id,
                quantity=Decimal(quantity),
                remaining_quantity=Decimal(remaining),
                harvested_on=date(2026, 10, 1) if origin == 0 else None,
                status="active",
            )
        )
    db.flush()

    def event(label, actor, kind, payload):
        return append_event(
            db,
            principals[actor],
            ids[label],
            event_type=kind,
            payload={"simulated": True, **payload},
        )

    def transfer(label, sender, recipient):
        handover = Handover(
            id=identifier(f"handover-{label}"),
            lot_id=ids[label],
            from_organization_id=principals[sender].organization_id,
            to_organization_id=principals[recipient].organization_id,
            created_by_user_id=principals[sender].user_id,
            resolved_by_user_id=principals[recipient].user_id,
            status="accepted",
            note="Dữ liệu giả lập Sprint 3–4",
        )
        db.add(handover)
        event(label, sender, "handover_pending", {"handover_id": str(handover.id)})
        event(label, recipient, "handover_accepted", {"handover_id": str(handover.id)})
        db.flush()
        handover.resolved_at = datetime.now(UTC)

    for label in ("R1", "R2"):
        event(
            label,
            0,
            "harvest_recorded",
            {"quantity": str(STOCK[label][0]), "farm_id": str(farm.id)},
        )
        transfer(label, 0, 1)
    for operation, edges in OPERATIONS:
        actor = 2 if edges[0][0] == "E" else 1
        if actor == 2:
            transfer("E", 1, 2)
        for parent, child, quantity in edges:
            db.add(
                LotRelation(
                    id=identifier(f"edge-{parent}-{child}"),
                    organization_id=principals[actor].organization_id,
                    parent_lot_id=ids[parent],
                    child_lot_id=ids[child],
                    quantity=Decimal(quantity),
                    operation=operation,
                )
            )
        for parent in dict.fromkeys(edge[0] for edge in edges):
            event(
                parent,
                actor,
                "lot_split" if operation == "split" else "lot_merged",
                {
                    "children": [
                        {"lot_id": str(ids[c]), "quantity": str(q)}
                        for p, c, q in edges
                        if p == parent
                    ]
                },
            )
        for child in dict.fromkeys(edge[1] for edge in edges):
            event(
                child,
                actor,
                "lot_derived",
                {
                    "operation": operation,
                    "parents": [
                        {"lot_id": str(ids[p]), "quantity": str(q)}
                        for p, c, q in edges
                        if c == child
                    ],
                },
            )
    for label in ("G", "H"):
        transfer(label, 1, 2)
    db.flush()
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Bộ dữ liệu giả lập phả hệ")
    parser.add_argument(
        "--workflow", action="store_true", help="Dựng bộ 18 lô bằng nghiệp vụ thật"
    )
    parser.add_argument(
        "--recall",
        action="store_true",
        help="Dựng bộ 18 lô mẫu thu hồi 4 tầng qua 3 tổ chức có lô tiêu thụ và lô gộp (N3-54)",
    )
    args = parser.parse_args()
    if settings.APP_ENV not in {"development", "staging"} or not settings.DEMO_PASSWORD:
        raise RuntimeError("Seed cần development/staging và DEMO_PASSWORD rõ ràng.")
    engine = create_engine(settings.MIGRATION_DATABASE_URL)
    try:
        with Session(engine) as db, db.begin():
            _lock_seed(db, NAMESPACE)
            principals = []
            for index, (kind, role) in enumerate(
                [
                    ("farm", "grower"),
                    ("cooperative", "cooperative"),
                    ("distribution", "distributor"),
                ]
            ):
                org_id, user_id = (
                    uuid5(NAMESPACE, f"org{index}"),
                    uuid5(NAMESPACE, f"user{index}"),
                )
                org = db.get(Organization, org_id)
                if org is None:
                    org = Organization(
                        id=org_id,
                        name=(
                            "Nông trại Trại Mát",
                            "Hợp tác xã Rau Đà Lạt",
                            "Kho phân phối Rau Việt",
                        )[index],
                        organization_type=kind,
                        is_active=True,
                    )
                    db.add(org)
                    db.flush()
                user = db.get(User, user_id)
                if user is None:
                    user = User(
                        id=user_id,
                        organization_id=org_id,
                        role_code=role,
                        email=f"s34-{kind}@example.com",
                        full_name=org.name,
                        password_hash=hash_password(settings.DEMO_PASSWORD),
                        is_active=True,
                        failed_login_attempts=0,
                    )
                    db.add(user)
                    db.flush()
                principals.append(
                    Principal(
                        user.id,
                        user.email,
                        user.full_name,
                        org.id,
                        org.name,
                        org.organization_type,
                        user.role_code,
                    )
                )
            ids = {} if (args.workflow or args.recall) else seed_graph(db, principals)
        if args.workflow:
            from app.seed_lineage_workflow import seed_workflow

            ids = seed_workflow(engine, principals)
        elif args.recall:
            from app.seed_recall_demo import seed_recall_workflow

            ids = seed_recall_workflow(engine, principals)
        print("Seed ready: " + ", ".join(f"{k}={v}" for k, v in ids.items()))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
