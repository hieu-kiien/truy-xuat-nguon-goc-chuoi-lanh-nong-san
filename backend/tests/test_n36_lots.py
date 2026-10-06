from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authorization import has_permission
from app.core.database import SessionLocal, set_db_context
from app.main import app
from app.models.farm import Farm
from app.models.lot import Lot
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


def _add_lot(db: Session, organization_id: UUID, farm_id: UUID, name: str) -> Lot:
    lot = Lot(organization_id=organization_id, farm_id=farm_id, name=name)
    db.add(lot)
    db.commit()
    return lot


def _spoof_tenant_and_role(db: Session, organization_id: UUID, role: str) -> None:
    db.execute(
        text(
            "SELECT set_config('app.current_organization', :organization, true), "
            "set_config('app.current_role', :role, true)"
        ),
        {"organization": str(organization_id), "role": role},
    )


def test_application_role_is_limited_and_does_not_bypass_rls():
    with SessionLocal() as db:
        role = db.execute(
            text(
                """
                SELECT r.rolsuper, r.rolbypassrls,
                    pg_catalog.pg_get_userbyid(c.relowner) = current_user AS owns_lots,
                    has_table_privilege(current_user, 'lots', 'INSERT') AS can_insert,
                    has_table_privilege(current_user, 'lots', 'UPDATE') AS can_update,
                    has_table_privilege(current_user, 'lots', 'DELETE') AS can_delete
                FROM pg_catalog.pg_roles AS r
                CROSS JOIN pg_catalog.pg_class AS c
                WHERE r.rolname = current_user AND c.oid = 'lots'::regclass
                """
            )
        ).one()

    assert role == (False, False, False, True, False, False)


@pytest.mark.asyncio
async def test_lots_are_tenant_scoped_and_inspector_is_read_only_read_all(
    admin_session, identity_factory, caplog
):
    owner = identity_factory()
    other = identity_factory()
    inspector = identity_factory(role="inspector", organization_type="inspection")
    owner_farm = _add_farm(admin_session, owner.organization_id, "Owner farm")
    other_farm = _add_farm(admin_session, other.organization_id, "Other farm")
    owner_lot = _add_lot(
        admin_session, owner.organization_id, owner_farm.id, "Owner lot"
    )
    other_lot = _add_lot(
        admin_session, other.organization_id, other_farm.id, "Other lot"
    )

    async with _client() as client:
        await _login(client, owner)
        own_list = await client.get("/api/v1/lots/")
        assert own_list.status_code == 200, own_list.text
        assert [row["id"] for row in own_list.json()] == [str(owner_lot.id)]
        own_detail = await client.get(f"/api/v1/lots/{owner_lot.id}")
        assert own_detail.status_code == 200
        assert own_detail.json()["farm_id"] == str(owner_farm.id)

        caplog.clear()
        denied = await client.get(f"/api/v1/lots/{other_lot.id}")
        assert denied.status_code == 403
        assert any(
            getattr(record, "event", None) == "authorization.record_not_visible"
            for record in caplog.records
        )

        renamed = await client.put(
            f"/api/v1/farms/{owner_farm.id}",
            json={
                "name": "Renamed owner farm",
                "area_ha": 1.25,
                "latitude": 10.762622,
                "longitude": 106.660172,
            },
        )
        assert renamed.status_code == 200, renamed.text
        reloaded_lot = await client.get(f"/api/v1/lots/{owner_lot.id}")
        assert reloaded_lot.status_code == 200
        assert reloaded_lot.json()["farm_id"] == str(owner_farm.id)

    with SessionLocal() as db:
        set_db_context(db, session_token_hash=owner.session_token_hash)
        lot_from_database = db.get(Lot, owner_lot.id)
        assert lot_from_database is not None
        assert lot_from_database.farm_id == owner_farm.id

    assert has_permission("inspector", "lots:read")
    assert not has_permission("inspector", "lots:write")
    async with _client() as client:
        await _login(client, inspector)
        inspector_list = await client.get("/api/v1/lots/")
        assert inspector_list.status_code == 200, inspector_list.text
        assert {row["id"] for row in inspector_list.json()} == {
            str(owner_lot.id),
            str(other_lot.id),
        }
        inspector_detail = await client.get(f"/api/v1/lots/{other_lot.id}")
        assert inspector_detail.status_code == 200
        assert inspector_detail.json()["organization_id"] == str(other.organization_id)
        no_write_route = await client.post("/api/v1/lots/", json={})
        assert no_write_route.status_code == 403


