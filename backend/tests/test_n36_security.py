import logging
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text

from app.core.auth import Principal
from app.core.authorization import has_permission
from app.core.database import SessionLocal, set_db_context
from app.core.tenancy import get_tenant_record, tenant_select
from app.models.identity import User
from app.models.lot import Lot
from tests.conftest import IdentityFixture


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


def test_rls_scopes_organization_users_and_login_lookup(identity_factory):
    owner = identity_factory()
    other = identity_factory()

    with SessionLocal() as db:
        assert list(db.scalars(select(User)).all()) == []
        set_db_context(
            db,
            session_token_hash=owner.session_token_hash,
        )
        db.execute(
            text(
                "SELECT set_config('app.current_organization', :organization, true), "
                "set_config('app.current_role', 'inspector', true)"
            ),
            {"organization": str(other.organization_id)},
        )
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
            session_token_hash=owner.session_token_hash,
        )
        db.execute(
            text(
                "SELECT set_config('app.current_organization', :organization, true), "
                "set_config('app.current_role', 'inspector', true)"
            ),
            {"organization": str(other.organization_id)},
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
    assert tenant_select(Lot, inspector).whereclause is None
    assert tenant_select(User, inspector).whereclause is not None
    assert has_permission("inspector", "lots:read")
    assert not has_permission("inspector", "lots:write")


def test_tenant_query_without_context_fails_closed():
    with pytest.raises(ValueError, match="Tenant context is required"):
        tenant_select(Lot)
