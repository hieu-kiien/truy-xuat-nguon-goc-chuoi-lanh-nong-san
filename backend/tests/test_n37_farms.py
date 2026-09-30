from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, set_db_context
from app.main import app
from app.models.farm import Farm
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


def _add_farm(db: Session, organization_id: UUID, name: str) -> Farm:
    farm = Farm(
        organization_id=organization_id,
        name=name,
        area_ha=Decimal("1.2500"),
        latitude=Decimal("10.762622"),
        longitude=Decimal("106.660172"),
    )
    db.add(farm)
    db.commit()
    return farm


@pytest.mark.asyncio
async def test_farm_crud_validation_tenant_scope_and_stable_identity(
    admin_session, identity_factory, caplog
):
    owner = identity_factory()
    other = identity_factory()
    other_farm = _add_farm(admin_session, other.organization_id, "Other tenant")

    async with _client() as client:
        await _login(client, owner)

        invalid_area = await client.post(
            "/api/v1/farms/",
            json={
                "name": "Invalid area",
                "area_ha": 0,
                "latitude": 10,
                "longitude": 20,
            },
        )
        assert invalid_area.status_code == 422
        invalid_coordinates = await client.post(
            "/api/v1/farms/",
            json={
                "name": "Invalid coordinate",
                "area_ha": 1,
                "latitude": 91,
                "longitude": 20,
            },
        )
        assert invalid_coordinates.status_code == 422

        created = await client.post(
            "/api/v1/farms/",
            json={
                "name": "My plot",
                "area_ha": 2.5,
                "latitude": 10.762622,
                "longitude": 106.660172,
                "organization_id": str(other.organization_id),
            },
        )
        assert created.status_code == 201, created.text
        farm = created.json()
        farm_id = farm["id"]
        assert farm["organization_id"] == str(owner.organization_id)
        assert (await client.get(f"/api/v1/farms/{farm_id}")).status_code == 200

        updated = await client.put(
            f"/api/v1/farms/{farm_id}",
            json={
                "name": "Renamed plot",
                "area_ha": 3.5,
                "latitude": 10.8,
                "longitude": 106.7,
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["id"] == farm_id
        assert updated.json()["organization_id"] == str(owner.organization_id)

        caplog.clear()
        denied = await client.get(f"/api/v1/farms/{other_farm.id}")
        assert denied.status_code == 403
        assert any(
            getattr(record, "event", None) == "authorization.record_not_visible"
            for record in caplog.records
        )
        caplog.clear()
        denied_update = await client.put(
            f"/api/v1/farms/{other_farm.id}",
            json={
                "name": "Attempted change",
                "area_ha": 3,
                "latitude": 10,
                "longitude": 20,
            },
        )
        assert denied_update.status_code == 403
        assert any(
            getattr(record, "event", None) == "authorization.record_not_visible"
            for record in caplog.records
        )
        listing = await client.get("/api/v1/farms/")
        assert [row["id"] for row in listing.json()] == [farm_id]


def test_farm_rls_filters_rows_without_api_filter(identity_factory, admin_session):
    owner = identity_factory()
    other = identity_factory()
    own_farm = _add_farm(admin_session, owner.organization_id, "Mine")
    _add_farm(admin_session, other.organization_id, "Theirs")

    with SessionLocal() as db:
        assert list(db.scalars(select(Farm)).all()) == []
        set_db_context(db, organization_id=owner.organization_id)
        assert [row.id for row in db.scalars(select(Farm)).all()] == [own_farm.id]


@pytest.mark.parametrize(
    "invalid_values",
    [
        {"area_ha": Decimal("0")},
        {"area_ha": Decimal("NaN")},
        {"latitude": Decimal("90.000001")},
        {"longitude": Decimal("-180.000001")},
    ],
)
def test_database_constraints_reject_invalid_farm_values(
    admin_session, identity_factory, invalid_values
):
    identity = identity_factory()
    values = {
        "organization_id": identity.organization_id,
        "name": "Invalid database row",
        "area_ha": Decimal("1.0000"),
        "latitude": Decimal("10.000000"),
        "longitude": Decimal("20.000000"),
    }
    values.update(invalid_values)
    admin_session.add(Farm(**values))
    with pytest.raises(IntegrityError):
        admin_session.flush()
    admin_session.rollback()
