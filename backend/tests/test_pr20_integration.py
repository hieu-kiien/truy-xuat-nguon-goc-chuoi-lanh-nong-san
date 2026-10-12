"""Scenarios ported from PR #20 to the canonical lineage API.

Original cases: test_n339_concurrency.py (60 then rejected 50 from 100 kg),
and test_sprint3_split_merge.py (50/30/10 split and direct children).
Original commit history is preserved by the integration merge.
"""

from decimal import Decimal
from uuid import UUID

import pytest

from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login, split_body

lineage = fixtures.lineage
lineage_products = fixtures.lineage_products
assert_mass = fixtures.assert_mass


@pytest.mark.asyncio
async def test_repeated_split_uses_remaining_stock_and_extends_existing_chain(
    lineage, admin_session
):
    owner, products, _ = lineage
    parent = add_lot(admin_session, owner, products[0], quantity="100")
    async with client() as api:
        await login(api, owner)
        first = await api.post(f"/api/v1/lots/{parent.id}/split", json=split_body("60"))
        assert first.status_code == 201, first.text
        initial_detail = await api.get(f"/api/v1/lots/{parent.id}")
        assert initial_detail.status_code == 200, initial_detail.text
        before = initial_detail.json()
        rejected = await api.post(
            f"/api/v1/lots/{parent.id}/split", json=split_body("50")
        )
        assert rejected.status_code == 409, rejected.text
        final_detail = await api.get(f"/api/v1/lots/{parent.id}")
        assert final_detail.status_code == 200, final_detail.text
        after = final_detail.json()
        assert after == before
        assert_mass(admin_session, parent.id, "40")

        last = await api.post(f"/api/v1/lots/{parent.id}/split", json=split_body("40"))
        assert last.status_code == 201, last.text
        assert_mass(admin_session, parent.id, "0", "closed")
        history = await api.get(f"/api/v1/events/lots/{parent.id}/history")
        assert history.status_code == 200, history.text
        assert history.json()["integrity"]["valid"] is True
        events = history.json()["events"]
        assert len(events) == 2
        assert [event["event_type"] for event in events] == ["lot_split", "lot_split"]
        assert events[1]["prev_hash"] == events[0]["event_hash"]


@pytest.mark.asyncio
async def test_three_child_split_preserves_mass_and_excludes_grandchildren_from_detail(
    lineage, admin_session
):
    owner, products, _ = lineage
    root = add_lot(admin_session, owner, products[0], quantity="100")
    async with client() as api:
        await login(api, owner)
        first = await api.post(
            f"/api/v1/lots/{root.id}/split", json=split_body("50", "30", "10")
        )
        assert first.status_code == 201, first.text
        children = first.json()["children"]
        assert len(children) == 3
        assert sum(Decimal(str(c["quantity"])) for c in children) == Decimal("90")
        assert_mass(admin_session, root.id, "10")
        child = children[0]
        second = await api.post(
            f"/api/v1/lots/{child['id']}/split", json=split_body("20")
        )
        assert second.status_code == 201, second.text
        grandchild = second.json()["children"][0]
        detail = await api.get(f"/api/v1/lots/{root.id}")
        assert detail.status_code == 200, detail.text
        assert {c["id"] for c in detail.json()["children"]} == {
            c["id"] for c in children
        }
        trace = await api.get(
            f"/api/v1/lots/{grandchild['id']}/lineage?direction=ancestors"
        )
        assert trace.status_code == 200, trace.text
        assert trace.json()["roots"] == [str(root.id)]
        assert {n["id"] for n in trace.json()["nodes"]} == {
            str(root.id),
            child["id"],
            grandchild["id"],
        }
        assert UUID(trace.json()["root_farms"][0]["id"]) == root.farm_id
