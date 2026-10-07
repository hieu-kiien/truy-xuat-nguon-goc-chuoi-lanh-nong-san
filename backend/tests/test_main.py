import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_demo_items_route_is_removed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/items/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_check_html_landing():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "AgroChain Backend API" in response.text
    assert "https://ttcs-frontend-staging.onrender.com" in response.text


@pytest.mark.asyncio
async def test_custom_404_html_and_json():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_html = await client.get(
            "/ttcs-backend-staging.onrender.com",
            headers={"Accept": "text/html"},
        )
        assert res_html.status_code == 404
        assert "404" in res_html.text

        res_json = await client.get(
            "/ttcs-backend-staging.onrender.com",
            headers={"Accept": "application/json"},
        )
        assert res_json.status_code == 404
        assert res_json.json()["detail"] == "Not Found"

