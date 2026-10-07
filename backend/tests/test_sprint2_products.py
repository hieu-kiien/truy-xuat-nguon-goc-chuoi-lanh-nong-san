from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.main import app
from app.models.product import Product
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_system_admin_can_edit_shared_products_and_grower_cannot(
    admin_session: Session, identity_factory
):
    admin = identity_factory(role="system_admin", organization_type="administration")
    grower = identity_factory(role="grower", organization_type="farm")
    suffix = uuid4().hex[:8]
    created_ids: list[str] = []

    async with _client() as admin_client, _client() as grower_client:
        await _login(admin_client, admin)
        await _login(grower_client, grower)

        first = await admin_client.post(
            "/api/v1/products/",
            json={"name": f"Product {suffix} A", "unit": "kg"},
        )
        second = await admin_client.post(
            "/api/v1/products/",
            json={"name": f"Product {suffix} B", "unit": "thùng"},
        )
        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        created_ids.extend([first.json()["id"], second.json()["id"]])

        updated = await admin_client.put(
            f"/api/v1/products/{first.json()['id']}",
            json={"name": f"Product {suffix} A mới", "unit": "tấn"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["unit"] == "tấn"

        duplicate = await admin_client.put(
            f"/api/v1/products/{first.json()['id']}",
            json={"name": f"product {suffix} b", "unit": "kg"},
        )
        assert duplicate.status_code == 409

        forbidden = await grower_client.put(
            f"/api/v1/products/{second.json()['id']}",
            json={"name": f"Changed {suffix}", "unit": "kg"},
        )
        assert forbidden.status_code == 403

    admin_session.execute(delete(Product).where(Product.id.in_(created_ids)))
    admin_session.commit()
