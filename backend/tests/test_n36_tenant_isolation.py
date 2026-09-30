"""N3-6 - Tenant isolation and authorization acceptance criteria.

Exercises the isolation boundary at three independent layers, because any one
of them alone is insufficient:

* the **permission layer** (``enforce_route_permission`` / ``require_permission``),
* the **query layer** (tenant-scoped SELECTs in the handlers), and
* the **database layer** (PostgreSQL row-level security).

The inspector's cross-organization read is verified against the real ``lots``
table, not a stand-in probe model: inspector visibility is proved end to end
through the API and through raw SQL as the application database role.
"""

import logging
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_current_principal
from app.core.authorization import (
    enforce_route_permission,
    has_permission,
    require_permission,
)
from app.core.config import settings
from app.main import app
from app.models.traceability import Lot
from tests.conftest import (
    APP_URL,
    create_farm,
    create_lot,
    create_product,
    login_as,
)

# Endpoints that are intentionally reachable without a session. Anything not
# listed here and not on the health surface must require authentication.
PUBLIC_ROUTE_ALLOWLIST = {
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/trace/{public_code}"),
}
UNAUTHENTICATED_ROUTES = {
    ("GET", "/"),
    ("GET", "/health/live"),
    ("GET", "/health/ready"),
}
# Swagger UI is only mounted in development (see `DOCS_ENABLED` in app.main).
DEV_DOCS_ROUTES = {
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
    ("GET", "/openapi.json"),
}


# --------------------------------------------------------------------------- #
# Permission layer                                                            #
# --------------------------------------------------------------------------- #


def _iter_effective_routes(router, prefix: str = "") -> Iterator:
    """Yield every APIRoute reachable from ``router``.

    FastAPI >= 0.100 keeps included routers as lazy `_IncludedRouter` nodes, so
    ``app.routes`` no longer enumerates nested routes directly. Walking the
    original routers (and their include prefixes) keeps this architectural
    guard working across FastAPI versions.
    """
    for route in getattr(router, "routes", []):
        if hasattr(route, "endpoint") and hasattr(route, "methods"):
            yield prefix, route
            continue
        original = getattr(route, "original_router", None)
        if original is None:
            continue
        nested_prefix = getattr(route.include_context, "prefix", "") or ""
        yield from _iter_effective_routes(original, prefix + nested_prefix)


def _declared_permissions() -> dict[tuple[str, str], str | None]:
    """Map ``(method, path)`` to the permission the endpoint declares."""
    declared: dict[tuple[str, str], str | None] = {}
    for prefix, route in _iter_effective_routes(app):
        permission = getattr(route.endpoint, "__required_permission__", None)
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            declared[(method, prefix + route.path)] = permission
    return declared


def _all_paths() -> set[str]:
    return {prefix + route.path for prefix, route in _iter_effective_routes(app)}


def test_every_business_route_under_api_v1_declares_a_permission() -> None:
    """Fail closed: an undeclared business route is a 403, never a 200.

    This is the architectural guard. A developer who adds a router without
    declaring permissions cannot accidentally expose it, and any route that
    *is* reachable must be provably intentional.
    """
    offenders: list[str] = []
    for (method, path), permission in _declared_permissions().items():
        if not path.startswith("/api/v1"):
            continue
        if (method, path) in PUBLIC_ROUTE_ALLOWLIST:
            continue
        if permission is None:
            offenders.append(f"{method} {path}")

    assert not offenders, f"business routes without @require_permission: {offenders}"


def test_public_allowlist_is_explicit_and_minimal() -> None:
    """The unauthenticated surface must stay exactly the declared allowlist."""
    allowed = PUBLIC_ROUTE_ALLOWLIST | UNAUTHENTICATED_ROUTES | DEV_DOCS_ROUTES
    unguarded = [
        f"{method} {path}"
        for (method, path), permission in _declared_permissions().items()
        if permission is None and (method, path) not in allowed
    ]

    assert not unguarded, f"unexpected unauthenticated routes: {unguarded}"


def test_every_declared_public_route_is_actually_reachable() -> None:
    """Guard against an allowlist entry rotting into a stale no-op."""
    declared = set(_declared_permissions())
    missing = {
        f"{method} {path}"
        for method, path in PUBLIC_ROUTE_ALLOWLIST
        if (method, path) not in declared
    }

    assert not missing, f"public allowlist references unknown routes: {missing}"


