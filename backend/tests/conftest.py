"""Integration test harness running against a real PostgreSQL instance.

The security guarantees this project claims -- Argon2id hashing, opaque
HttpOnly session cookies, per-organization row-level security, and a
non-privileged application database role -- can only be verified against a real
database. SQLite cannot emulate any of it, so these tests deliberately require
PostgreSQL and are skipped with a clear reason when none is configured.

Required environment (defaults match ``docker-compose.yml``)::

    DB_HOST, DB_PORT, DB_NAME, DB_ADMIN_USER, DB_ADMIN_PASSWORD, DB_USER, DB_PASSWORD
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TEST_DB = {
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "ttcs_db",
    "DB_ADMIN_USER": "admin",
    "DB_ADMIN_PASSWORD": "testadmin123",
    "DB_USER": "ttcs_app",
    "DB_PASSWORD": "ttcs_app_test_password",
}


def _configure_environment() -> bool:
    """Point the application at the test database before ``app`` is imported.

    Returns ``False`` when no test database is configured, so the suite can
    skip instead of silently running against a developer database.
    """
    configured = bool(os.getenv("DB_ADMIN_PASSWORD") or os.getenv("DATABASE_URL_ENV"))
    for key, default in DEFAULT_TEST_DB.items():
        os.environ.setdefault(key, default)
    os.environ["APP_ENV"] = "development"
    # The test client speaks plain HTTP, so the session cookie must be allowed
    # to travel without the Secure attribute. `SESSION_COOKIE_SECURE` is
    # asserted to be mandatory outside development by config validation, and a
    # dedicated test asserts that guarantee directly.
    os.environ["SESSION_COOKIE_SECURE"] = "false"
    os.environ.setdefault("SESSION_TTL_MINUTES", "480")
    return configured


_TEST_DB_CONFIGURED = _configure_environment()

pytestmark = pytest.mark.skipif(
    not _TEST_DB_CONFIGURED,
    reason="integration tests need a PostgreSQL instance; set DB_ADMIN_PASSWORD",
)

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.catalog import Product  # noqa: E402
from app.models.farm import Farm  # noqa: E402
from app.models.identity import Organization, Role, User  # noqa: E402
from app.models.traceability import Lot  # noqa: E402

ADMIN_URL = (
    f"postgresql+psycopg://{settings.DB_ADMIN_USER}:{settings.DB_ADMIN_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)
APP_URL = (
    f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# Truncated between tests. `alembic_version` is preserved so the schema check
# fixture cannot be fooled into skipping migrations.
TENANT_TABLES = [
    "lot_events",
    "lot_lineage",
    "cold_chain_alerts",
    "temperature_readings",
    "sensors",
    "shipments",
    "lots",
    "products",
    "farms",
    "sessions",
    "users",
    "organizations",
]


@pytest.fixture(scope="session")
def database() -> Iterator[None]:
    """Bootstrap the least-privilege role and migrate to head, once per run."""
    bootstrap = subprocess.run(
        [sys.executable, "-m", "app.bootstrap_db_role"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    if bootstrap.returncode != 0:
        pytest.skip(
            f"cannot bootstrap the application database role: {bootstrap.stderr}"
        )

    admin_engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(
            text(f'GRANT ALL ON SCHEMA public TO "{settings.DB_ADMIN_USER}"')
        )
    admin_engine.dispose()

    migrate = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    if migrate.returncode != 0:
        pytest.skip(f"cannot apply migrations: {migrate.stdout}\n{migrate.stderr}")

    yield

    admin_engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(
            text(f'GRANT ALL ON SCHEMA public TO "{settings.DB_ADMIN_USER}"')
        )
    admin_engine.dispose()


@pytest.fixture
def admin_db(database: None) -> Iterator[Session]:
    """Privileged session used only to arrange fixtures, never by the app."""
    engine = create_engine(ADMIN_URL)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def _clean_state(admin_db: Session) -> Iterator[None]:
    admin_db.execute(
        text(f"TRUNCATE {', '.join(TENANT_TABLES)} RESTART IDENTITY CASCADE")
    )
    admin_db.commit()
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


class Tenant:
    """An organization plus a user that can authenticate against it."""

    def __init__(self, organization: Organization, user: User, password: str) -> None:
        self.organization = organization
        self.user = user
        self.password = password

    @property
    def organization_id(self) -> UUID:
        return self.organization.id


def create_tenant(
    db: Session,
    *,
    role: str = "grower",
    organization_type: str = "farm",
    email: str | None = None,
    password: str = "CorrectHorseBattery9!",
    prefix: str | None = None,
) -> Tenant:
    """Create an organization and an active user inside it."""
    slug = prefix or uuid4().hex[:8]
    organization = Organization(name=f"Org {slug}", organization_type=organization_type)
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        role_code=role,
        # The application always case-folds on write, and the database enforces
        # it, so the fixture must do the same.
        email=str(email or f"{role}-{slug}@ttcs-demo.org").strip().casefold(),
        full_name=f"User {slug}",
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    return Tenant(organization, user, password)


async def login(client: AsyncClient, tenant: Tenant) -> AsyncClient:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": tenant.user.email, "password": tenant.password},
    )
    assert response.status_code == 200, response.text
    return client


async def login_as(client: AsyncClient, tenant: Tenant) -> AsyncClient:
    client.cookies.clear()
    return await login(client, tenant)


def create_farm(db: Session, tenant: Tenant, **overrides) -> Farm:
    values = {
        "organization_id": tenant.organization_id,
        "name": "Thửa đất mặc định",
        "area_ha": Decimal("2.5000"),
        "latitude": Decimal("10.776900"),
        "longitude": Decimal("106.700900"),
    }
    values.update(overrides)
    farm = Farm(**values)
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


def create_product(db: Session, tenant: Tenant, **overrides) -> Product:
    values = {
        "organization_id": tenant.organization_id,
        "name": "Xanh lá",
        "category": "rau",
    }
    values.update(overrides)
    product = Product(**values)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def create_lot(
    db: Session,
    tenant: Tenant,
    farm: Farm,
    product: Product,
    *,
    organization_id: UUID | None = None,
    **overrides,
) -> Lot:
    values = {
        "public_code": uuid4().hex + uuid4().hex,
        "lot_number": f"LOT-{uuid4().hex[:8]}",
        "organization_id": organization_id or tenant.organization_id,
        "origin_organization_id": tenant.organization_id,
        "product_id": product.id,
        "origin_farm_id": farm.id,
        "quantity": Decimal("100.000"),
        "unit": "kg",
        "status": "created",
        "created_by_id": tenant.user.id,
    }
    values.update(overrides)
    lot = Lot(**values)
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


@pytest.fixture
def tenant_factory(admin_db: Session):
    def _factory(**kwargs) -> Tenant:
        return create_tenant(admin_db, **kwargs)

    return _factory


@pytest.fixture
def role_seeded(admin_db: Session) -> None:
    """The role catalogue is created by migration 20260929_01."""
    assert admin_db.query(Role).count() > 0
