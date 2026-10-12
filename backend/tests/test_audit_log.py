import asyncio
import base64
import json
from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, event, select, text
from sqlalchemy.exc import DBAPIError

from app.core.database import SessionLocal, engine, set_db_context
from app.main import app
from app.models.audit_log import AuditLog
from app.models.integrity_check import IntegrityCheck
from app.models.lot import Lot
from tests.lineage_helpers import add_lot, login, split_body
from tests.test_sprint3_lineage import lineage_products  # noqa: F401


def audit_client():
    return AsyncClient(
        transport=ASGITransport(
            app=app, client=("198.51.100.44", 1234), raise_app_exceptions=False
        ),
        base_url="https://testserver",
    )


@pytest.fixture(autouse=True)
def cleanup_audit(admin_session):
    yield
    admin_session.rollback()
    admin_session.execute(text("ALTER TABLE audit_logs DISABLE TRIGGER USER"))
    admin_session.execute(delete(AuditLog).where(AuditLog.client_ip == "198.51.100.44"))
    admin_session.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER USER"))
    admin_session.commit()


@pytest.mark.asyncio
async def test_login_harvest_split_audit_metadata_no_secret(request, admin_session):
    products = request.getfixturevalue("lineage_products")
    factory = request.getfixturevalue("identity_factory")
    owner = factory(role="organization_admin", organization_type="cooperative")
    reference = add_lot(admin_session, owner, products[0])
    async with audit_client() as api:
        await login(api, owner)
        created = await api.post(
            "/api/v1/lots/",
            json={
                "farm_id": str(reference.farm_id),
                "product_id": str(products[0].id),
                "harvested_on": date.today().isoformat(),
                "quantity": "10",
            },
        )
        assert created.status_code == 201, created.text
        lot_id = UUID(created.json()["id"])
        split = await api.post(
            f"/api/v1/lots/{lot_id}/split", json=split_body("2", "3")
        )
        assert split.status_code == 201, split.text
    rows = list(
        admin_session.scalars(
            select(AuditLog)
            .where(AuditLog.actor_user_id == owner.user_id)
            .order_by(AuditLog.recorded_at)
        )
    )
    assert [r.action for r in rows] == ["auth.login", "lots.create", "lots.split"]
    assert [r.object_id for r in rows] == [owner.user_id, lot_id, lot_id]
    assert all(
        r.organization_id == owner.organization_id
        and r.client_ip == "198.51.100.44"
        and r.outcome == "success"
        and r.actor_authenticated
        for r in rows
    )
    assert all(owner.password not in str(r.__dict__) for r in rows)


@pytest.mark.asyncio
async def test_failed_login_reason_attempted_identity_and_unknown(
    identity_factory, admin_session
):
    owner = identity_factory()
    secret = f"Must-never-store-{uuid4()}"
    async with audit_client() as api:
        for email in [owner.email, f"{uuid4()}@example.com"]:
            response = await api.post(
                "/api/v1/auth/login",
                json={"email": email, "password": secret},
                headers={"X-Forwarded-For": "203.0.113.200"},
            )
            assert response.status_code == 401
    rows = list(
        admin_session.scalars(
            select(AuditLog).where(AuditLog.client_ip == "198.51.100.44")
        )
    )
    assert len(rows) == 2
    assert {r.actor_user_id for r in rows} == {owner.user_id, None}
    known = next(r for r in rows if r.actor_user_id == owner.user_id)
    assert known.actor_name and known.organization_name
    assert all(
        r.reason == "credentials_rejected"
        and r.outcome == "denied"
        and not r.actor_authenticated
        and secret not in str(r.__dict__)
        for r in rows
    )


@pytest.mark.asyncio
async def test_audit_admin_list_cursor_rbac_and_database_immutable(
    identity_factory, admin_session
):
    owner = identity_factory()
    admin = identity_factory(role="system_admin", organization_type="administration")
    async with audit_client() as api:
        await login(api, owner)
        assert (await api.get("/api/v1/audit/")).status_code == 403
        await login(api, admin)
        response = await api.get("/api/v1/audit/?limit=1")
        assert response.status_code == 200, response.text
        first = response.json()
        assert len(first["items"]) == 1 and first["next_cursor"]
        second = await api.get(
            "/api/v1/audit/", params={"limit": 1, "cursor": first["next_cursor"]}
        )
        assert second.status_code == 200
        assert first["items"][0]["id"] != second.json()["items"][0]["id"]
        assert (await api.get("/api/v1/audit/?cursor=invalid")).status_code == 422
    row = admin_session.scalar(
        select(AuditLog).where(AuditLog.actor_user_id == owner.user_id)
    )
    for operation in [
        "UPDATE audit_logs SET action='tampered' WHERE id=:id",
        "DELETE FROM audit_logs WHERE id=:id",
    ]:
        with pytest.raises(DBAPIError), admin_session.begin_nested():
            admin_session.execute(text(operation), {"id": row.id})
    with SessionLocal() as db:
        set_db_context(db, session_token_hash=owner.session_token_hash)
        assert not list(db.scalars(select(AuditLog)))


