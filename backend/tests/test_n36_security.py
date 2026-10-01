import logging
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.auth import Principal
from app.core.authorization import has_permission
from app.core.config import settings
from app.core.database import SessionLocal, set_db_context
from app.core.tenancy import get_tenant_record, tenant_select
from app.main import app
from app.models.identity import User
from tests.conftest import IdentityFixture


class ProbeBase(DeclarativeBase):
    pass


class LotPermissionProbe(ProbeBase):
    __tablename__ = "lots"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )


def _principal(identity: IdentityFixture) -> Principal:
    return Principal(
        user_id=identity.user_id,
        email=identity.email,
        full_name="Integration test user",
        organization_id=identity.organization_id,
        organization_name="Test organization",
        organization_type="farm",
        role="grower",
    )


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


@pytest.mark.asyncio
async def test_route_without_permission_is_denied_and_logged(identity_factory, caplog):
    identity = identity_factory()
    async with _client() as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": identity.email, "password": identity.password},
        )
        assert login.status_code == 200

        caplog.clear()
        response = await client.get("/api/v1/items/")
        assert response.status_code == 403
        assert any(
            getattr(record, "event", None) == "authorization.route_missing_permission"
            for record in caplog.records
        )


def test_application_role_is_least_privilege_and_rls_is_enabled(admin_session):
    role = admin_session.execute(
        text(
            "SELECT rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
            "FROM pg_catalog.pg_roles WHERE rolname = :role"
        ),
        {"role": settings.DB_USER},
    ).one()
    assert tuple(role) == (False, False, False, False, False)

    rows = admin_session.execute(
        text(
            "SELECT relname, relrowsecurity FROM pg_catalog.pg_class "
            "WHERE relname IN ('organizations', 'users', 'sessions', 'farms')"
        )
    ).all()
    rls_by_table = {name: enabled for name, enabled in rows}
    assert rls_by_table == {
        "organizations": True,
        "users": True,
        "sessions": True,
        "farms": True,
    }


def test_rls_scopes_organization_users_and_login_lookup(identity_factory):
    owner = identity_factory()
    other = identity_factory()

    with SessionLocal() as db:
        assert list(db.scalars(select(User)).all()) == []
        set_db_context(db, organization_id=owner.organization_id)
        scoped_users = list(db.scalars(select(User)).all())
        assert [user.id for user in scoped_users] == [owner.user_id]

    with SessionLocal() as db:
        set_db_context(db, login_email=other.email)
        login_match = list(
            db.scalars(select(User).where(User.email == other.email)).all()
        )
        assert [user.id for user in login_match] == [other.user_id]


def test_cross_tenant_id_is_denied_and_logged(identity_factory, caplog):
    owner = identity_factory()
    other = identity_factory()

    with SessionLocal() as db:
        set_db_context(
            db,
            organization_id=owner.organization_id,
            user_id=owner.user_id,
            role="grower",
        )
        with caplog.at_level(logging.WARNING):
            with pytest.raises(HTTPException) as raised:
                get_tenant_record(db, User, other.user_id, _principal(owner))
    assert raised.value.status_code == 403
    assert any(
        getattr(record, "event", None) == "authorization.record_not_visible"
        for record in caplog.records
    )


def test_inspector_permission_is_read_all_and_read_only():
    inspector = Principal(
        user_id=uuid4(),
        email="inspector@example.com",
        full_name="Inspector",
        organization_id=uuid4(),
        organization_name="Inspection office",
        organization_type="inspection",
        role="inspector",
    )
    assert tenant_select(LotPermissionProbe, inspector).whereclause is None
    assert tenant_select(User, inspector).whereclause is not None
    assert has_permission("inspector", "lots:read")
    assert not has_permission("inspector", "lots:write")
