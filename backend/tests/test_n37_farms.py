"""N3-7 - Farm (thửa đất) acceptance criteria.

Covers creation, ownership assignment from the authenticated principal,
validation of name/area/coordinates, database-level constraints, tenant-scoped
listing, cross-tenant 403 with a security log, and the key acceptance
criterion: renaming a farm must not detach the lots that reference it.
"""

import logging
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from tests.conftest import (
    APP_URL,
    create_farm,
    create_lot,
    create_product,
    login_as,
)

FARMS_URL = "/api/v1/farms/"
VALID_FARM = {
    "name": "Thửa đất số 1",
    "area_ha": "3.2500",
    "latitude": "10.776900",
    "longitude": "106.700900",
}


# --------------------------------------------------------------------------- #
# Creation and ownership                                                      #
# --------------------------------------------------------------------------- #


async def test_create_farm_succeeds(client: AsyncClient, tenant_factory) -> None:
    client = await login_as(client, tenant_factory())

    response = await client.post(FARMS_URL, json=VALID_FARM)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == VALID_FARM["name"]
    assert body["area_ha"] == "3.2500"
    assert body["id"]


async def test_farm_is_owned_by_the_authenticated_organization(
    client: AsyncClient, tenant_factory
) -> None:
    tenant = tenant_factory()
    client = await login_as(client, tenant)

    response = await client.post(FARMS_URL, json=VALID_FARM)

    assert response.status_code == 201
    assert response.json()["organization_id"] == str(tenant.organization_id)


@pytest.mark.parametrize("role", ["grower", "organization_admin"])
async def test_client_cannot_assign_an_arbitrary_organization_id(
    client: AsyncClient, admin_db: Session, tenant_factory, role: str
) -> None:
    """`organization_id` is not a writable field, so the body is rejected.

    Rejecting is strictly stronger than ignoring: the value never reaches the
    ORM, so there is no code path in which it could be honoured.
    """
    from uuid import UUID

    from app.models.farm import Farm

    tenant = tenant_factory(role=role, organization_type="farm")
    victim = tenant_factory()
    client = await login_as(client, tenant)

    rejected = await client.post(
        FARMS_URL, json={**VALID_FARM, "organization_id": str(victim.organization_id)}
    )
    assert rejected.status_code == 422
    assert admin_db.query(Farm).count() == 0

    # Without the field, the farm lands in the caller's own organization.
    created = await client.post(FARMS_URL, json=VALID_FARM)
    assert created.status_code == 201
    assert created.json()["organization_id"] == str(tenant.organization_id)

    admin_db.expire_all()
    farm = admin_db.get(Farm, UUID(created.json()["id"]))
    assert farm.organization_id == tenant.organization_id


async def test_unknown_fields_are_rejected(client: AsyncClient, tenant_factory) -> None:
    client = await login_as(client, tenant_factory())

    response = await client.post(FARMS_URL, json={**VALID_FARM, "unexpected": "value"})

    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Validation                                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
async def test_blank_name_is_rejected(
    client: AsyncClient, tenant_factory, name: str
) -> None:
    client = await login_as(client, tenant_factory())

    response = await client.post(FARMS_URL, json={**VALID_FARM, "name": name})

    assert response.status_code == 422
    assert "Tên thửa đất" in response.text


async def test_name_is_trimmed(client: AsyncClient, tenant_factory) -> None:
    client = await login_as(client, tenant_factory())

    response = await client.post(FARMS_URL, json={**VALID_FARM, "name": "  Thửa A  "})

    assert response.status_code == 201
    assert response.json()["name"] == "Thửa A"


@pytest.mark.parametrize("area", ["0", "0.0000", "-1", "-0.5", 0, -3.5])
async def test_non_positive_area_is_rejected(
    client: AsyncClient, tenant_factory, area
) -> None:
    client = await login_as(client, tenant_factory())

    response = await client.post(FARMS_URL, json={**VALID_FARM, "area_ha": area})

    assert response.status_code == 422
    assert "Diện tích" in response.text


async def test_area_must_be_numeric(client: AsyncClient, tenant_factory) -> None:
    client = await login_as(client, tenant_factory())

    response = await client.post(FARMS_URL, json={**VALID_FARM, "area_ha": "vùng"})

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        ("90.000001", "106.0"),
        ("-90.000001", "106.0"),
        ("91", "106.0"),
        ("-91", "106.0"),
        ("10.0", "180.000001"),
        ("10.0", "-180.000001"),
        ("10.0", "181"),
        ("10.0", "-181"),
    ],
)
async def test_out_of_range_coordinates_are_rejected(
    client: AsyncClient, tenant_factory, latitude: str, longitude: str
) -> None:
    client = await login_as(client, tenant_factory())

    response = await client.post(
        FARMS_URL, json={**VALID_FARM, "latitude": latitude, "longitude": longitude}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [("90", "180"), ("-90", "-180"), ("0", "0"), ("10.776900", "106.700900")],
)
async def test_boundary_coordinates_are_accepted(
    client: AsyncClient, tenant_factory, latitude: str, longitude: str
) -> None:
    client = await login_as(client, tenant_factory())

    response = await client.post(
        FARMS_URL, json={**VALID_FARM, "latitude": latitude, "longitude": longitude}
    )

    assert response.status_code == 201


