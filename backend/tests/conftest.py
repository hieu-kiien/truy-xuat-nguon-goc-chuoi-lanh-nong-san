from collections.abc import Callable, Iterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.farm import Farm
from app.models.identity import AuthSession, Organization, Role, User


@dataclass(frozen=True)
class IdentityFixture:
    organization_id: UUID
    user_id: UUID
    email: str
    password: str


@pytest.fixture(scope="session")
def admin_engine():
    engine = create_engine(settings.MIGRATION_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def admin_session(admin_engine) -> Iterator[Session]:
    with Session(admin_engine) as session:
        yield session


@pytest.fixture
def identity_factory(
    admin_session: Session,
) -> Iterator[Callable[..., IdentityFixture]]:
    created_organizations: list[UUID] = []
    created_users: list[UUID] = []

    def create_identity(
        *, role: str = "grower", organization_type: str = "farm"
    ) -> IdentityFixture:
        suffix = uuid4().hex
        if admin_session.get(Role, role) is None:
            raise AssertionError(f"Role was not seeded by migration: {role}")

        organization = Organization(
            name=f"integration-{suffix}",
            organization_type=organization_type,
            is_active=True,
        )
        admin_session.add(organization)
        admin_session.flush()

        password = "Correct horse battery staple 2026!"
        user = User(
            organization_id=organization.id,
            role_code=role,
            email=f"{suffix}@example.com",
            full_name="Integration test user",
            password_hash=hash_password(password),
            failed_login_attempts=0,
            locked_until=None,
            is_active=True,
        )
        admin_session.add(user)
        admin_session.commit()

        created_organizations.append(organization.id)
        created_users.append(user.id)
        return IdentityFixture(
            organization_id=organization.id,
            user_id=user.id,
            email=user.email,
            password=password,
        )

    yield create_identity

    if created_users:
        admin_session.execute(
            delete(AuthSession).where(AuthSession.user_id.in_(created_users))
        )
        admin_session.execute(delete(User).where(User.id.in_(created_users)))
    if created_organizations:
        admin_session.execute(
            delete(Farm).where(Farm.organization_id.in_(created_organizations))
        )
        admin_session.execute(
            delete(Organization).where(Organization.id.in_(created_organizations))
        )
    admin_session.commit()
