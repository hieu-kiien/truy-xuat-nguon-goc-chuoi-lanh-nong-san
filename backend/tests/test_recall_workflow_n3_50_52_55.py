"""Comprehensive test suite for N3-50 (S-34), N3-55 (S-36), and N3-52 (S-37).

Covers:
1. N3-50 (S-34):
   - AC1: Given a root lot that went through 4 tiers of split and merge across 3 organizations,
     when viewing the recall order, the descendant list matches the hand-counted oracle (N3-54 / S-39)
     without missing any lot.
   - AC2: Given a descendant is a merged lot with external sources mixed in, when listed, that merged
     lot is included and marked as multi-source merge (is_multi_source_merge = True).
   - AC3: Given a new lot is split from a descendant after the recall order was already opened,
     when refreshing the recall order's affected lots list, the newly created lot appears dynamically.
   - Non-functional: The affected/descendant list of a recall order is recomputed dynamically from
     the lineage graph on every read, NOT hardcoded/frozen at open time.
2. N3-55 (S-36):
   - AC1: Given a recall order was just opened, when a related organization (e.g. distributor holding
     an affected lot) logs in, they see a prominent notification listing their affected lots.
   - AC2: Given the organization has gathered goods from shelves, when they confirm handling,
     the recall order records that their organization has completed handling with timestamp and note.
   - AC3: Given the organization has not yet confirmed handling, when viewing the recall order,
     their organization's part is shown as pending ('pending').
   - Non-functional: Confirmation is an append-only / immutable event (cannot be modified, overwritten,
     or deleted once recorded; enforced by both API/service and PostgreSQL trigger + immutable event log).
3. N3-52 (S-37):
   - AC1: Given a recall order involves N organizations (e.g. 5) and K (e.g. 3) have confirmed,
     when viewing the recall order, it shows progress '3/5' along with the names of pending organizations.
   - AC2: Given the last remaining organization confirms handling, when saved, the recall order
     automatically transitions to 'completed', sets completed_at, and appends an immutable
     'recall_completed' event to the root lot's event history.
   - Non-functional: Completed recall orders remain viewable (read-only, never deleted).
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.core.auth import Principal
from app.core.authorization import has_permission
from app.models.lot import Lot
from app.models.lot_relation import LotRelation
from app.schemas.event import EventCreate
from app.schemas.recall import RecallConfirmCreate
from app.seed_recall_demo import seed_recall_workflow
from tests import test_lineage_seed as seed_fixtures
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login

seed_namespace = seed_fixtures.seed_namespace
lineage_products = fixtures.lineage_products


def load_recall_oracle() -> dict:
    oracle_path = Path(__file__).parent / "data/recall-lineage-oracle.json"
    assert oracle_path.exists(), "Oracle file not found"
    return json.loads(oracle_path.read_text(encoding="utf-8"))


# --- Pure Unit & Schema Tests ---


def test_recall_confirm_schema_and_reserved_event_validation():
    """Verify RecallConfirmCreate validation and that recall_confirmed is a reserved system event."""
    default_payload = RecallConfirmCreate()
    assert len(default_payload.note) > 0

    custom_payload = RecallConfirmCreate(
        note="  Đã thu gom toàn bộ 40kg lô D1 tại kho lạnh trung tâm.  "
    )
    assert (
        custom_payload.note == "Đã thu gom toàn bộ 40kg lô D1 tại kho lạnh trung tâm."
    )

    with pytest.raises(ValidationError):
        RecallConfirmCreate(note="   ")

    # Manual creation of recall_confirmed via /events must be rejected
    with pytest.raises(ValidationError):
        EventCreate(lot_id=uuid4(), event_type="recall_confirmed", payload={})


@pytest.mark.parametrize(
    "role",
    [
        "grower",
        "cooperative",
        "distributor",
        "transporter",
        "organization_admin",
        "system_admin",
    ],
)
def test_roles_authorized_to_confirm_recall_handling(role: str):
    assert has_permission(role, "recalls:confirm") is True


# --- Integration Tests for N3-50 (S-34) ---


@pytest.mark.asyncio
async def test_n3_50_recall_order_lists_all_descendants_matching_oracle_and_updates_dynamically(
    request, admin_session, admin_engine
):
    """N3-50 AC1, AC2, AC3 & Non-functional:
    - AC1: Recall order on R1 lists all 8 descendants across 4 tiers and 3 organizations matching oracle.
    - AC2: Multi-source merged lots (M1, M2, D1, D2, E1, E2) are included and marked is_multi_source_merge=True.
    - AC3 & Non-functional: When a new lot is split/derived from a descendant after the recall order is already open,
      refreshing GET /api/v1/recalls/{id} dynamically includes the new lot without modifying the recall_orders row.
    """
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
            f"Seed {kind}",
            actor.organization_id,
            f"Org {kind}",
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

    ids = seed_recall_workflow(admin_engine, principals, namespace)
    oracle = load_recall_oracle()
    expected_r1 = oracle["root_lots"]["R1"]

    async with client() as api:
        await login(api, inspector)

        # Open recall order on R1
        open_res = await api.post(
            "/api/v1/recalls/",
            json={
                "lot_id": str(ids["R1"]),
                "reason": "Phát hiện tồn dư thuốc bảo vệ thực vật vượt ngưỡng trên lô R1.",
            },
        )
        assert open_res.status_code == 201, open_res.text
        order_data = open_res.json()
        recall_id = order_data["id"]

        # AC1: Verify descendant list on the recall order matches hand-counted oracle 100%
        detail_res = await api.get(f"/api/v1/recalls/{recall_id}")
        assert detail_res.status_code == 200, detail_res.text
        detail = detail_res.json()

        assert detail["summary"]["total_descendants_count"] == 8
        assert detail["summary"]["total_affected_lots"] == 9
        assert detail["summary"]["involved_organizations_count"] == 3
        assert detail["summary"]["has_multi_source_merge"] is True

        actual_by_label = {
            item["name"].rsplit(" — ", 1)[-1]: item for item in detail["descendants"]
        }
        assert set(actual_by_label.keys()) == {
            d["label"] for d in expected_r1["descendants"]
        }

        # AC2: Verify multi-source merges (M1 merged from A1+B1, M2 merged from A2+C1, and their children)
        for exp_desc in expected_r1["descendants"]:
            act = actual_by_label[exp_desc["label"]]
            assert act["tier"] == exp_desc["tier"]
            assert act["status"] == exp_desc["status"]
            assert act["is_multi_source_merge"] == exp_desc["is_multi_source_merge"]
            assert Decimal(str(act["remaining_quantity"])) == Decimal(
                exp_desc["remaining_quantity"]
            )

        assert actual_by_label["M1"]["is_multi_source_merge"] is True
        assert actual_by_label["M2"]["is_multi_source_merge"] is True
        assert actual_by_label["D1"]["is_multi_source_merge"] is True

        # AC3 & Non-functional: Suppose a new lot D1_SUB is split from descendant D1 AFTER the recall order was opened
        d1_lot = admin_session.get(Lot, ids["D1"])
        assert d1_lot is not None
        d1_lot.remaining_quantity = Decimal("25.000")
        new_sub_lot = Lot(
            organization_id=d1_lot.organization_id,
            current_holder_organization_id=d1_lot.current_holder_organization_id,
            name="Cà chua cherry — D1_SUB",
            lot_code=f"L{uuid4().hex[:10].upper()}",
            product_id=d1_lot.product_id,
            harvested_on=date(2026, 10, 2),
            quantity=Decimal("15.000"),
            remaining_quantity=Decimal("15.000"),
            status="active",
        )
        admin_session.add(new_sub_lot)
        admin_session.flush()
        admin_session.add(
            LotRelation(
                organization_id=d1_lot.current_holder_organization_id,
                parent_lot_id=d1_lot.id,
                child_lot_id=new_sub_lot.id,
                quantity=Decimal("15.000"),
                operation="split",
            )
        )
        admin_session.commit()

        # Refreshing the recall order dynamically discovers D1_SUB at tier 5!
        refreshed_res = await api.get(f"/api/v1/recalls/{recall_id}")
        assert refreshed_res.status_code == 200, refreshed_res.text
        refreshed = refreshed_res.json()

        refreshed_labels = {
            item["name"].rsplit(" — ", 1)[-1]: item for item in refreshed["descendants"]
        }
        assert "D1_SUB" in refreshed_labels
        assert refreshed_labels["D1_SUB"]["tier"] == 5
        assert refreshed_labels["D1_SUB"]["is_multi_source_merge"] is True
        assert refreshed["summary"]["total_descendants_count"] == 9


# --- Integration Tests for N3-55 (S-36) & N3-52 (S-37) ---


@pytest.mark.asyncio
async def test_n3_55_and_n3_52_five_organizations_progress_notifications_immutability_and_auto_complete(
    request, admin_session
):
    """Test N3-55 and N3-52 end-to-end across 5 involved organizations:
    - N3-55 AC1: Each related organization sees a recall notification listing its affected lots upon login.
    - N3-55 AC2 & AC3: Confirming records timestamp & note; unconfirmed organizations remain 'pending'.
    - N3-55 Non-functional: Confirmation is strictly append-only (re-confirm returns 409; DB UPDATE/DELETE is blocked by trigger).
    - N3-52 AC1: With 5 involved organizations and 3 confirmed, progress shows '3/5' and lists the 2 pending organizations.
    - N3-52 AC2 & Non-functional: When the 5th organization confirms, status automatically transitions to 'completed',
      records 'recall_completed' in the root lot's immutable event chain, and remains viewable (read-only).
    """
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    org_farm = identities(role="grower", organization_type="farm")
    org_coop = identities(role="cooperative", organization_type="cooperative")
    org_dist1 = identities(role="distributor", organization_type="distribution")
    org_dist2 = identities(role="distributor", organization_type="distribution")
    org_dist3 = identities(role="distributor", organization_type="distribution")
    unrelated_org = identities(role="distributor", organization_type="distribution")
    inspector = identities(role="inspector", organization_type="inspection")

    # Build a lineage graph spanning 5 organizations:
    # Root lot created by org_farm (100 kg), handed over to org_coop, which splits into 3 lots
    # held by org_dist1, org_dist2, org_dist3 while keeping 10 kg at org_coop.
    root_lot = add_lot(admin_session, org_farm, products[0], quantity=Decimal("100"))
    root_lot.current_holder_organization_id = org_coop.organization_id
    root_lot.remaining_quantity = Decimal("10.000")

    child_lots = []
    for idx, dist_actor in enumerate([org_dist1, org_dist2, org_dist3], start=1):
        child = Lot(
            organization_id=org_coop.organization_id,
            current_holder_organization_id=dist_actor.organization_id,
            name=f"Lô phân phối nhánh {idx}",
            lot_code=f"LDIST{idx}{uuid4().hex[:6].upper()}",
            product_id=products[0].id,
            harvested_on=date(2026, 10, 5),
            quantity=Decimal("30.000"),
            remaining_quantity=Decimal("30.000"),
            status="active",
        )
        admin_session.add(child)
        admin_session.flush()
        admin_session.add(
            LotRelation(
                organization_id=org_coop.organization_id,
                parent_lot_id=root_lot.id,
                child_lot_id=child.id,
                quantity=Decimal("30.000"),
                operation="split",
            )
        )
        child_lots.append(child)
    admin_session.commit()

    async with (
        client() as inspector_api,
        client() as farm_api,
        client() as coop_api,
        client() as dist1_api,
        client() as dist2_api,
        client() as dist3_api,
        client() as unrelated_api,
    ):
        await login(inspector_api, inspector)
        await login(farm_api, org_farm)
        await login(coop_api, org_coop)
        await login(dist1_api, org_dist1)
        await login(dist2_api, org_dist2)
        await login(dist3_api, org_dist3)
        await login(unrelated_api, unrelated_org)

        # Inspector opens recall on root_lot
        open_res = await inspector_api.post(
            "/api/v1/recalls/",
            json={
                "lot_id": str(root_lot.id),
                "reason": "Phát hiện vi khuẩn Listeria monocytogenes vượt giới hạn cho phép.",
            },
        )
        assert open_res.status_code == 201, open_res.text
        recall = open_res.json()
        recall_id = recall["id"]

        assert recall["status"] == "open"
        assert recall["total_organizations_count"] == 5
        assert recall["confirmed_organizations_count"] == 0
        assert recall["progress_text"] == "0/5"
        assert len(recall["pending_organizations"]) == 5

        # N3-55 AC1: Distributor 1 logs in and checks recall notifications -> sees alert with its affected lot
        notif_res = await dist1_api.get("/api/v1/recalls/notifications")
        assert notif_res.status_code == 200, notif_res.text
        notifs = notif_res.json()
        my_notif = next((n for n in notifs if n["recall_id"] == recall_id), None)
        assert my_notif is not None
        assert my_notif["handling_status"] == "pending"
        assert my_notif["progress_text"] == "0/5"
        my_lot_ids = {item["id"] for item in my_notif["affected_lots"]}
        assert str(child_lots[0].id) in my_lot_ids

        # Unrelated organization sees no notification for this recall and gets 403/404 when trying to confirm or view
        unrelated_notifs = (
            await unrelated_api.get("/api/v1/recalls/notifications")
        ).json()
        assert all(n["recall_id"] != recall_id for n in unrelated_notifs)
        unrelated_confirm = await unrelated_api.post(
            f"/api/v1/recalls/{recall_id}/confirm",
            json={"note": "Cố tình xác nhận dù không liên quan."},
        )
        assert unrelated_confirm.status_code in {403, 404}

        # N3-55 AC2 & N3-52 AC1: 3 out of 5 organizations confirm handling
        for api_client, note_text in [
            (farm_api, "Trang trại đã khoanh vùng nguồn thu hoạch gốc."),
            (coop_api, "HTX đã phong tỏa 10kg tồn kho còn lại tại trạm sơ chế."),
            (dist1_api, "Nhà phân phối 1 đã gom đủ 30kg khỏi kệ siêu thị."),
        ]:
            conf_res = await api_client.post(
                f"/api/v1/recalls/{recall_id}/confirm",
                json={"note": note_text},
            )
            assert conf_res.status_code == 200, conf_res.text

        # View recall order: progress must be 3/5, status still 'open', and 2 pending organizations listed
        mid_res = await inspector_api.get(f"/api/v1/recalls/{recall_id}")
        assert mid_res.status_code == 200, mid_res.text
        mid = mid_res.json()
        assert mid["status"] == "open"
        assert mid["total_organizations_count"] == 5
        assert mid["confirmed_organizations_count"] == 3
        assert mid["progress_text"] == "3/5"
        assert len(mid["pending_organizations"]) == 2
        assert len(mid["confirmed_organizations"]) == 3

        # Verify N3-55 AC3: Dist 2 and Dist 3 are shown as 'pending', while Dist 1 is 'confirmed' with timestamp & note
        progress_by_org = {
            p["organization_id"]: p for p in mid["organizations_progress"]
        }
        assert progress_by_org[str(org_dist1.organization_id)]["status"] == "confirmed"
        assert (
            progress_by_org[str(org_dist1.organization_id)]["note"]
            == "Nhà phân phối 1 đã gom đủ 30kg khỏi kệ siêu thị."
        )
        assert (
            progress_by_org[str(org_dist1.organization_id)]["confirmed_at"] is not None
        )
        assert progress_by_org[str(org_dist2.organization_id)]["status"] == "pending"
        assert progress_by_org[str(org_dist3.organization_id)]["status"] == "pending"

        # Verify N3-55 Non-functional (append-only): Dist 1 cannot overwrite or re-confirm its confirmation
        dup_res = await dist1_api.post(
            f"/api/v1/recalls/{recall_id}/confirm",
            json={"note": "Thử ghi đè xác nhận lần 2."},
        )
        assert dup_res.status_code == 409, dup_res.text

        # Also verify DB trigger blocks UPDATE and DELETE on recall_confirmations
        with pytest.raises(Exception) as db_err:
            with admin_session.begin_nested():
                admin_session.execute(
                    text("UPDATE recall_confirmations SET note = 'hacked'")
                )
        assert "append-only" in str(db_err.value) or "bất biến" in str(db_err.value)

        with pytest.raises(Exception) as db_del_err:
            with admin_session.begin_nested():
                admin_session.execute(text("DELETE FROM recall_confirmations"))
        assert "append-only" in str(db_del_err.value) or "bất biến" in str(
            db_del_err.value
        )

        # Organization 4 (Dist 2) confirms -> 4/5, still open
        res4 = await dist2_api.post(
            f"/api/v1/recalls/{recall_id}/confirm",
            json={"note": "Nhà phân phối 2 đã cách ly toàn bộ 30kg lô nhánh 2."},
        )
        assert res4.status_code == 200, res4.text
        assert res4.json()["progress_text"] == "4/5"
        assert res4.json()["status"] == "open"

        # N3-52 AC2: Organization 5 (the last remaining organization, Dist 3) confirms ->
        # Recall order automatically transitions to 'completed' and records 'recall_completed' event!
        res5 = await dist3_api.post(
            f"/api/v1/recalls/{recall_id}/confirm",
            json={"note": "Nhà phân phối 3 đã thu hồi xong 30kg lô nhánh 3."},
        )
        assert res5.status_code == 200, res5.text
        completed_data = res5.json()
        assert completed_data["progress_text"] == "5/5"
        assert completed_data["confirmed_organizations_count"] == 5
        assert completed_data["pending_organizations"] == []
        assert completed_data["status"] == "completed"
        assert completed_data["completed_at"] is not None

        # N3-52 Non-functional: Completed recall order remains viewable in list and detail endpoints
        completed_list = (
            await inspector_api.get("/api/v1/recalls/?status_filter=completed")
        ).json()
        assert any(r["id"] == recall_id for r in completed_list)

        completed_detail = await dist3_api.get(f"/api/v1/recalls/{recall_id}")
        assert completed_detail.status_code == 200
        assert completed_detail.json()["status"] == "completed"

        # Verify immutable event history on root_lot has recall_opened and recall_completed with valid hash chain
        history_res = await inspector_api.get(
            f"/api/v1/events/lots/{root_lot.id}/history"
        )
        assert history_res.status_code == 200, history_res.text
        history = history_res.json()
        assert history["integrity"]["valid"] is True
        event_types = [e["event_type"] for e in history["events"]]
        assert "recall_opened" in event_types
        assert "recall_completed" in event_types
