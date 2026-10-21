"""Integration test suite for N3-70: the public route map of a lot.

The public page shows the growing area and the main stops of the journey in
order. The coordinates are rounded to the district level, so the exact plot
never leaves the system.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.farm import Farm
from app.models.lot import Lot
from app.models.product import Product
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


def _seed_lot(
    db: Session,
    identity: IdentityFixture,
    *,
    latitude: str,
    longitude: str,
) -> Lot:
    farm = Farm(
        organization_id=identity.organization_id,
        name=f"route-farm-{uuid4().hex[:8]}",
        area_ha=Decimal("1.0000"),
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
    )
    product = Product(name=f"route-product-{uuid4().hex[:8]}", unit="kg")
    db.add_all([farm, product])
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        name="Lô có hành trình",
        lot_code=uuid4().hex[:8].upper(),
        product_id=product.id,
        harvested_on=date.today(),
        quantity=Decimal("10.000"),
        remaining_quantity=Decimal("10.000"),
        status="active",
    )
    db.add(lot)
    db.commit()
    return lot


@pytest.mark.asyncio
async def test_n3_70_public_route_shows_the_origin(
    admin_session: Session, identity_factory
):
    """The public route starts at the growing area of the lot."""
    grower = identity_factory(role="grower", organization_type="farm")
    lot = _seed_lot(admin_session, grower, latitude="10.776900", longitude="106.700400")

    async with _client() as client:
        response = await client.get(f"/api/v1/public/trace/{lot.lot_code}/route")
        assert response.status_code == 200, response.text
        payload = response.json()

    assert len(payload["points"]) == 1
    point = payload["points"][0]
    assert point["kind"] == "origin"
    assert point["latitude"] == 10.78
    assert point["longitude"] == 106.7
    assert (
        "thửa" in payload["precision_note"].lower()
        or "toạ độ" in payload["precision_note"]
    )


@pytest.mark.asyncio
async def test_n3_70_public_route_never_shows_the_exact_plot(
    admin_session: Session, identity_factory
):
    """The published coordinates are rounded, not the exact plot."""
    grower = identity_factory(role="grower", organization_type="farm")
    lot = _seed_lot(admin_session, grower, latitude="10.776923", longitude="106.700456")

    async with _client() as client:
        response = await client.get(f"/api/v1/public/trace/{lot.lot_code}/route")
        assert response.status_code == 200, response.text
        point = response.json()["points"][0]

    assert point["latitude"] != 10.776923
    assert point["longitude"] != 106.700456
    assert point["latitude"] == 10.78
    assert point["longitude"] == 106.7


@pytest.mark.asyncio
async def test_n3_70_unknown_lot_code_is_refused(
    admin_session: Session, identity_factory
):
    """An unknown lot code has no route."""
    async with _client() as client:
        response = await client.get("/api/v1/public/trace/ZZZZZZZZ/route")
        assert response.status_code == 404, response.text