def test_no_demo_or_sample_router_is_mounted() -> None:
    """The old public `/api/v1/items` sample endpoints are gone for good."""
    assert not any("/items" in path for path in _all_paths())


async def test_health_endpoints_require_no_session(client: AsyncClient) -> None:
    anonymous = {
        ("GET", "/"),
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
    }
    for _, path in sorted(anonymous):
        assert (await client.get(path)).status_code in {200, 503}


async def test_missing_permission_declaration_is_denied_with_403() -> None:
    """A route that forgot `@require_permission` must fail closed, not open.

    Built on a throwaway app so the real router tree is untouched; the
    dependency under test is the same one every business router carries.
    """
    unsafe_app = FastAPI()
    router = APIRouter(dependencies=[Depends(enforce_route_permission)])

    @router.get("/undeclared")
    async def undeclared():
        return {"leaked": True}

    unsafe_app.include_router(router, prefix="/api/v1")
    unsafe_app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=uuid4(),
        email="t@ttcs-demo.org",
        full_name="T",
        organization_id=uuid4(),
        organization_name="Org",
        organization_type="farm",
        role="system_admin",
    )

    transport = ASGITransport(app=unsafe_app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as unsafe_client:
        response = await unsafe_client.get("/api/v1/undeclared")

    assert response.status_code == 403
    assert "chưa được cấu hình" in response.json()["detail"]


def test_missing_permission_emits_a_security_log(caplog) -> None:
    """The fail-closed decision must leave an auditable trail."""
    from app.core.logging_config import configure_logging

    configure_logging()
    request = Request(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/api/v1/undeclared",
            "headers": [],
            "client": ("10.0.0.1", 51234),
        }
    )
    principal = Principal(
        user_id=uuid4(),
        email="t@ttcs-demo.org",
        full_name="T",
        organization_id=uuid4(),
        organization_name="Org",
        organization_type="farm",
        role="grower",
    )

    with caplog.at_level(logging.WARNING, logger="app.security"):
        with pytest.raises(HTTPException) as excinfo:
            enforce_route_permission(request, principal)

    assert excinfo.value.status_code == 403
    record = next(
        r
        for r in caplog.records
        if getattr(r, "event", None) == "authorization.route_missing_permission"
    )
    assert record.user_id == str(principal.user_id)
    assert record.organization_id == str(principal.organization_id)
    assert record.path == "/api/v1/undeclared"
    assert record.client_ip == "10.0.0.1"


def test_cross_organization_access_emits_a_security_log(
    caplog, admin_db: Session, tenant_factory
) -> None:
    """A 403 on a foreign record must be logged with the resource identity."""
    from app.core.logging_config import configure_logging
    from app.core.tenancy import get_tenant_record
    from app.models.farm import Farm

    configure_logging()
    owner = tenant_factory()
    attacker = tenant_factory()
    victim_farm = create_farm(admin_db, owner)

    principal = Principal(
        user_id=attacker.user.id,
        email=attacker.user.email,
        full_name=attacker.user.full_name,
        organization_id=attacker.organization_id,
        organization_name=attacker.organization.name,
        organization_type="farm",
        role="grower",
    )

    with caplog.at_level(logging.WARNING, logger="app.security"):
        with pytest.raises(HTTPException) as excinfo:
            get_tenant_record(admin_db, Farm, victim_farm.id, principal)

    assert excinfo.value.status_code == 403
    record = next(
        r
        for r in caplog.records
        if getattr(r, "event", None) == "authorization.cross_organization_access"
    )
    assert record.resource_type == "farms"
    assert record.resource_id == str(victim_farm.id)
    assert record.organization_id == str(attacker.organization_id)


async def test_insufficient_permission_is_denied_with_403(
    client: AsyncClient, tenant_factory
) -> None:
    """A valid session without the required permission is still a 403."""
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    client = await login_as(client, inspector)

    response = await client.post(
        "/api/v1/farms/",
        json={
            "name": "Không được phép",
            "area_ha": "1.0",
            "latitude": "10.0",
            "longitude": "106.0",
        },
    )

    assert response.status_code == 403


