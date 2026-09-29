import pytest
from httpx import ASGITransport, AsyncClient

from app.core.authorization import has_permission
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_get_items():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/items/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_organization_admin_has_only_mvp_farm_and_lot_read_access():
    assert has_permission("organization_admin", "farms:read")
    assert has_permission("organization_admin", "farms:write")
    assert has_permission("organization_admin", "lots:read")
    assert not has_permission("organization_admin", "lots:write")