@pytest.mark.asyncio
async def test_audit_insert_failure_rolls_back_business_commit(request, admin_session):
    products = request.getfixturevalue("lineage_products")
    owner = request.getfixturevalue("identity_factory")(
        role="organization_admin", organization_type="cooperative"
    )
    reference = add_lot(admin_session, owner, products[0])
    async with audit_client() as api:
        await login(api, owner)
        before = set(
            admin_session.scalars(
                select(Lot.id).where(Lot.organization_id == owner.organization_id)
            )
        )

        def fail_audit(connection, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO audit_logs"):
                raise RuntimeError("simulated audit storage failure")

        event.listen(engine, "before_cursor_execute", fail_audit)
        try:
            response = await api.post(
                "/api/v1/lots/",
                json={
                    "farm_id": str(reference.farm_id),
                    "product_id": str(products[0].id),
                    "harvested_on": date.today().isoformat(),
                    "quantity": "10",
                },
            )
            assert response.status_code == 500
        finally:
            event.remove(engine, "before_cursor_execute", fail_audit)
        assert (
            set(
                admin_session.scalars(
                    select(Lot.id).where(Lot.organization_id == owner.organization_id)
                )
            )
            == before
        )


@pytest.mark.asyncio
async def test_concurrent_denied_requests_keep_actor_and_object_isolated(
    identity_factory, admin_session
):
    owners = [identity_factory(), identity_factory()]
    identifiers = [uuid4(), uuid4()]

    async def attempt(owner, identifier):
        async with audit_client() as api:
            await login(api, owner)
            response = await api.post(f"/api/v1/lots/{identifier}/consume", json={})
            assert response.status_code == 403
            return response.headers["x-request-id"]

    request_ids = await asyncio.gather(
        *(
            attempt(owner, identifier)
            for owner, identifier in zip(owners, identifiers, strict=True)
        )
    )
    assert len(set(request_ids)) == 2
    for owner, identifier, request_id in zip(
        owners, identifiers, request_ids, strict=True
    ):
        row = admin_session.get(AuditLog, UUID(request_id))
        assert row.actor_user_id == owner.user_id
        assert row.organization_id == owner.organization_id
        assert row.object_id == identifier
        assert row.reason == "permission_denied"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        [None, None],
        [1, 2],
        ["no-date", "no-uuid"],
        ["2026-01-01T00:00:00+00:00", 2],
        ["2026-01-01T00:00:00+00:00", {}],
        ["2026-01-01T00:00:00+00:00", []],
        ["2026-01-01T00:00:00", str(uuid4())],
    ],
)
async def test_malformed_cursor_never_causes_server_error(identity_factory, value):
    admin = identity_factory(role="system_admin", organization_type="administration")
    cursor = base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
    async with audit_client() as api:
        await login(api, admin)
        assert (
            await api.get("/api/v1/audit/", params={"cursor": cursor})
        ).status_code == 422


def test_runtime_cannot_insert_audit_for_another_actor(identity_factory):
    owner, other = identity_factory(), identity_factory()
    with SessionLocal() as db:
        set_db_context(db, session_token_hash=owner.session_token_hash)
        db.add(
            AuditLog(
                actor_user_id=other.user_id,
                organization_id=other.organization_id,
                actor_authenticated=True,
                action="lots.create",
                object_type="lot",
                outcome="success",
                status_code=201,
            )
        )
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


@pytest.mark.asyncio
async def test_logout_audit_and_revocation_commit_together(
    identity_factory, admin_session
):
    owner = identity_factory()
    async with audit_client() as api:
        await login(api, owner)
        response = await api.post("/api/v1/auth/logout")
        assert response.status_code == 204
        row = admin_session.get(AuditLog, UUID(response.headers["x-request-id"]))
        assert row.action == "auth.logout" and row.actor_user_id == owner.user_id
        assert row.status_code == 204 and row.actor_authenticated
        assert (await api.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_integrity_check_audit_identifies_the_lot(request, admin_session):
    products = request.getfixturevalue("lineage_products")
    owner = request.getfixturevalue("identity_factory")(
        role="inspector", organization_type="administration"
    )
    lot = add_lot(admin_session, owner, products[0])
    async with audit_client() as api:
        await login(api, owner)
        response = await api.post(f"/api/v1/events/lots/{lot.id}/integrity-checks")
        assert response.status_code == 201, response.text
        row = admin_session.get(AuditLog, UUID(response.headers["x-request-id"]))
        assert (row.action, row.object_type, row.object_id) == (
            "lots.integrity_check",
            "lot",
            lot.id,
        )
    admin_session.execute(text("ALTER TABLE integrity_checks DISABLE TRIGGER USER"))
    admin_session.execute(delete(IntegrityCheck).where(IntegrityCheck.lot_id == lot.id))
    admin_session.execute(text("ALTER TABLE integrity_checks ENABLE TRIGGER USER"))
    admin_session.commit()


def test_rolled_back_object_id_is_not_reused(identity_factory, admin_session):
    from app.core.audit import _context, current_audit
    from app.models.product import Product

    owner = identity_factory(role="system_admin", organization_type="administration")
    context = _context(
        {
            "path": "/api/v1/products/",
            "method": "POST",
            "client": ("198.51.100.44", 1234),
            "state": {
                "audit_actor": {
                    "user_id": owner.user_id,
                    "organization_id": owner.organization_id,
                }
            },
        }
    )
    marker = current_audit.set(context)
    kept_id = None
    try:
        with SessionLocal() as db:
            set_db_context(db, session_token_hash=owner.session_token_hash)
            first = Product(name="Rolled back " + uuid4().hex, unit="kg")
            db.add(first)
            db.flush()
            assert context.created_id == first.id
            first_id = first.id
            db.rollback()
            assert context.created_id is None
            second = Product(name="Kept " + uuid4().hex, unit="kg")
            db.add(second)
            db.commit()
            kept_id = second.id
        row = admin_session.get(AuditLog, context.id)
        assert row.object_id == kept_id and row.object_id != first_id
    finally:
        current_audit.reset(marker)
        if kept_id:
            admin_session.execute(delete(Product).where(Product.id == kept_id))
            admin_session.commit()