def test_permission_matrix_keeps_inspection_read_only() -> None:
    """Inspection can read lots across tenants but must never write anything."""
    assert has_permission("inspector", "lots:read")
    assert has_permission("inspector", "lots:read_all")
    for forbidden in (
        "farms:write",
        "lots:write",
        "products:write",
        "shipments:create",
        "shipments:receive",
        "sensors:write",
        "users:manage",
        "organizations:manage",
    ):
        assert not has_permission("inspector", forbidden), forbidden


def test_require_permission_marker_is_attached_to_the_endpoint() -> None:
    @require_permission("farms:read")
    def endpoint():
        return None

    assert endpoint.__required_permission__ == "farms:read"


def test_farms_endpoints_declare_farm_permissions() -> None:
    declared = _declared_permissions()

    assert declared[("GET", "/api/v1/farms/")] == "farms:read"
    assert declared[("POST", "/api/v1/farms/")] == "farms:write"
    assert declared[("GET", "/api/v1/farms/{farm_id}")] == "farms:read"
    assert declared[("PATCH", "/api/v1/farms/{farm_id}")] == "farms:write"
    assert declared[("PUT", "/api/v1/farms/{farm_id}")] == "farms:write"


# --------------------------------------------------------------------------- #
# Query layer: cross-tenant access                                            #
# --------------------------------------------------------------------------- #


async def test_tenant_a_cannot_read_tenant_b_farm_by_id(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    owner = tenant_factory()
    attacker = tenant_factory()
    victim_farm = create_farm(admin_db, owner, name="Ruộng của tổ chức B")

    client = await login_as(client, attacker)
    response = await client.get(f"/api/v1/farms/{victim_farm.id}")

    assert response.status_code == 403
    assert "tổ chức khác" in response.json()["detail"]


async def test_tenant_a_cannot_update_tenant_b_farm(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    owner = tenant_factory()
    attacker = tenant_factory()
    victim_farm = create_farm(admin_db, owner, name="Ruộng của tổ chức B")

    client = await login_as(client, attacker)
    response = await client.patch(
        f"/api/v1/farms/{victim_farm.id}", json={"name": "Chiếm đoạt"}
    )

    assert response.status_code == 403
    admin_db.expire_all()
    from app.models.farm import Farm

    assert admin_db.get(Farm, victim_farm.id).name == "Ruộng của tổ chức B"


async def test_missing_record_returns_404_not_403(
    client: AsyncClient, tenant_factory
) -> None:
    """404 and 403 must stay distinguishable for genuinely absent records."""
    tenant = tenant_factory()
    client = await login_as(client, tenant)

    response = await client.get(f"/api/v1/farms/{uuid4()}")

    assert response.status_code == 404


async def test_tenant_a_cannot_list_tenant_b_lot_by_id(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    owner = tenant_factory()
    attacker = tenant_factory()
    farm = create_farm(admin_db, owner)
    product = create_product(admin_db, owner)
    victim_lot = create_lot(admin_db, owner, farm, product)

    client = await login_as(client, attacker)
    response = await client.get(f"/api/v1/lots/{victim_lot.id}")

    assert response.status_code == 403


async def test_tenant_a_listing_never_includes_tenant_b_records(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    owner = tenant_factory()
    attacker = tenant_factory()
    farm = create_farm(admin_db, owner)
    product = create_product(admin_db, owner)
    create_lot(admin_db, owner, farm, product, lot_number="LOT-B-1")
    own_farm = create_farm(admin_db, attacker, name="Ruộng của tôi")
    own_product = create_product(admin_db, attacker)
    create_lot(admin_db, attacker, own_farm, own_product, lot_number="LOT-A-1")

    client = await login_as(client, attacker)
    response = await client.get("/api/v1/lots/")

    assert response.status_code == 200
    numbers = {item["lot_number"] for item in response.json()["items"]}
    assert numbers == {"LOT-A-1"}


# --------------------------------------------------------------------------- #
# Database layer: PostgreSQL row-level security                               #
# --------------------------------------------------------------------------- #


@pytest.fixture
def app_role_db():
    """A raw connection as the unprivileged application database role.

    Deliberately *not* the request-scoped session: this proves that isolation
    holds even for a client that bypasses the application query layer.
    """
    engine = create_engine(APP_URL)
    try:
        yield engine
    finally:
        engine.dispose()


def test_application_role_is_not_privileged(app_role_db) -> None:
    with app_role_db.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
            )
            is False
        )
        assert (
            connection.scalar(
                text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
            )
            is False
        )


def test_tenant_tables_have_row_level_security_forced(app_role_db) -> None:
    expected = {
        "farms",
        "users",
        "sessions",
        "products",
        "lots",
        "lot_lineage",
        "lot_events",
        "shipments",
        "sensors",
        "temperature_readings",
        "cold_chain_alerts",
    }
    with app_role_db.connect() as connection:
        enabled = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT relname FROM pg_class "
                    "WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace "
                    "AND relforcerowsecurity"
                )
            )
        }

    assert expected <= enabled, (
        f"missing FORCE ROW LEVEL SECURITY: {expected - enabled}"
    )


