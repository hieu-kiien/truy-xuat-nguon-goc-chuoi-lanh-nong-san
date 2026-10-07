from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.database import SessionLocal
from app.core.tenancy import shared_select
from app.main import app
from app.models.farm import Farm
from app.models.product import Product
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


def test_shared_query_helper_only_accepts_registered_global_tables():
    assert shared_select(Product).whereclause is None
    with pytest.raises(TypeError, match="not registered as a shared table"):
        shared_select(Farm)


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_catalog_is_global_duplicate_names_are_rejected_and_growers_are_read_only(
    identity_factory,
):
    admin = identity_factory(role="system_admin", organization_type="administration")
    grower = identity_factory()
    product_name = f"S07 test crop {uuid4().hex}"
    product_id = None

    try:
        async with _client() as admin_client:
            await _login(admin_client, admin)
            created = await admin_client.post(
                "/api/v1/products/",
                json={"name": product_name, "unit": "kg"},
            )
            assert created.status_code == 201, created.text
            product_id = created.json()["id"]
            assert created.json()["price"] == 0

            updated_name = f"{product_name} updated"
            updated = await admin_client.put(
                f"/api/v1/products/{product_id}",
                json={"name": updated_name, "unit": "tấn"},
            )
            assert updated.status_code == 200, updated.text
            assert updated.json()["name"] == updated_name
            assert updated.json()["unit"] == "tấn"

            duplicate = await admin_client.post(
                "/api/v1/products/",
                json={"name": updated_name, "unit": "kg"},
            )
            assert duplicate.status_code == 409
            assert "Tên sản phẩm đã tồn tại" in duplicate.json()["detail"]

            invalid_unit = await admin_client.post(
                "/api/v1/products/",
                json={"name": f"Invalid unit {uuid4().hex}", "unit": "bao"},
            )
            assert invalid_unit.status_code == 422

        async with _client() as grower_client:
            await _login(grower_client, grower)
            listing = await grower_client.get("/api/v1/products/")
            assert listing.status_code == 200, listing.text
            assert any(product["id"] == product_id for product in listing.json())

            denied_create = await grower_client.post(
                "/api/v1/products/",
                json={"name": f"Grower attempt {uuid4().hex}", "unit": "kg"},
            )
            assert denied_create.status_code == 403

            denied_update = await grower_client.put(
                f"/api/v1/products/{product_id}",
                json={"name": f"Changed {uuid4().hex}"},
            )
            assert denied_update.status_code == 403

            denied_delete = await grower_client.delete(f"/api/v1/products/{product_id}")
            assert denied_delete.status_code == 403
    finally:
        if product_id is not None:
            with SessionLocal() as db:
                db.execute(delete(Product).where(Product.id == product_id))
                db.commit()
