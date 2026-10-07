from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.main import app
from app.models.event import Event
from app.models.farm import Farm
from app.models.handover import Handover
from app.models.lot import Lot
from app.models.product import Product
from app.services import event_service, lot_service
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


def _make_farm(db: Session, organization_id) -> Farm:
    farm = Farm(
        organization_id=organization_id,
        name=f"sprint2-lot-farm-{uuid4().hex[:8]}",
        area_ha=Decimal("1.2500"),
        latitude=Decimal("10.762622"),
        longitude=Decimal("106.660172"),
    )
    db.add(farm)
    db.commit()
    return farm


def _make_principal(identity: IdentityFixture) -> Principal:
    return Principal(
        user_id=identity.user_id,
        email=identity.email,
        full_name="Integration test user",
        organization_id=identity.organization_id,
        organization_name="Integration test organization",
        organization_type="farm",
        role="grower",
    )


def _delete_lots_with_events(db: Session, lot_ids: list) -> None:
    if not lot_ids:
        return
    with db.begin_nested():
        db.execute(text("ALTER TABLE events DISABLE TRIGGER USER"))
        db.execute(delete(Handover).where(Handover.lot_id.in_(lot_ids)))
        db.execute(delete(Event).where(Event.lot_id.in_(lot_ids)))
        db.execute(delete(Lot).where(Lot.id.in_(lot_ids)))
        db.execute(text("ALTER TABLE events ENABLE TRIGGER USER"))
    db.commit()


@pytest.mark.asyncio
async def test_lot_create_validates_fields_and_retries_a_code_collision(
    admin_session: Session, identity_factory, monkeypatch
):
    owner = identity_factory()
    farm = _make_farm(admin_session, owner.organization_id)
    product = Product(name=f"sprint2-lot-product-{uuid4().hex[:8]}", unit="kg")
    collision_code = f"C{uuid4().hex[:7].upper()}"
    retry_code = f"R{uuid4().hex[:7].upper()}"
    existing_lot = Lot(
        organization_id=owner.organization_id,
        current_holder_organization_id=owner.organization_id,
        farm_id=farm.id,
        name="Existing lot",
        lot_code=collision_code,
        remaining_quantity=Decimal("0"),
        status="active",
    )
    admin_session.add_all([product, existing_lot])
    admin_session.commit()
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()
    request_base = {
        "farm_id": str(farm.id),
        "product_id": str(product.id),
        "harvested_on": today,
        "quantity": "12.500",
    }

    async with _client() as client:
        await _login(client, owner)
        invalid_quantity = await client.post(
            "/api/v1/lots/", json={**request_base, "quantity": 0}
        )
        assert invalid_quantity.status_code == 422
        assert any(
            error["loc"][-1] == "quantity"
            for error in invalid_quantity.json()["detail"]
        )

        future_date = await client.post(
            "/api/v1/lots/",
            json={**request_base, "harvested_on": (date(2999, 1, 1)).isoformat()},
        )
        assert future_date.status_code == 422
        assert any(
            error["loc"][-1] == "harvested_on" for error in future_date.json()["detail"]
        )

        generated_codes = iter([collision_code, retry_code])
        monkeypatch.setattr(
            lot_service, "generate_lot_code", lambda: next(generated_codes)
        )
        created = await client.post("/api/v1/lots/", json=request_base)

    assert created.status_code == 201, created.text
    assert created.json()["lot_code"] == retry_code
    assert Decimal(created.json()["quantity"]) == Decimal("12.500")
    created_lot_id = created.json()["id"]
    events = list(
        admin_session.scalars(
            select(Event).where(Event.lot_id == UUID(created_lot_id))
        ).all()
    )
    assert len(events) == 1
    assert event_service.verify_event_chain(events)["valid"] is True

    lot_ids = list(
        admin_session.scalars(select(Lot.id).where(Lot.farm_id == farm.id)).all()
    )
    _delete_lots_with_events(admin_session, lot_ids)
    admin_session.execute(delete(Product).where(Product.id == product.id))
    admin_session.commit()


def test_harvest_lot_and_event_roll_back_if_event_append_fails(
    admin_session: Session, identity_factory, monkeypatch
):
    owner = identity_factory()
    farm = _make_farm(admin_session, owner.organization_id)
    product = Product(name=f"sprint2-rollback-product-{uuid4().hex[:8]}", unit="kg")
    admin_session.add(product)
    admin_session.commit()
    generated_code = f"T{uuid4().hex[:7].upper()}"
    monkeypatch.setattr(lot_service, "generate_lot_code", lambda: generated_code)
    append_event = event_service.append_event
    attempted_lot_ids = []

    def append_then_fail(db, principal, lot_id, **event_data):
        attempted_lot_ids.append(lot_id)
        append_event(db, principal, lot_id, **event_data)
        raise RuntimeError("simulated event append failure")

    monkeypatch.setattr(event_service, "append_event", append_then_fail)
    payload = lot_service.LotCreate(
        farm_id=farm.id,
        product_id=product.id,
        harvested_on=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date(),
        quantity=Decimal("5.000"),
    )

    with pytest.raises(RuntimeError, match="simulated event append failure"):
        lot_service.create_harvest_lot(admin_session, _make_principal(owner), payload)

    admin_session.expire_all()
    assert (
        admin_session.scalar(select(Lot.id).where(Lot.lot_code == generated_code))
        is None
    )
    assert (
        admin_session.scalar(
            select(Event.id).where(Event.lot_id.in_(attempted_lot_ids))
        )
        is None
    )
    admin_session.execute(delete(Product).where(Product.id == product.id))
    admin_session.commit()