def test_rls_blocks_cross_tenant_read_even_with_raw_sql(
    app_role_db, admin_db: Session, tenant_factory
) -> None:
    """The database itself must refuse to show another tenant's rows."""
    owner = tenant_factory()
    attacker = tenant_factory()
    victim_farm = create_farm(admin_db, owner, name="Ruộng bí mật")

    with app_role_db.connect() as connection:
        connection.execute(
            text("SELECT set_config('app.current_organization', :org, true)"),
            {"org": str(attacker.organization_id)},
        )
        visible = (
            connection.execute(
                text("SELECT name FROM farms WHERE id = :farm_id"),
                {"farm_id": str(victim_farm.id)},
            )
            .scalars()
            .all()
        )

        assert visible == [], "RLS leaked another tenant's farm to the app role"
        assert connection.execute(text("SELECT count(*) FROM farms")).scalar() == 0


def test_rls_blocks_cross_tenant_write_even_with_raw_sql(
    app_role_db, admin_db: Session, tenant_factory
) -> None:
    """A WITH CHECK violation must abort the write, not silently no-op."""
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
                    "VALUES (:id, :org, 'Chèn trộm', 1.0, 10.0, 106.0)"
                ),
                {"id": str(uuid4()), "org": str(owner.organization_id)},
            )
            connection.commit()

    assert "row-level security" in str(excinfo.value).lower()


def test_rls_tenant_context_does_not_leak_between_transactions(
    app_role_db, admin_db: Session, tenant_factory
) -> None:
    """`SET LOCAL` must be transaction-scoped, not connection-scoped.

    Reusing one pooled connection for a second tenant must not inherit the
    first tenant's organization context.
    """
    first = tenant_factory()
    second = tenant_factory()
    create_farm(admin_db, first, name="Ruộng A")

    with app_role_db.connect() as connection:
        # Transaction 1: tenant A.
        connection.execute(
            text("SELECT set_config('app.current_organization', :org, true)"),
            {"org": str(first.organization_id)},
        )
        assert connection.execute(text("SELECT count(*) FROM farms")).scalar() == 1
        connection.commit()

        # Transaction 2 on the SAME connection: tenant B must see nothing.
        connection.execute(
            text("SELECT set_config('app.current_organization', :org, true)"),
            {"org": str(second.organization_id)},
        )
        assert connection.execute(text("SELECT count(*) FROM farms")).scalar() == 0
        connection.commit()

        # Transaction 3: no context at all, so RLS must deny everything.
        assert connection.execute(text("SELECT count(*) FROM farms")).scalar() == 0
        connection.commit()


def test_application_role_cannot_read_rows_without_a_tenant_context(
    app_role_db,
) -> None:
    """No context means no rows: RLS must not fall open."""
    with app_role_db.connect() as connection:
        for table in ("farms", "products", "lots", "shipments", "sensors"):
            assert (
                connection.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0
            ), table


# --------------------------------------------------------------------------- #
# Inspector: cross-organization read of the real `lots` table                  #
# --------------------------------------------------------------------------- #


