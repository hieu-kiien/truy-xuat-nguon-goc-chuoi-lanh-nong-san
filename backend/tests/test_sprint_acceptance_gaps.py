"""Explicit acceptance evidence for remaining Sprint 3 task boundaries."""

from uuid import UUID

import pytest
from sqlalchemy import text

from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login, merge_body, split_body

lineage = fixtures.lineage
lineage_products = fixtures.lineage_products


@pytest.mark.asyncio
async def test_overstock_identifies_owned_lot_and_actual_remaining(
    lineage, admin_session
):
    owner, products, _ = lineage
    source = add_lot(admin_session, owner, products[0])
    async with client() as api:
        await login(api, owner)
        result = await api.post(
            f"/api/v1/lots/{source.id}/split", json=split_body("40.001")
        )
    assert result.status_code == 409
    assert source.lot_code in result.json()["detail"]
    assert "40.000 kg" in result.json()["detail"]


@pytest.mark.asyncio
async def test_wrong_product_names_only_the_authorized_offending_lot(
    lineage, admin_session
):
    owner, products, _ = lineage
    first = add_lot(admin_session, owner, products[0])
    other = add_lot(admin_session, owner, products[1])
    async with client() as api:
        await login(api, owner)
        result = await api.post(
            "/api/v1/lots/merge", json=merge_body((first, "1"), (other, "1"))
        )
    assert result.status_code == 422
    assert other.lot_code in result.json()["detail"]


@pytest.mark.asyncio
async def test_tampering_child_genesis_does_not_corrupt_sibling_or_parent(
    lineage, admin_session
):
    owner, products, _ = lineage
    root = add_lot(admin_session, owner, products[0])
    async with client() as api:
        await login(api, owner)
        response = await api.post(
            f"/api/v1/lots/{root.id}/split", json=split_body("10", "20")
        )
        assert response.status_code == 201
        children = response.json()["children"]
        # Simulate privileged corruption only in this isolated test database.
        with admin_session.begin_nested():
            admin_session.execute(text("ALTER TABLE events DISABLE TRIGGER USER"))
            admin_session.execute(
                text(
                    "UPDATE events SET payload = payload || jsonb_build_object('tampered', true) WHERE lot_id=:id AND sequence_number=1"
                ),
                {"id": UUID(children[0]["id"])},
            )
            admin_session.execute(text("ALTER TABLE events ENABLE TRIGGER USER"))
        admin_session.commit()
        for lot_id, expected in [
            (children[0]["id"], False),
            (children[1]["id"], True),
            (str(root.id), True),
        ]:
            history = await api.get(f"/api/v1/events/lots/{lot_id}/history")
            assert history.status_code == 200
            assert history.json()["integrity"]["valid"] is expected