@pytest.mark.asyncio
async def test_lot_offset_keeps_lookahead_row_on_the_next_page(
    admin_session, identity_factory
):
    owner = identity_factory()
    farm = _add_farm(admin_session, owner.organization_id, "Pagination farm")
    lots = [
        Lot(
            organization_id=owner.organization_id,
            farm_id=farm.id,
            name=f"Pagination lot {index}",
        )
        for index in range(21)
    ]
    admin_session.add_all(lots)
    admin_session.commit()

    async with _client() as client:
        await _login(client, owner)
        first_page = await client.get(
            "/api/v1/lots/?offset=0&page_size=21"
        )
        second_page = await client.get(
            "/api/v1/lots/?offset=20&page_size=21"
        )

    assert first_page.status_code == 200, first_page.text
    assert second_page.status_code == 200, second_page.text
    first_page_ids = [lot["id"] for lot in first_page.json()]
    second_page_ids = [lot["id"] for lot in second_page.json()]
    assert len(first_page_ids) == 21
    assert len(second_page_ids) == 1
    assert first_page_ids[20] == second_page_ids[0]


def test_lot_rls_uses_authenticated_session_not_spoofable_tenant_or_role_gucs(
    identity_factory, admin_session
):
    owner = identity_factory()
    other = identity_factory()
    inspector = identity_factory(role="inspector", organization_type="inspection")
    owner_farm = _add_farm(admin_session, owner.organization_id, "Owner farm")
    other_farm = _add_farm(admin_session, other.organization_id, "Other farm")
    owner_lot = _add_lot(admin_session, owner.organization_id, owner_farm.id, "Owner")
    other_lot = _add_lot(admin_session, other.organization_id, other_farm.id, "Other")

    with SessionLocal() as db:
        set_db_context(
            db,
            session_token_hash=owner.session_token_hash,
        )
        _spoof_tenant_and_role(db, other.organization_id, "inspector")
        visible = list(db.scalars(select(Lot)).all())
        assert [lot.id for lot in visible] == [owner_lot.id]

    with SessionLocal() as db:
        set_db_context(
            db,
            session_token_hash=inspector.session_token_hash,
        )
        _spoof_tenant_and_role(db, owner.organization_id, "grower")
        visible = list(db.scalars(select(Lot)).all())
        assert {lot.id for lot in visible} == {owner_lot.id, other_lot.id}

    with SessionLocal() as db:
        _spoof_tenant_and_role(db, other.organization_id, "inspector")
        assert list(db.scalars(select(Lot)).all()) == []


def test_lot_farm_relation_is_tenant_consistent(identity_factory, admin_session):
    owner = identity_factory()
    other = identity_factory()
    farm = _add_farm(admin_session, other.organization_id, "Other farm")
    invalid_lot = Lot(
        organization_id=owner.organization_id,
        farm_id=farm.id,
        name="Cross-organization relation",
    )
    admin_session.add(invalid_lot)

    with pytest.raises(IntegrityError):
        admin_session.flush()
    admin_session.rollback()


def test_transaction_local_tenant_context_does_not_leak_between_sessions(
    identity_factory, admin_session
):
    owner = identity_factory()
    farm = _add_farm(admin_session, owner.organization_id, "Tenant farm")
    lot = _add_lot(admin_session, owner.organization_id, farm.id, "Tenant lot")

    with SessionLocal() as authenticated_db:
        set_db_context(authenticated_db, session_token_hash=owner.session_token_hash)
        assert authenticated_db.get(Lot, lot.id) is not None
        authenticated_db.commit()

    with SessionLocal() as fresh_db:
        assert list(fresh_db.scalars(select(Lot)).all()) == []
