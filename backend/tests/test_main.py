from httpx import AsyncClient
import pytest
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_get_items():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/items/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
