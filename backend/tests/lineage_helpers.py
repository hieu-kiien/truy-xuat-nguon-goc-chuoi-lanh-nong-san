"""Real-database fixtures shared by lineage API regression tests."""

from decimal import Decimal
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.farm import Farm
from app.models.lot import Lot


def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def login(api, identity):
    response = await api.post(
        "/api/v1/auth/login",
        json={
            "email": identity.email,
            "password": identity.password,
        },
    )
    assert response.status_code == 200, response.text


def add_lot(db, identity, product, quantity="40.000", status="active"):
    farm = Farm(
        organization_id=identity.organization_id,
        name=f"lineage-{uuid4().hex}",
        area_ha=Decimal("1"),
        latitude=Decimal("10"),
        longitude=Decimal("106"),
    )
    db.add(farm)
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        product_id=product.id,
        name="Lineage parent",
        lot_code=uuid4().hex[:10].upper(),
        quantity=Decimal(quantity),
        remaining_quantity=Decimal(quantity),
        status=status,
    )
    db.add(lot)
    db.commit()
    return lot


def split_body(*quantities):
    return {
        "children": [
            {"name": f"Child {index}", "quantity": value}
            for index, value in enumerate(quantities)
        ]
    }


def merge_body(*parents):
    return {
        "name": "Merged harvest",
        "parents": [
            {"lot_id": str(lot.id), "quantity": quantity} for lot, quantity in parents
        ],
    }
