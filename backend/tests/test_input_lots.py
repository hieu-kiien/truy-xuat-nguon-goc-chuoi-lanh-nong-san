"""Integration test suite for N3-38: input material declarations for a lot.

A grower records which input material was used for a lot. Every declaration
becomes one event on the lot chain, inspectors see the declarations in the
file, and other organizations do not.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models.event import Event
from app.models.farm import Farm
from app.models.lot import Lot
from app.models.lot_input import LotInputLot
from app.models.product import Product
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


def _seed_lot(db: Session, identity: IdentityFixture) -> tuple[Lot, Product]:
    farm = Farm(
        organization_id=identity.organization_id,
        name=f"input-farm-{uuid4().hex[:8]}",
        area_ha=Decimal("1.0000"),
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
    )
    product = Product(name=f"input-product-{uuid4().hex[:8]}", unit="kg")
    db.add_all([farm, product])
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        name="Lô có vật tư",
        lot_code=uuid4().hex[:8].upper(),
        product_id=product.id,
        harvested_on=date.today(),
        quantity=Decimal("10.000"),
        remaining_quantity=Decimal("10.000"),
        status="active",
    )
    db.add(lot)
    db.commit()
    return lot, product


@pytest.mark.asyncio
async def test_n3_38_declaring_input_materials_writes_one_event_each(
    admin_session: Session, identity_factory
):
    """Every declaration becomes one event on the lot chain."""
    grower = identity_factory(role="grower", organization_type="farm")
    lot, product = _seed_lot(admin_session, grower)
    used_on = date.today() - timedelta(days=3)

    async with _client() as grower_client:
        await _login(grower_client, grower)
        response = await grower_client.post(
            f"/api/v1/lots/{lot.id}/input-lots",
            json={
                "items": [
                    {
                        "product_id": str(product.id),
                        "quantity": "12.500",
                        "used_on": used_on.isoformat(),
                    }
                ]
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["product_name"] == product.name
        assert payload[0]["quantity"] == "12.500"
        assert payload[0]["used_on"] == used_on.isoformat()

    events = list(
        admin_session.scalars(
            select(Event).where(
                Event.lot_id == lot.id,
                Event.event_type == "input_lot_declared",
            )
        ).all()
    )
    assert len(events) == 1
    payload = events[0].payload
    assert payload["product_name"] == product.name
    assert payload["quantity"] == 12.5
    assert payload["used_on"] == used_on.isoformat()


@pytest.mark.asyncio
async def test_n3_38_input_materials_are_visible_to_the_inspector(
    admin_session: Session, identity_factory
):
    """The inspector sees the declarations of a lot they check."""
    grower = identity_factory(role="grower", organization_type="farm")
    inspector = identity_factory(role="inspector", organization_type="inspection")
    lot, product = _seed_lot(admin_session, grower)

    async with _client() as grower_client, _client() as inspector_client:
        await _login(grower_client, grower)
        await _login(inspector_client, inspector)

        created = await grower_client.post(
            f"/api/v1/lots/{lot.id}/input-lots",
            json={
                "items": [
                    {
                        "product_id": str(product.id),
                        "quantity": "3.000",
                        "used_on": date.today().isoformat(),
                    }
                ]
            },
        )
        assert created.status_code == 201, created.text

        response = await inspector_client.get(f"/api/v1/lots/{lot.id}/input-lots")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["product_name"] == product.name


@pytest.mark.asyncio
async def test_n3_38_other_organizations_do_not_see_the_declarations(
    admin_session: Session, identity_factory
):
    """Another organization cannot read the declarations of a lot."""
    grower = identity_factory(role="grower", organization_type="farm")
    outsider = identity_factory(role="cooperative", organization_type="cooperative")
    lot, product = _seed_lot(admin_session, grower)

    async with _client() as grower_client, _client() as outsider_client:
        await _login(grower_client, grower)
        await _login(outsider_client, outsider)

        await grower_client.post(
            f"/api/v1/lots/{lot.id}/input-lots",
            json={
                "items": [
                    {
                        "product_id": str(product.id),
                        "quantity": "3.000",
                        "used_on": date.today().isoformat(),
                    }
                ]
            },
        )

        # The lot itself is out of reach, so the declarations are too.
        response = await outsider_client.get(f"/api/v1/lots/{lot.id}/input-lots")
        assert response.status_code in {403, 404}, response.text

    rows = list(
        admin_session.scalars(
            select(LotInputLot).where(LotInputLot.lot_id == lot.id)
        ).all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_n3_38_the_date_may_sit_after_the_harvest(
    admin_session: Session, identity_factory
):
    """A material can be declared for a day after the harvest date."""
    grower = identity_factory(role="grower", organization_type="farm")
    lot, product = _seed_lot(admin_session, grower)
    later = date.today() + timedelta(days=2)

    async with _client() as grower_client:
        await _login(grower_client, grower)
        response = await grower_client.post(
            f"/api/v1/lots/{lot.id}/input-lots",
            json={
                "items": [
                    {
                        "product_id": str(product.id),
                        "quantity": "1.000",
                        "used_on": later.isoformat(),
                    }
                ]
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()[0]["used_on"] == later.isoformat()


@pytest.mark.asyncio
async def test_n3_38_an_unknown_input_material_is_refused(
    admin_session: Session, identity_factory
):
    """Only materials from the managed catalogue can be declared."""
    grower = identity_factory(role="grower", organization_type="farm")
    lot, _product = _seed_lot(admin_session, grower)

    async with _client() as grower_client:
        await _login(grower_client, grower)
        response = await grower_client.post(
            f"/api/v1/lots/{lot.id}/input-lots",
            json={
                "items": [
                    {
                        "product_id": "11111111-1111-4111-8111-111111111111",
                        "quantity": "1.000",
                        "used_on": date.today().isoformat(),
                    }
                ]
            },
        )
        assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_n3_38_a_lot_of_another_organization_cannot_be_declared(
    admin_session: Session, identity_factory
):
    """Only the organization holding the lot records the declaration."""
    grower = identity_factory(role="grower", organization_type="farm")
    outsider = identity_factory(role="grower", organization_type="farm")
    lot, product = _seed_lot(admin_session, grower)

    async with _client() as outsider_client:
        await _login(outsider_client, outsider)
        response = await outsider_client.post(
            f"/api/v1/lots/{lot.id}/input-lots",
            json={
                "items": [
                    {
                        "product_id": str(product.id),
                        "quantity": "1.000",
                        "used_on": date.today().isoformat(),
                    }
                ]
            },
        )
        assert response.status_code in {403, 404}, response.text

    rows = list(
        admin_session.scalars(
            select(LotInputLot).where(LotInputLot.lot_id == lot.id)
        ).all()
    )
    assert rows == []