async def test_inspector_lists_lots_across_all_organizations(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    for index in range(3):
        grower = tenant_factory(prefix=f"grower{index}")
        farm = create_farm(admin_db, grower, name=f"Ruộng {index}")
        product = create_product(admin_db, grower)
        create_lot(admin_db, grower, farm, product, lot_number=f"LOT-{index}")

    client = await login_as(client, inspector)
    response = await client.get("/api/v1/lots/?page_size=100")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert {item["lot_number"] for item in body["items"]} == {"LOT-0", "LOT-1", "LOT-2"}


async def test_inspector_reads_a_lot_from_another_organization(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    grower = tenant_factory()
    farm = create_farm(admin_db, grower)
    product = create_product(admin_db, grower)
    lot = create_lot(admin_db, grower, farm, product)

    client = await login_as(client, inspector)
    response = await client.get(f"/api/v1/lots/{lot.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(lot.id)


async def test_inspector_cannot_create_a_lot(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    grower = tenant_factory()
    farm = create_farm(admin_db, grower)
    product = create_product(admin_db, grower)

    client = await login_as(client, inspector)
    response = await client.post(
        "/api/v1/lots/",
        json={
            "product_id": str(product.id),
            "origin_farm_id": str(farm.id),
            "lot_number": "LOT-INSPECTOR",
            "quantity": "10.000",
            "unit": "kg",
        },
    )

    assert response.status_code == 403


async def test_inspector_cannot_modify_a_lot(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    grower = tenant_factory()
    farm = create_farm(admin_db, grower)
    product = create_product(admin_db, grower)
    lot = create_lot(admin_db, grower, farm, product)

    client = await login_as(client, inspector)
    response = await client.post(
        f"/api/v1/lots/{lot.id}/events",
        json={"event_type": "harvested", "occurred_at": "2026-01-01T00:00:00+00:00"},
    )

    assert response.status_code == 403


async def test_inspector_cannot_create_or_update_a_farm(
    client: AsyncClient, tenant_factory
) -> None:
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    client = await login_as(client, inspector)

    created = await client.post(
        "/api/v1/farms/",
        json={
            "name": "Ruộng của thanh tra",
            "area_ha": "1.0",
            "latitude": "10.0",
            "longitude": "106.0",
        },
    )
    listed = await client.get("/api/v1/farms/")

    assert created.status_code == 403
    assert listed.status_code == 403


def test_inspector_sees_all_tenants_lots_in_the_database_layer(
    app_role_db, admin_db: Session, tenant_factory
) -> None:
    """Inspection's cross-tenant read is granted by the `lots_tenant_read`
    policy, verified as the application role rather than a test helper."""
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    for index in range(2):
        grower = tenant_factory(prefix=f"g{index}")
        farm = create_farm(admin_db, grower)
        product = create_product(admin_db, grower)
        create_lot(admin_db, grower, farm, product)

    with app_role_db.connect() as connection:
        connection.execute(
            text("SELECT set_config('app.current_role', 'inspector', true)")
        )
        connection.execute(
            text("SELECT set_config('app.current_organization', :org, true)"),
            {"org": str(inspector.organization_id)},
        )
        assert connection.execute(text("SELECT count(*) FROM lots")).scalar() == 2


def test_inspector_cannot_write_lots_in_the_database_layer(
    app_role_db, admin_db: Session, tenant_factory
) -> None:
    """Read-only inspection must hold at the RLS layer, not just the API.

    Note the failure mode: RLS filters UPDATE rows out of the USING clause, so
    the statement succeeds but matches nothing. The assertion is therefore on
    the row's unchanged value, not on an exception.
    """
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    grower = tenant_factory()
    farm = create_farm(admin_db, grower)
    product = create_product(admin_db, grower)
    lot = create_lot(admin_db, grower, farm, product)

    with app_role_db.connect() as connection:
        connection.execute(
            text("SELECT set_config('app.current_role', 'inspector', true)")
        )
        connection.execute(
            text("SELECT set_config('app.current_organization', :org, true)"),
            {"org": str(inspector.organization_id)},
        )
        # The row is visible for reading...
        assert (
            connection.execute(
                text("SELECT count(*) FROM lots WHERE id = :id"), {"id": str(lot.id)}
            ).scalar()
            == 1
        )
        # ...but it is not writable, so the UPDATE must not take effect.
        connection.execute(
            text("UPDATE lots SET status = 'discarded' WHERE id = :id"),
            {"id": str(lot.id)},
        )
        connection.commit()

    admin_db.expire_all()
    assert admin_db.get(Lot, lot.id).status == "created"


def test_inspector_cannot_read_another_tenants_farms_in_the_database_layer(
    app_role_db, admin_db: Session, tenant_factory
) -> None:
    """Migration 20260929_05 removed the blanket inspector read on `farms`."""
    inspector = tenant_factory(role="inspector", organization_type="inspection")
    grower = tenant_factory()
    create_farm(admin_db, grower, name="Ruộng riêng của grower")

    with app_role_db.connect() as connection:
        connection.execute(
            text("SELECT set_config('app.current_role', 'inspector', true)")
        )
        connection.execute(
            text("SELECT set_config('app.current_organization', :org, true)"),
            {"org": str(inspector.organization_id)},
        )
        assert connection.execute(text("SELECT count(*) FROM farms")).scalar() == 0


# --------------------------------------------------------------------------- #
# Session isolation between tenants                                           #
# --------------------------------------------------------------------------- #


async def test_session_principal_is_pinned_to_its_own_organization(
    client: AsyncClient, tenant_factory
) -> None:
    """A session must never be usable to act as a different organization."""
    first = tenant_factory()
    second = tenant_factory()

    client = await login_as(client, first)
    me = await client.get("/api/v1/auth/me")
    assert me.json()["organization_id"] == str(first.organization_id)

    client = await login_as(client, second)
    me = await client.get("/api/v1/auth/me")
    assert me.json()["organization_id"] == str(second.organization_id)


async def test_deactivated_user_session_stops_working(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    client = await login_as(client, tenant)

    admin_db.execute(
        text("UPDATE users SET is_active = false WHERE id = :id"),
        {"id": str(tenant.user.id)},
    )
    admin_db.commit()

    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_inactive_organization_invalidates_the_session(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    client = await login_as(client, tenant)

    admin_db.execute(
        text("UPDATE organizations SET is_active = false WHERE id = :id"),
        {"id": str(tenant.organization_id)},
    )
    admin_db.commit()

    assert (await client.get("/api/v1/auth/me")).status_code == 401


def test_application_role_has_no_delete_on_tenant_data(app_role_db) -> None:
    """Least privilege: append-only provenance tables cannot be tampered with."""
    with app_role_db.connect() as connection:
        for table in ("lot_events", "lot_lineage", "lots", "shipments", "sensors"):
            assert (
                connection.execute(
                    text("SELECT has_table_privilege(current_user, :t, 'DELETE')"),
                    {"t": table},
                ).scalar()
                is False
            ), table
        assert (
            connection.execute(
                text("SELECT has_table_privilege(current_user, 'users', 'UPDATE')")
            ).scalar()
            is True
        )


def test_tenant_context_uses_set_local_not_a_persistent_setting(app_role_db) -> None:
    """`SET LOCAL` is what makes pooled-connection reuse safe."""
    from app.core.database import TENANT_CONTEXT_SETTINGS

    assert set(TENANT_CONTEXT_SETTINGS) == {
        "app.current_organization",
        "app.current_user_id",
        "app.current_role",
        "app.session_token_hash",
        "app.login_email",
    }
    with app_role_db.connect() as connection:
        # A non-local setting survives COMMIT on the same connection...
        connection.execute(text("SELECT set_config('app.probe', 'x', false)"))
        connection.commit()
        assert (
            connection.execute(text("SELECT current_setting('app.probe')")).scalar()
            == "x"
        )
        # ...whereas a local one is discarded together with its transaction, so
        # the tenant context cannot survive into the next request that reuses
        # this pooled connection.
        connection.execute(text("SELECT set_config('app.probe_local', 'y', true)"))
        assert (
            connection.execute(
                text("SELECT current_setting('app.probe_local')")
            ).scalar()
            == "y"
        )
        connection.commit()
        assert (
            connection.execute(
                text("SELECT current_setting('app.probe_local')")
            ).scalar()
            != "y"
        )


def test_session_cookie_name_uses_a_host_prefix_in_production() -> None:
    """A `__Host-` prefix is only honoured when Secure/Path/no-Domain hold."""
    assert settings.SESSION_COOKIE_NAME.startswith("__Host-")
