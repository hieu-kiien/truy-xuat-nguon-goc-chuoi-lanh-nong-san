"""Provenance visibility must not expose sibling stock or grant mutation rights."""

import pytest

from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login, split_body

lineage = fixtures.lineage
lineage_products = fixtures.lineage_products


@pytest.mark.asyncio
async def test_receiver_of_merged_child_cannot_read_siblings_or_mutate_sources(
    lineage, admin_session
):
    owner, products, identities = lineage
    receiver = identities(role="distributor", organization_type="distribution")
    roots = [add_lot(admin_session, owner, products[0]) for _ in range(2)]
    async with client() as source_api, client() as receiver_api:
        await login(source_api, owner)
        await login(receiver_api, receiver)
        split = await source_api.post(
            f"/api/v1/lots/{roots[0].id}/split", json=split_body("10", "10")
        )
        assert split.status_code == 201, split.text
        first, sibling = split.json()["children"]
        merged = await source_api.post(
            "/api/v1/lots/merge",
            json={
                "name": "Mixed sources",
                "parents": [
                    {"lot_id": first["id"], "quantity": "10"},
                    {"lot_id": str(roots[1].id), "quantity": "5"},
                ],
            },
        )
        assert merged.status_code == 201, merged.text
        merged_id = merged.json()["id"]
        transfer = await source_api.post(
            "/api/v1/handovers/",
            json={
                "lot_id": merged_id,
                "to_organization_id": str(receiver.organization_id),
            },
        )
        assert transfer.status_code == 201, transfer.text
        accepted = await receiver_api.post(
            f"/api/v1/handovers/{transfer.json()['id']}/accept"
        )
        assert accepted.status_code == 200, accepted.text
        former_graph = await source_api.get(f"/api/v1/lots/{merged_id}/lineage")
        assert former_graph.status_code == 200, former_graph.text
        former_node = next(
            node for node in former_graph.json()["nodes"] if node["id"] == merged_id
        )
        assert former_node["historical_only"]
        assert former_node["remaining_quantity"] is None
        assert former_node["current_holder_organization_id"] is None
        former_history = await source_api.get(
            f"/api/v1/events/lots/{merged_id}/history"
        )
        assert former_history.status_code == 200, former_history.text
        assert former_history.json()["events"][-1]["event_type"] == "handover_accepted"
        trace = await receiver_api.get(f"/api/v1/lots/{merged_id}/lineage")
        assert trace.status_code == 200, trace.text
        assert set(trace.json()["roots"]) == {str(root.id) for root in roots}
        assert sibling["id"] not in {node["id"] for node in trace.json()["nodes"]}
        history = await receiver_api.get(f"/api/v1/events/lots/{roots[0].id}/history")
        assert history.status_code == 200
        assert (
            sibling["id"] not in history.text
            and sibling["lot_code"] not in history.text
        )
        assert history.json()["integrity"]["valid"]
        assert all(entry["payload_redacted"] for entry in history.json()["events"])
        event_list = await receiver_api.get(
            "/api/v1/events/", params={"lot_id": str(roots[0].id)}
        )
        assert event_list.status_code == 200
        assert (
            sibling["id"] not in event_list.text
            and sibling["lot_code"] not in event_list.text
        )
        for entry in history.json()["events"]:
            event = await receiver_api.get(f"/api/v1/events/{entry['id']}")
            assert event.status_code == 200
            assert (
                sibling["id"] not in event.text
                and sibling["lot_code"] not in event.text
            )
        for resource in [
            f"/api/v1/lots/{sibling['id']}",
            f"/api/v1/events/lots/{sibling['id']}/history",
        ]:
            assert (await receiver_api.get(resource)).status_code == 403
        downstream = await receiver_api.get(
            f"/api/v1/lots/{roots[0].id}/lineage?direction=descendants"
        )
        assert downstream.status_code == 200, downstream.text
        assert sibling["id"] not in {node["id"] for node in downstream.json()["nodes"]}
        denied_event = await receiver_api.post(
            "/api/v1/events/",
            json={
                "lot_id": str(roots[0].id),
                "event_type": "forged_from_provenance",
            },
        )
        assert denied_event.status_code == 403, denied_event.text
        denied_split = await receiver_api.post(
            f"/api/v1/lots/{roots[0].id}/split", json=split_body("1")
        )
        assert denied_split.status_code == 403, denied_split.text
        denied_handover = await receiver_api.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(roots[0].id),
                "to_organization_id": str(owner.organization_id),
            },
        )
        assert denied_handover.status_code == 403, denied_handover.text
    for root, remaining in zip(roots, ["20", "35"], strict=True):
        fixtures.assert_mass(admin_session, root.id, remaining)


@pytest.mark.asyncio
async def test_multi_hop_ancestor_history_handles_hidden_intermediate_organization(
    lineage, admin_session
):
    owner, products, identities = lineage
    middle = identities(role="cooperative", organization_type="cooperative")
    first_dist = identities(role="distributor", organization_type="distribution")
    receiver = identities(role="distributor", organization_type="distribution")
    root = add_lot(admin_session, owner, products[0])
    async with (
        client() as origin,
        client() as hub,
        client() as depot,
        client() as destination,
    ):
        for api, actor in [
            (origin, owner),
            (hub, middle),
            (depot, first_dist),
            (destination, receiver),
        ]:
            await login(api, actor)

        async def transfer(sender, recipient, actor, identifier):
            handover = await sender.post(
                "/api/v1/handovers/",
                json={
                    "lot_id": identifier,
                    "to_organization_id": str(actor.organization_id),
                },
            )
            assert handover.status_code == 201, handover.text
            accepted = await recipient.post(
                "/api/v1/handovers/" + handover.json()["id"] + "/accept"
            )
            assert accepted.status_code == 200, accepted.text

        await transfer(origin, hub, middle, str(root.id))
        recorded = await hub.post(
            "/api/v1/events/",
            json={"lot_id": str(root.id), "event_type": "cold_storage"},
        )
        assert recorded.status_code == 201, recorded.text
        await transfer(hub, depot, first_dist, str(root.id))
        split = await depot.post(f"/api/v1/lots/{root.id}/split", json=split_body("10"))
        assert split.status_code == 201, split.text
        await transfer(depot, destination, receiver, split.json()["children"][0]["id"])
        history = await destination.get(f"/api/v1/events/lots/{root.id}/history")
        assert history.status_code == 200, history.text
        assert history.json()["integrity"]["valid"]
        assert all(entry["organization_name"] for entry in history.json()["events"])
