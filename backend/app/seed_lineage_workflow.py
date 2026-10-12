"""Versioned demo built with the application's actual business services."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.farm import Farm
from app.models.lot import Lot
from app.models.product import Product
from app.schemas.handover import HandoverCreate
from app.schemas.lineage import LotMerge, LotSplit
from app.schemas.lot import LotCreate
from app.seed_lineage_demo import _lock_seed
from app.services import handover_service, lineage_service, lot_service

NAMESPACE = UUID("dd4fa977-8933-4c0a-bf32-236ac67f8013")
LABELS = (
    "R1",
    "R2",
    "R3",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
    "M1",
    "M2",
    "M3",
    "D1",
    "D2",
    "E1",
    "E2",
    "F1",
    "F2",
)


def seed_workflow(
    engine: Engine, principals: list[Principal], namespace: UUID = NAMESPACE
):
    # Service commits release savepoints; the whole seed remains one owner
    # transaction, including an injected failure during any business operation.
    with (
        engine.begin() as connection,
        Session(bind=connection, join_transaction_mode="create_savepoint") as db,
    ):
        _lock_seed(db, namespace)
        product_id = uuid5(namespace, "product")
        existing = list(db.scalars(select(Lot).where(Lot.product_id == product_id)))
        if existing:
            labels = {lot.name.rsplit(" — ", 1)[-1]: lot.id for lot in existing}
            if len(existing) != 18 or set(labels) != set(LABELS):
                raise RuntimeError(
                    "Bộ mẫu nghiệp vụ chưa đầy đủ; không ghi đè dữ liệu."
                )
            return {label: labels[label] for label in LABELS}
        if db.get(Product, product_id) is not None:
            raise RuntimeError(
                "Bộ mẫu có danh mục nhưng thiếu lô; cần kiểm tra trước khi chạy lại."
            )
        product = Product(
            id=product_id,
            name="Bắp cải xanh"
            if namespace == NAMESPACE
            else f"Bắp cải xanh (mẫu {namespace.hex[:8]})",
            description="Dữ liệu mẫu: ba lô thu hoạch qua hợp tác xã rồi kho phân phối, có tách và gộp chéo.",
            unit="kg",
        )
        db.add(product)
        db.flush()
        lots = {}

        def label(lot, value):
            lot.name = f"Bắp cải xanh — {value}"
            lots[value] = lot
            db.flush()

        def transfer(lot, sender, receiver):
            handover = handover_service.create_handover(
                db,
                principals[sender],
                HandoverCreate(
                    lot_id=lot.id,
                    to_organization_id=principals[receiver].organization_id,
                    note="Dữ liệu mẫu nghiệp vụ Sprint 3–4.",
                ),
            )
            handover_service.accept_handover(db, principals[receiver], handover["id"])

        def split(source, labels, amounts, actor):
            result = lineage_service.split_lot(
                db,
                principals[actor],
                lots[source].id,
                LotSplit(
                    children=[
                        {"name": f"Bắp cải xanh — {value}", "quantity": amount}
                        for value, amount in zip(labels, amounts, strict=True)
                    ]
                ),
            )
            for value, lot in zip(labels, result["children"], strict=True):
                lots[value] = lot

        for index, name in enumerate(
            ("Thửa bắp cải số 1", "Thửa bắp cải số 2", "Thửa bắp cải số 3"), 1
        ):
            farm = Farm(
                id=uuid5(namespace, f"farm{index}"),
                organization_id=principals[0].organization_id,
                name=name,
                area_ha=Decimal("1"),
                latitude=Decimal("11.924850"),
                longitude=Decimal("108.497210"),
            )
            db.add(farm)
            db.flush()
            root = lot_service.create_harvest_lot(
                db,
                principals[0],
                LotCreate(
                    farm_id=farm.id,
                    product_id=product.id,
                    harvested_on=date(2026, 10, 1),
                    quantity=Decimal("100"),
                ),
            )
            label(root, f"R{index}")
            transfer(root, 0, 1)
        for source, children in [
            ("R1", ["A1", "A2"]),
            ("R2", ["B1", "B2"]),
            ("R3", ["C1", "C2"]),
        ]:
            split(source, children, ["50", "50"], 1)
        for value, parents in [
            ("M1", ["A1", "B1"]),
            ("M2", ["A2", "C1"]),
            ("M3", ["B2", "C2"]),
        ]:
            merged = lineage_service.merge_lots(
                db,
                principals[1],
                LotMerge(
                    name=f"Bắp cải xanh — {value}",
                    parents=[
                        {"lot_id": lots[parent].id, "quantity": "50"}
                        for parent in parents
                    ],
                ),
            )
            lots[value] = merged
            transfer(merged, 1, 2)
        for source, children, amounts in [
            ("M1", ["D1", "D2"], ["40", "60"]),
            ("M2", ["E1", "E2"], ["50", "50"]),
            ("M3", ["F1", "F2"], ["30", "70"]),
        ]:
            split(source, children, amounts, 2)
        db.commit()
        return {label: lot.id for label, lot in lots.items()}