async def test_coordinate_precision_is_preserved(
    client: AsyncClient, tenant_factory
) -> None:
    """Six decimal places is ~11 cm, which is what a map rendering needs."""
    client = await login_as(client, tenant_factory())

    response = await client.post(FARMS_URL, json=VALID_FARM)

    body = response.json()
    assert body["latitude"] == "10.776900"
    assert body["longitude"] == "106.700900"
    assert Decimal(body["latitude"]).as_tuple().exponent == -6
    assert Decimal(body["longitude"]).as_tuple().exponent == -6


# --------------------------------------------------------------------------- #
# Database-level constraints                                                  #
# --------------------------------------------------------------------------- #


@pytest.fixture
def app_role_db():
    engine = create_engine(APP_URL)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("column", "value", "constraint"),
    [
        ("area_ha", "0", "ck_farms_area_positive"),
        ("area_ha", "-5", "ck_farms_area_positive"),
        ("latitude", "90.5", "ck_farms_latitude_range"),
        ("latitude", "-90.5", "ck_farms_latitude_range"),
        ("longitude", "180.5", "ck_farms_longitude_range"),
        ("longitude", "-180.5", "ck_farms_longitude_range"),
    ],
)
def test_database_rejects_invalid_farm_rows(
    admin_db: Session,
    tenant_factory,
    column: str,
    value: str,
    constraint: str,
) -> None:
    """Pydantic is not the only line of defence; the database must also refuse."""
    tenant = tenant_factory()
    values = {
        "id": str(uuid4()),
        "organization_id": str(tenant.organization_id),
        "name": "Thửa đất rác",
        "area_ha": "1.0000",
        "latitude": "10.000000",
        "longitude": "106.000000",
    }
    values[column] = value

    columns = ", ".join(values)
    placeholders = ", ".join(f":{key}" for key in values)
    with pytest.raises(IntegrityError) as excinfo:
        admin_db.execute(
            text(f"INSERT INTO farms ({columns}) VALUES ({placeholders})"), values
        )
        admin_db.commit()

    assert constraint in str(excinfo.value)


def test_database_rejects_a_farm_with_an_unknown_organization(
    admin_db: Session,
) -> None:
    with pytest.raises(IntegrityError) as excinfo:
        admin_db.execute(
            text(
                "INSERT INTO farms (id, organization_id, name, area_ha, latitude, longitude) "
                "VALUES (:id, :org, 'Orphan', 1.0, 10.0, 106.0)"
            ),
            {"id": str(uuid4()), "org": str(uuid4())},
        )
        admin_db.commit()

    assert "organizations" in str(excinfo.value)


async def test_rls_prevents_cross_tenant_farm_insert(
    app_role_db, admin_db: Session, tenant_factory
) -> None:
    """Even the application role cannot insert a farm into another tenant."""
    owner = tenant_factory()
    attacker = tenant_factory()

    with app_role_db.connect() as connection:
        connection.execute(
            text("SELECT set_config('app.current_organization', :org, true)"),
            {"org": str(attacker.organization_id)},
        )
        with pytest.raises(Exception) as excinfo:
            connection.execute(
                text(
                    "INSERT INTO farms (id, organization_id, name, area_ha, latitude, longitude) "
                    "VALUES (:id, :org, 'Chèn chéo', 1.0, 10.0, 106.0)"
                ),
                {"id": str(uuid4()), "org": str(owner.organization_id)},
            )
            connection.commit()

    assert "row-level security" in str(excinfo.value).lower()


# --------------------------------------------------------------------------- #
# Listing and tenant scoping                                                  #
# --------------------------------------------------------------------------- #


