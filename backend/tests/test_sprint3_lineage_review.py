"""Additional regression boundaries found during independent lineage review."""

import pytest
from sqlalchemy import select, text

from app.models.event import Event
from app.models.lot import Lot
from app.services import lineage_service
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login, merge_body, split_body

lineage = fixtures.lineage
lineage_products = fixtures.lineage_products
assert_mass = fixtures.assert_mass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "boundary", ["late_overmass", "total_overflow", "code_collision"]
)
async def test_merge_late_failures_restore_all_parents(
    lineage, admin_session, monkeypatch, boundary
):
    owner, products, _ = lineage
    quantity = "99999999999.999" if boundary == "total_overflow" else "40"
    parents = [add_lot(admin_session, owner, products[0], quantity) for _ in range(2)]
    portions = [quantity, quantity]
    expected_status = 422 if boundary == "total_overflow" else 409
    if boundary == "late_overmass":
        portions = ["10", "40.001"]
    if boundary == "code_collision":
        monkeypatch.setattr(
            lineage_service, "generate_lot_code", lambda: parents[0].lot_code
        )
        expected_status = 503
    async with client() as api:
        await login(api, owner)
        response = await api.post(
            "/api/v1/lots/merge",
            json=merge_body((parents[0], portions[0]), (parents[1], portions[1])),
        )
    assert response.status_code == expected_status, response.text
    for parent in parents:
        assert_mass(admin_session, parent.id, quantity)
        assert not admin_session.scalars(
            select(Event).where(Event.lot_id == parent.id)
        ).all()
        assert not admin_session.execute(
            text("SELECT id FROM lot_relations WHERE parent_lot_id = :id"),
            {"id": parent.id},
        ).all()


@pytest.mark.asyncio
async def test_split_collision_after_first_child_rolls_back_partial_creation(
    lineage, admin_session, monkeypatch
):
    owner, products, _ = lineage
    parent = add_lot(admin_session, owner, products[0])
    codes = iter(["R" + parent.lot_code, *([parent.lot_code] * 5)])
    monkeypatch.setattr(lineage_service, "generate_lot_code", lambda: next(codes))
    async with client() as api:
        await login(api, owner)
        response = await api.post(
            f"/api/v1/lots/{parent.id}/split", json=split_body("10", "20")
        )
    assert response.status_code == 503, response.text
    assert_mass(admin_session, parent.id, "40")
    assert (
        admin_session.scalar(select(Lot).where(Lot.lot_code == "R" + parent.lot_code))
        is None
    )
    assert not admin_session.execute(
        text("SELECT id FROM lot_relations WHERE parent_lot_id = :id"),
        {"id": parent.id},
    ).all()
