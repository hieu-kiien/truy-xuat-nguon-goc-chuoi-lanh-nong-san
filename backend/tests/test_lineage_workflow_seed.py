"""Prove service-based workflow, independent oracle, idempotency and rollback."""

import json
from pathlib import Path
from uuid import uuid5

import pytest
from sqlalchemy import func, select

from app.core.auth import Principal
from app.models.event import Event
from app.models.lot import Lot
from app.models.product import Product
from app.seed_lineage_workflow import seed_workflow
from app.services import lineage_service
from tests import test_lineage_seed as seed_fixtures
from tests.lineage_helpers import client, login

seed_namespace = seed_fixtures.seed_namespace


@pytest.mark.asyncio
async def test_workflow_seed_calls_services_and_matches_all_36_fixed_sets(
    request, admin_session, admin_engine
):
    namespace = request.getfixturevalue("seed_namespace")
    identities = request.getfixturevalue("identity_factory")
    actors = [
        identities(role=role, organization_type=kind)
        for role, kind in [
            ("grower", "farm"),
            ("cooperative", "cooperative"),
            ("distributor", "distribution"),
        ]
    ]
    inspector = identities(role="inspector", organization_type="inspection")
    principals = [
        Principal(
            actor.user_id,
            actor.email,
            "Seed",
            actor.organization_id,
            "Seed",
            kind,
            role,
        )
        for actor, (role, kind) in zip(
            actors,
            [
                ("grower", "farm"),
                ("cooperative", "cooperative"),
                ("distributor", "distribution"),
            ],
            strict=True,
        )
    ]
    ids = seed_workflow(admin_engine, principals, namespace)
    assert len(ids) == 18
    hashes = list(
        admin_session.execute(
            select(Event.id, Event.event_hash)
            .where(Event.lot_id.in_(ids.values()))
            .order_by(Event.id)
        )
    )
    assert seed_workflow(admin_engine, principals, namespace) == ids
    assert (
        list(
            admin_session.execute(
                select(Event.id, Event.event_hash)
                .where(Event.lot_id.in_(ids.values()))
                .order_by(Event.id)
            )
        )
        == hashes
    )
    assert (
        admin_session.scalar(
            select(func.sum(Lot.remaining_quantity)).where(Lot.id.in_(ids.values()))
        )
        == 300
    )
    oracle = json.loads(
        (Path(__file__).parent / "data/workflow-lineage-oracle.json").read_text(
            encoding="utf-8"
        )
    )
    async with client() as api:
        await login(api, inspector)
        for direction in ("ancestors", "descendants"):
            for label, expected in oracle[direction].items():
                response = await api.get(
                    f"/api/v1/lots/{ids[label]}/lineage?direction={direction}"
                )
                assert response.status_code == 200, response.text
                assert {node["id"] for node in response.json()["nodes"]} == {
                    str(ids[key]) for key in [label, *expected]
                }
        for lot_id in ids.values():
            history = await api.get(f"/api/v1/events/lots/{lot_id}/history")
            assert history.json()["integrity"]["valid"]


def test_workflow_seed_rolls_back_all_service_commits_on_late_failure(
    request, admin_session, admin_engine, monkeypatch
):
    namespace = request.getfixturevalue("seed_namespace")
    identities = request.getfixturevalue("identity_factory")
    actors = [
        identities(role=role, organization_type=kind)
        for role, kind in [
            ("grower", "farm"),
            ("cooperative", "cooperative"),
            ("distributor", "distribution"),
        ]
    ]
    principals = [
        Principal(
            actor.user_id,
            actor.email,
            "Seed",
            actor.organization_id,
            "Seed",
            kind,
            role,
        )
        for actor, (role, kind) in zip(
            actors,
            [
                ("grower", "farm"),
                ("cooperative", "cooperative"),
                ("distributor", "distribution"),
            ],
            strict=True,
        )
    ]

    def fail(*args, **kwargs):
        raise RuntimeError("Injected late merge failure")

    monkeypatch.setattr(lineage_service, "merge_lots", fail)
    with pytest.raises(RuntimeError, match="late merge"):
        seed_workflow(admin_engine, principals, namespace)
    assert admin_session.get(Product, uuid5(namespace, "product")) is None
    assert not admin_session.scalars(
        select(Lot).where(
            Lot.organization_id.in_([actor.organization_id for actor in actors])
        )
    ).all()
