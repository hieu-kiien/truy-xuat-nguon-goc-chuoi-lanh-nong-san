import ast
import logging
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core.auth import Principal, get_current_principal
from app.core.authorization import enforce_route_permission
from app.main import app

AUTH_ROUTE_ALLOWLIST = {("/api/v1/auth/login", "POST")}
AUTH_QUERY_FILE_ALLOWLIST = {"auth.py"}
DIRECT_QUERY_METHODS = {"execute", "get", "scalar", "scalars"}


def _dependency_calls(dependant) -> Iterator[object]:
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _dependency_calls(dependency)


def _api_routes():
    for route in app.routes:
        for context in getattr(route, "effective_route_contexts", lambda: [])():
            if context.path.startswith("/api/v1/"):
                yield context
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1/"):
            yield route


def test_every_api_route_is_guarded_or_explicitly_allowlisted():
    routes = list(_api_routes())
    assert routes

    seen_allowlist: set[tuple[str, str]] = set()
    for route in routes:
        permission = getattr(route.endpoint, "__required_permission__", None)
        calls = set(_dependency_calls(route.dependant))
        for method in route.methods or set():
            route_key = (route.path, method)
            if route_key in AUTH_ROUTE_ALLOWLIST:
                seen_allowlist.add(route_key)
                assert permission is None
                continue

            assert enforce_route_permission in calls, route_key
            assert permission, route_key

    assert seen_allowlist == AUTH_ROUTE_ALLOWLIST


def test_guard_denies_and_logs_a_route_without_permission(caplog):
    protected_router = APIRouter(dependencies=[Depends(enforce_route_permission)])

    @protected_router.get("/missing-permission")
    def route_without_permission():
        return {"ok": True}

    test_app = FastAPI()
    test_app.include_router(protected_router, prefix="/api/v1")
    test_app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="aa0efde6-4ba6-4ec7-9abf-0fd43839c888",
        email="grower@example.com",
        full_name="Grower",
        organization_id="86a8d72b-6b9c-469d-9fee-7cdd2046e144",
        organization_name="Farm",
        organization_type="farm",
        role="grower",
    )

    with TestClient(test_app, base_url="https://testserver") as client:
        with caplog.at_level(logging.WARNING):
            response = client.get("/api/v1/missing-permission")

    assert response.status_code == 403
    assert any(
        getattr(record, "event", None) == "authorization.route_missing_permission"
        for record in caplog.records
    )


def test_business_endpoint_queries_must_use_tenant_helpers():
    endpoint_dir = Path(__file__).parents[1] / "app" / "api" / "v1" / "endpoints"
    violations: list[str] = []

    for source_path in endpoint_dir.glob("*.py"):
        if source_path.name in AUTH_QUERY_FILE_ALLOWLIST:
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == "select":
                violations.append(f"{source_path.name}:{node.lineno}: select()")
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in {"scalar", "scalars"}
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"db", "session"}
                and any(
                    isinstance(argument, ast.Call)
                    and isinstance(argument.func, ast.Name)
                    and argument.func.id == "tenant_select"
                    for argument in node.args
                )
            ):
                continue
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in DIRECT_QUERY_METHODS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"db", "session"}
            ):
                violations.append(
                    f"{source_path.name}:{node.lineno}: .{node.func.attr}()"
                )

    assert violations == []
