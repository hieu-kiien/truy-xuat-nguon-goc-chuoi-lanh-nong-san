import json
from pathlib import Path
from uuid import uuid4, uuid5

import pytest
from sqlalchemy import delete, func, select

from app.core.auth import Principal
from app.models.event import Event
from app.models.lot import Lot
from app.models.lot_relation import LotRelation
from app.models.product import Product
from app.seed_lineage_demo import seed_graph
from app.services.event_service import verify_event_chain
from tests.lineage_helpers import client, login

# Fixed external oracle, deliberately independent of traversal/fixture generation.
_ORACLE = json.loads(
    (Path(__file__).parent / "data/lineage-oracle.json").read_text(encoding="utf-8")
)
ANCESTORS = {label: set(expected) for label, expected in _ORACLE["ancestors"].items()}
DESCENDANTS = {
    label: set(expected) for label, expected in _ORACLE["descendants"].items()
}


@pytest.mark.asyncio
async def test_seed_idempotent_mass_event_integrity_and_fixed_oracle(
    request, admin_session
):
    namespace = request.getfixturevalue("seed_namespace")
    identity_factory = request.getfixturevalue("identity_factory")
    identities = [
        identity_factory(role=role, organization_type=kind)
        for role, kind in [
            ("grower", "farm"),
            ("cooperative", "cooperative"),
            ("distributor", "distribution"),
        ]
    ]
    inspector = identity_factory(role="inspector", organization_type="inspection")
    principals = [
        Principal(i.user_id, i.email, "Seed", i.organization_id, "Seed", kind, role)
        for i, (role, kind) in zip(
            identities,
            [
                ("grower", "farm"),
                ("cooperative", "cooperative"),
                ("distributor", "distribution"),
            ],
            strict=True,
        )
    ]
    ids = seed_graph(admin_session, principals, namespace)
    admin_session.commit()
    assert seed_graph(admin_session, principals, namespace) == ids
    admin_session.commit()
    try:
        assert (
            admin_session.scalar(
                select(func.count()).select_from(Lot).where(Lot.id.in_(ids.values()))
            )
            == 12
        )
        assert (
            admin_session.scalar(
                select(func.sum(Lot.remaining_quantity)).where(Lot.id.in_(ids.values()))
            )
            == 180
        )
        assert (
            admin_session.scalar(
                select(func.count())
                .select_from(LotRelation)
                .where(LotRelation.parent_lot_id.in_(ids.values()))
            )
            == 12
        )
        for lot_id in ids.values():
            events = list(
                admin_session.scalars(
                    select(Event)
                    .where(Event.lot_id == lot_id)
                    .order_by(Event.sequence_number)
                )
            )
            assert verify_event_chain(events)["valid"], events
        async with client() as api:
            await login(api, inspector)
            for direction, oracle in [
                ("ancestors", ANCESTORS),
                ("descendants", DESCENDANTS),
            ]:
                for label, expected in oracle.items():
                    response = await api.get(
                        f"/api/v1/lots/{ids[label]}/lineage?direction={direction}"
                    )
                    assert response.status_code == 200, response.text
                    assert {n["id"] for n in response.json()["nodes"]} == {
                        str(ids[key]) for key in expected | {label}
                    }, (direction, label, response.json())
    finally:
        admin_session.rollback()


@pytest.fixture
def seed_namespace(admin_session):
    namespace = uuid4()
    yield namespace
    # Requested before identity_factory, so its lots are already removed here.
    admin_session.execute(
        delete(Product).where(Product.id == uuid5(namespace, "product"))
    )
    admin_session.commit()
