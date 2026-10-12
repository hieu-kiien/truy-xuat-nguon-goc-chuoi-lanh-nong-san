import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.event import Event
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login, split_body

lineage = fixtures.lineage
lineage_products = fixtures.lineage_products


@pytest.mark.asyncio
async def test_relation_edges_cannot_be_rewritten_even_by_table_admin(
    lineage, admin_session
):
    owner, products, _ = lineage
    parent = add_lot(admin_session, owner, products[0])
    async with client() as api:
        await login(api, owner)
        response = await api.post(
            f"/api/v1/lots/{parent.id}/split", json=split_body("10")
        )
        assert response.status_code == 201
    for statement in [
        "UPDATE lot_relations SET quantity = 1 WHERE parent_lot_id = :id",
        "DELETE FROM lot_relations WHERE parent_lot_id = :id",
    ]:
        with pytest.raises(IntegrityError, match="immutable"):
            with admin_session.begin_nested():
                admin_session.execute(text(statement), {"id": parent.id})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_type",
    [
        "lot_split",
        "lot_merged",
        "lot_derived",
        "handover_accepted",
        "lot_moved",
        "lot_consumed",
        " LOT_CONSUMED ",
        "Lot_Moved",
    ],
)
async def test_manual_events_cannot_forge_system_transformation_records(
    lineage, admin_session, event_type
):
    owner, products, _ = lineage
    lot = add_lot(admin_session, owner, products[0])
    async with client() as api:
        await login(api, owner)
        response = await api.post(
            "/api/v1/events/", json={"lot_id": str(lot.id), "event_type": event_type}
        )
        assert response.status_code == 422, response.text
    admin_session.refresh(lot)
    assert lot.status == "active" and lot.remaining_quantity == lot.quantity
    assert not list(admin_session.scalars(select(Event).where(Event.lot_id == lot.id)))
