"""Smoke tests for the application shell.

Security-relevant behaviour lives in the N3-5/N3-6/N3-7 suites; this module
only asserts the process starts and the health surface responds.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def smoke_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_health_check(smoke_client: AsyncClient) -> None:
    response = await smoke_client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_liveness(smoke_client: AsyncClient) -> None:
    assert (await smoke_client.get("/health/live")).status_code == 200


async def test_security_headers_are_present(smoke_client: AsyncClient) -> None:
    response = await smoke_client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Request-ID"]


async def test_request_id_is_echoed_for_correlation(smoke_client: AsyncClient) -> None:
    response = await smoke_client.get("/", headers={"X-Request-ID": "abc123"})

    assert response.headers["X-Request-ID"] == "abc123"


async def test_business_routes_reject_anonymous_requests(
    smoke_client: AsyncClient,
) -> None:
    for path in ("/api/v1/farms/", "/api/v1/lots/", "/api/v1/products/"):
        assert (await smoke_client.get(path)).status_code == 401, path