async def test_list_farms_is_scoped_to_the_own_organization(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    mine = tenant_factory()
    other = tenant_factory()
    create_farm(admin_db, mine, name="Ruộng của tôi")
    create_farm(admin_db, other, name="Ruộng của họ")

    client = await login_as(client, mine)
    response = await client.get(FARMS_URL)

    assert response.status_code == 200
    body = response.json()
    assert [farm["name"] for farm in body] == ["Ruộng của tôi"]
    assert all(farm["organization_id"] == str(mine.organization_id) for farm in body)


async def test_list_farms_is_empty_for_a_tenant_without_farms(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    mine = tenant_factory()
    create_farm(admin_db, tenant_factory(), name="Ruộng của họ")

    client = await login_as(client, mine)

    assert (await client.get(FARMS_URL)).json() == []


async def test_farm_listing_requires_the_read_permission(
    client: AsyncClient, tenant_factory
) -> None:
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    client = await login_as(client, inspector)

    assert (await client.get(FARMS_URL)).status_code == 403


# --------------------------------------------------------------------------- #
# Cross-tenant access                                                         #
# --------------------------------------------------------------------------- #


async def test_cross_tenant_get_farm_returns_403(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    victim_farm = create_farm(admin_db, tenant_factory(), name="Ruộng của tổ chức khác")
    attacker = tenant_factory()
    client = await login_as(client, attacker)

    response = await client.get(f"{FARMS_URL}{victim_farm.id}")

    assert response.status_code == 403
    assert "tổ chức khác" in response.json()["detail"]


async def test_cross_tenant_update_farm_returns_403(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    victim_farm = create_farm(admin_db, tenant_factory(), name="Tên gốc")
    attacker = tenant_factory()
    client = await login_as(client, attacker)

    response = await client.put(
        f"{FARMS_URL}{victim_farm.id}", json={**VALID_FARM, "name": "Bị đổi tên"}
    )

    assert response.status_code == 403
    from app.models.farm import Farm

    admin_db.expire_all()
    assert admin_db.get(Farm, victim_farm.id).name == "Tên gốc"


async def test_cross_tenant_patch_farm_returns_403(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    victim_farm = create_farm(admin_db, tenant_factory(), name="Tên gốc")
    attacker = tenant_factory()
    client = await login_as(client, attacker)

    response = await client.patch(
        f"{FARMS_URL}{victim_farm.id}", json={"name": "Bị đổi tên"}
    )

    assert response.status_code == 403


async def test_cross_tenant_access_emits_a_security_log(
    caplog, client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    from app.core.logging_config import configure_logging

    configure_logging()
    victim_farm = create_farm(admin_db, tenant_factory(), name="Ruộng của tổ chức khác")
    client = await login_as(client, tenant_factory())

    with caplog.at_level(logging.WARNING, logger="app.security"):
        response = await client.get(f"{FARMS_URL}{victim_farm.id}")

    assert response.status_code == 403
    events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "authorization.cross_organization_access"
    ]
    assert events, "no cross-organization security event was logged"
    assert events[0].resource_type == "farms"
    assert events[0].resource_id == str(victim_farm.id)


# --------------------------------------------------------------------------- #
# Update / rename                                                             #
# --------------------------------------------------------------------------- #


async def test_rename_farm_keeps_its_identifier(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    farm = create_farm(admin_db, tenant, name="Tên cũ")
    client = await login_as(client, tenant)

    response = await client.patch(f"{FARMS_URL}{farm.id}", json={"name": "Tên mới"})

    assert response.status_code == 200
    assert response.json()["id"] == str(farm.id)
    assert response.json()["name"] == "Tên mới"


async def test_rename_farm_does_not_detach_its_lots(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    """Core N3-7 acceptance criterion.

    After renaming a farm, the lots that reference it must still point at the
    very same farm. Asserted by reloading the relation from the database, not
    by comparing the farm's own id.
    """
    tenant = tenant_factory()
    farm = create_farm(admin_db, tenant, name="Thửa đất gốc")
    product = create_product(admin_db, tenant)
    lot = create_lot(admin_db, tenant, farm, product, lot_number="LOT-RENAME-1")
    original_farm_id = farm.id
    original_lot_id = lot.id

    client = await login_as(client, tenant)
    rename = await client.patch(
        f"{FARMS_URL}{farm.id}", json={"name": "Thửa đất sau khi đổi tên"}
    )
    assert rename.status_code == 200

    # Re-read everything from the database with a fresh session.
    admin_db.expire_all()
    reloaded_lot = admin_db.get(type(lot), original_lot_id)
    reloaded_farm = admin_db.get(type(farm), original_farm_id)

    assert reloaded_lot is not None
    assert reloaded_farm is not None
    assert reloaded_lot.origin_farm_id == original_farm_id
    assert reloaded_farm.name == "Thửa đất sau khi đổi tên"

    # And the relation must still be readable through the API.
    lot_response = await client.get(f"/api/v1/lots/{original_lot_id}")
    assert lot_response.status_code == 200
    assert lot_response.json()["origin_farm_id"] == str(original_farm_id)


async def test_rename_farm_preserves_relations_for_multiple_lots(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    farm = create_farm(admin_db, tenant, name="Thửa đất nhiều lô")
    product = create_product(admin_db, tenant)
    lots = [
        create_lot(admin_db, tenant, farm, product, lot_number=f"LOT-MULTI-{index}")
        for index in range(3)
    ]
    lot_ids = [lot.id for lot in lots]

    client = await login_as(client, tenant)
    assert (
        await client.patch(f"{FARMS_URL}{farm.id}", json={"name": "Đổi tên toàn bộ"})
    ).status_code == 200

    admin_db.expire_all()
    for lot_id in lot_ids:
        reloaded = admin_db.get(type(lots[0]), lot_id)
        assert reloaded.origin_farm_id == farm.id


async def test_patch_only_updates_supplied_fields(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    farm = create_farm(admin_db, tenant, name="Tên cũ", area_ha=Decimal("5.0000"))
    client = await login_as(client, tenant)

    response = await client.patch(f"{FARMS_URL}{farm.id}", json={"name": "Tên mới"})

    assert response.status_code == 200
    assert response.json()["name"] == "Tên mới"
    assert response.json()["area_ha"] == "5.0000"
    assert response.json()["latitude"] == "10.776900"
    assert response.json()["organization_id"] == str(tenant.organization_id)


async def test_patch_rejects_an_empty_body(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    farm = create_farm(admin_db, tenant)
    client = await login_as(client, tenant)

    assert (await client.patch(f"{FARMS_URL}{farm.id}", json={})).status_code == 200


async def test_patch_cannot_change_the_organization(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    from app.models.farm import Farm

    tenant = tenant_factory()
    other = tenant_factory()
    farm = create_farm(admin_db, tenant)
    client = await login_as(client, tenant)

    response = await client.patch(
        f"{FARMS_URL}{farm.id}", json={"organization_id": str(other.organization_id)}
    )

    assert response.status_code == 422
    admin_db.expire_all()
    assert admin_db.get(Farm, farm.id).organization_id == tenant.organization_id


async def test_patch_cannot_change_the_farm_identifier(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    from app.models.farm import Farm

    tenant = tenant_factory()
    farm = create_farm(admin_db, tenant)
    client = await login_as(client, tenant)

    response = await client.patch(f"{FARMS_URL}{farm.id}", json={"id": str(uuid4())})

    assert response.status_code == 422
    admin_db.expire_all()
    assert admin_db.get(Farm, farm.id) is not None


@pytest.mark.parametrize("area", ["0", "-1"])
async def test_patch_rejects_non_positive_area(
    client: AsyncClient, admin_db: Session, tenant_factory, area: str
) -> None:
    farm = create_farm(admin_db, tenant_factory())
    client = await login_as(client, tenant_factory())

    response = await client.patch(f"{FARMS_URL}{farm.id}", json={"area_ha": area})

    assert response.status_code == 422


async def test_full_update_replaces_every_field(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    farm = create_farm(admin_db, tenant, name="Tên cũ")
    client = await login_as(client, tenant)

    response = await client.put(
        f"{FARMS_URL}{farm.id}",
        json={
            "name": "Tên thay thế",
            "area_ha": "9.9999",
            "latitude": "1.000000",
            "longitude": "2.000000",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(farm.id)
    assert body["name"] == "Tên thay thế"
    assert body["area_ha"] == "9.9999"
    assert body["latitude"] == "1.000000"
    assert body["longitude"] == "2.000000"


async def test_incomplete_full_update_is_rejected(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    farm = create_farm(admin_db, tenant_factory())
    client = await login_as(client, tenant_factory())

    assert (
        await client.put(f"{FARMS_URL}{farm.id}", json={"name": "Chỉ có tên"})
    ).status_code == 422


async def test_lot_creation_requires_a_farm_in_the_same_organization(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    """A lot must not be attachable to another tenant's farm."""
    owner = tenant_factory()
    attacker = tenant_factory()
    victim_farm = create_farm(admin_db, owner)
    product = create_product(admin_db, attacker)

    client = await login_as(client, attacker)
    response = await client.post(
        "/api/v1/lots/",
        json={
            "product_id": str(product.id),
            "origin_farm_id": str(victim_farm.id),
            "lot_number": "LOT-STOLEN",
            "quantity": "10.000",
            "unit": "kg",
        },
    )

    assert response.status_code == 403


def test_farm_model_and_migration_agree_on_constraints() -> None:
    """Guards against a model/DB divergence going unnoticed."""
    from app.models.farm import Farm

    names = {
        constraint.name for constraint in Farm.__table__.constraints if constraint.name
    }
    assert {
        "ck_farms_area_positive",
        "ck_farms_latitude_range",
        "ck_farms_longitude_range",
        "uq_farms_id_organization",
    } <= names


def test_session_cookie_stays_secure_outside_development() -> None:
    """The test suite relaxes Secure to speak plain HTTP; production must not."""
    assert settings.SESSION_COOKIE_SECURE is False, (
        "the suite sets SESSION_COOKIE_SECURE=false for the HTTP test transport; "
        "if this fails the isolation between test and production settings broke"
    )
