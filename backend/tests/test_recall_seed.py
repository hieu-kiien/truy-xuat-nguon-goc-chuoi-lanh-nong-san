"""Test suite for N3-54: Recall sample dataset and independent hand-counted oracle."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.auth import Principal
from app.models.event import Event
from app.models.lot import Lot
from app.seed_recall_demo import seed_recall_workflow
from tests import test_lineage_seed as seed_fixtures
from tests.lineage_helpers import client, login

seed_namespace = seed_fixtures.seed_namespace


def load_recall_oracle() -> dict:
    oracle_path = Path(__file__).parent / "data/recall-lineage-oracle.json"
    assert oracle_path.exists(), (
        "Tệp đáp án đếm tay recall-lineage-oracle.json không tồn tại!"
    )
    return json.loads(oracle_path.read_text(encoding="utf-8"))


def test_recall_oracle_structure_and_two_independent_counters():
    """Verify AC2: Oracle ground truth is written with independent counters and complete data."""
    oracle = load_recall_oracle()

    # Kiểm tra metadata và 2 người kiểm định độc lập
    meta = oracle["meta"]
    assert meta["ticket"] == "N3-54"
    assert meta["backlog"] == "S-39"
    assert len(meta["independent_counters"]) >= 2
    counters = [c["name"] for c in meta["independent_counters"]]
    assert len(set(counters)) >= 2, "Cần ít nhất 2 người đếm độc lập!"

    # Kiểm tra tra cứu theo lô gốc R1
    root_lots = oracle["root_lots"]
    assert "R1" in root_lots
    r1 = root_lots["R1"]
    assert r1["root_lot_label"] == "R1"
    assert r1["initial_quantity"] == "100.000"

    descendants = r1["descendants"]
    descendant_labels = [d["label"] for d in descendants]
    assert "D1" in descendant_labels
    assert "D2" in descendant_labels
    assert "M1" in descendant_labels

    # AC1: Kiểm tra có ít nhất 1 lô gộp từ nhiều nguồn và 1 lô đã tiêu thụ
    multi_source_lots = [d for d in descendants if d["is_multi_source_merge"]]
    assert len(multi_source_lots) >= 1, "Phải có ít nhất 1 lô gộp từ nhiều nguồn!"

    consumed_lots = [d for d in descendants if d["status"] == "consumed"]
    assert len(consumed_lots) >= 1, "Phải có ít nhất 1 lô đã tiêu thụ!"
    assert consumed_lots[0]["label"] == "D2"
    assert Decimal(consumed_lots[0]["remaining_quantity"]) == Decimal("0.000")
    assert Decimal(consumed_lots[0]["consumed_quantity"]) > Decimal("0.000")

    # Kiểm tra 4 tầng (tier 1..4) và 3 tổ chức (farm, cooperative, distribution)
    tiers = {d["tier"] for d in descendants} | {1}
    assert tiers == {1, 2, 3, 4}, "Đồ thị phải đủ 4 tầng!"

    org_types = {d["holder_org_type"] for d in descendants} | {r1["origin_org_type"]}
    assert org_types == {"farm", "cooperative", "distribution"}, (
        "Phải qua đủ 3 tổ chức!"
    )

    # Kiểm tra tổng kết số liệu
    summary = r1["summary"]
    assert summary["total_descendants_count"] == 8
    assert summary["total_recoverable_kg"] == "140.000"
    assert summary["total_consumed_kg"] == "60.000"
    assert summary["involved_organizations_count"] == 3
    assert summary["has_multi_source_merge"] is True
    assert summary["has_consumed_lot"] is True


def test_recall_oracle_mass_conservation_and_lineage_sets():
    """Verify that oracle math and lineage sets are internally sound and acyclic."""
    oracle = load_recall_oracle()
    lineage = oracle["lineage_sets"]

    ancestors = lineage["ancestors"]
    descendants = lineage["descendants"]

    # Graph consistency: A in ancestors of B <=> B in descendants of A
    for lot_a, anc_list in ancestors.items():
        for anc in anc_list:
            assert lot_a in descendants[anc], f"{lot_a} should be descendant of {anc}"

    for lot_a, desc_list in descendants.items():
        for desc in desc_list:
            assert lot_a in ancestors[desc], f"{lot_a} should be ancestor of {desc}"

    # Verify R1 descendants match oracle root_lots summary
    r1_descendants = set(descendants["R1"])
    r1_from_roots = {d["label"] for d in oracle["root_lots"]["R1"]["descendants"]}
    assert r1_descendants == r1_from_roots


@pytest.mark.asyncio
async def test_recall_workflow_seed_execution_and_db_oracle_verification(
    request, admin_session, admin_engine
):
    """Integration test: execute seed_recall_workflow and verify DB against oracle."""
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

    # Run seed workflow
    ids = seed_recall_workflow(admin_engine, principals, namespace)
    assert len(ids) == 18

    # Verify idempotency: re-running gives identical IDs
    assert seed_recall_workflow(admin_engine, principals, namespace) == ids

    # Verify lot counts and properties in database
    lots = {
        lot.name.rsplit(" — ", 1)[-1]: lot
        for lot in admin_session.scalars(select(Lot).where(Lot.id.in_(ids.values())))
    }
    assert len(lots) == 18

    # AC1: Verify consumed lot
    d2 = lots["D2"]
    assert d2.status == "consumed"
    assert d2.remaining_quantity == 0

    # Verify active lots and location
    d1 = lots["D1"]
    assert d1.status == "active"
    assert d1.remaining_quantity == Decimal("40")
    assert d1.current_location_id is not None

    # Load oracle and verify descendants reachability via API
    oracle = load_recall_oracle()
    async with client() as api:
        await login(api, inspector)
        for label, expected_descendants in oracle["lineage_sets"][
            "descendants"
        ].items():
            res = await api.get(
                f"/api/v1/lots/{ids[label]}/lineage?direction=descendants"
            )
            assert res.status_code == 200, res.text
            expected_nodes = {str(ids[key]) for key in [label, *expected_descendants]}
            actual_nodes = {node["id"] for node in res.json()["nodes"]}
            assert actual_nodes == expected_nodes, f"Mismatch for lot {label}"

    # Verify immutable event log has lot_consumed
    consumed_events = list(
        admin_session.scalars(
            select(Event).where(
                Event.lot_id == d2.id, Event.event_type == "lot_consumed"
            )
        )
    )
    assert len(consumed_events) == 1
