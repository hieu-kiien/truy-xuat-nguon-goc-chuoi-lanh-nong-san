"""Integration test suite for N3-60: Cold chain sensor simulation and S-41 telemetry ingestion."""

import time
from uuid import uuid4

import pytest

from scripts.simulate_sensor import load_scenarios, run_scenario_simulation
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login

lineage_products = fixtures.lineage_products


async def _open_test_shipment(api, container_code: str, lot_id: str) -> dict:
    """Helper to open an in_transit shipment via authenticated API."""
    res = await api.post(
        "/api/v1/shipments/",
        json={"container_code": container_code, "lot_ids": [lot_id]},
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_oracle_scenarios_file_integrity():
    """Verify cold_chain_scenarios.json contains at least 5 standard scenarios with valid structure."""
    scenarios = load_scenarios()
    assert len(scenarios) >= 5

    scenario_ids = {s["id"] for s in scenarios}
    assert "scenario_1_normal" in scenario_ids
    assert "scenario_2_short_spike" in scenario_ids
    assert "scenario_3_sustained_violation" in scenario_ids
    assert "scenario_4_gap_merged" in scenario_ids
    assert "scenario_5_midnight_excursion" in scenario_ids

    for sc in scenarios:
        assert "container_code" in sc
        assert "readings" in sc
        assert len(sc["readings"]) > 0
        assert "expected" in sc
        assert "violation_count" in sc["expected"]


def test_offline_simulation_all_five_scenarios():
    """Verify that all 5 scenarios pass the TDD oracle test offline in milliseconds."""
    scenarios = load_scenarios()
    for sc in scenarios:
        res = run_scenario_simulation(scenario=sc, speedup=0)
        assert res["passed"] is True
        assert res["detected_violations"] == res["expected_violations"]


@pytest.mark.asyncio
async def test_api_ingest_readings_and_sliding_window_violations(
    request, admin_session
):
    """Verify S-41 endpoint ingests readings, enforces tenant ownership, and computes violations."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    lot = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-{uuid4().hex[:8].upper()}"

    async with client() as api:
        await login(api, transporter)

        # 1. Open active shipment
        shipment = await _open_test_shipment(api, container_code, str(lot.id))
        shipment_id = shipment["id"]
        assert shipment["status"] == "in_transit"

        # 2. Ingest telemetry readings with 45m continuous violation (08:10 to 08:55)
        readings = [
            {"recorded_at": "2026-10-18T08:00:00Z", "temperature_celsius": 4.0},
            {"recorded_at": "2026-10-18T08:05:00Z", "temperature_celsius": 4.2},
            {"recorded_at": "2026-10-18T08:10:00Z", "temperature_celsius": 11.5},
            {"recorded_at": "2026-10-18T08:15:00Z", "temperature_celsius": 12.0},
            {"recorded_at": "2026-10-18T08:20:00Z", "temperature_celsius": 12.5},
            {"recorded_at": "2026-10-18T08:25:00Z", "temperature_celsius": 14.0},
            {"recorded_at": "2026-10-18T08:30:00Z", "temperature_celsius": 13.5},
            {"recorded_at": "2026-10-18T08:35:00Z", "temperature_celsius": 13.0},
            {"recorded_at": "2026-10-18T08:40:00Z", "temperature_celsius": 12.8},
            {"recorded_at": "2026-10-18T08:45:00Z", "temperature_celsius": 12.5},
            {"recorded_at": "2026-10-18T08:50:00Z", "temperature_celsius": 12.2},
            {"recorded_at": "2026-10-18T08:55:00Z", "temperature_celsius": 12.0},
            {"recorded_at": "2026-10-18T09:00:00Z", "temperature_celsius": 4.0},
        ]
        res = await api.post(
            "/api/v1/telemetry/readings",
            json={
                "container_code": container_code,
                "readings": readings,
            },
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["container_code"] == container_code
        assert data["ingested_count"] == 13
        assert data["duplicate_count"] == 0
        assert data["violations_detected"] == 1
        assert len(data["violations"]) == 1
        assert data["violations"][0]["violation_type"] == "high_temp"
        assert data["violations"][0]["duration_minutes"] == 45.0

        # 3. Query readings endpoint
        readings_res = await api.get(
            f"/api/v1/telemetry/shipments/{shipment_id}/readings"
        )
        assert readings_res.status_code == 200
        assert len(readings_res.json()) == 13

        # 4. Query violations endpoint
        violations_res = await api.get(
            f"/api/v1/telemetry/shipments/{shipment_id}/violations"
        )
        assert violations_res.status_code == 200
        assert len(violations_res.json()) == 1


@pytest.mark.asyncio
async def test_api_ingest_all_five_scenarios_end_to_end(request, admin_session):
    """End-to-end verification of all 5 scenarios through S-41 API endpoint."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    scenarios = load_scenarios()

    async with client() as api:
        await login(api, transporter)

        for sc in scenarios:
            lot = add_lot(admin_session, transporter, products[0])
            container_code = f"RF-{uuid4().hex[:8].upper()}"

            # Open shipment
            await _open_test_shipment(api, container_code, str(lot.id))

            # Ingest readings
            res = await api.post(
                "/api/v1/telemetry/readings",
                json={
                    "container_code": container_code,
                    "readings": sc["readings"],
                },
            )
            assert res.status_code == 201, res.text
            data = res.json()
            expected_count = sc["expected"]["violation_count"]
            assert data["violations_detected"] == expected_count, (
                f"Scenario {sc['id']} expected {expected_count} violations, got {data['violations_detected']}"
            )


@pytest.mark.asyncio
async def test_telemetry_idempotency_duplicate_readings(request, admin_session):
    """Verify re-sending same timestamps does not crash or double-count (ON CONFLICT DO NOTHING)."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    lot = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-{uuid4().hex[:8].upper()}"

    batch = [
        {"recorded_at": "2026-10-18T10:00:00Z", "temperature_celsius": 4.5},
        {"recorded_at": "2026-10-18T10:05:00Z", "temperature_celsius": 4.7},
    ]

    async with client() as api:
        await login(api, transporter)
        await _open_test_shipment(api, container_code, str(lot.id))

        # First ingestion
        res1 = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": batch},
        )
        assert res1.status_code == 201
        assert res1.json()["ingested_count"] == 2
        assert res1.json()["duplicate_count"] == 0

        # Duplicate ingestion
        res2 = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": batch},
        )
        assert res2.status_code == 201
        assert res2.json()["ingested_count"] == 0
        assert res2.json()["duplicate_count"] == 2


@pytest.mark.asyncio
async def test_cannot_ingest_readings_to_nonexistent_or_completed_shipment(
    request, admin_session
):
    """Verify ingestion is rejected with 404 if shipment does not exist or has completed."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    lot = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-{uuid4().hex[:8].upper()}"

    async with client() as api:
        await login(api, transporter)
        shipment = await _open_test_shipment(api, container_code, str(lot.id))
        shipment_id = shipment["id"]

        # Complete shipment
        await api.post(f"/api/v1/shipments/{shipment_id}/complete")

        # Ingestion after completion -> 404
        res = await api.post(
            "/api/v1/telemetry/readings",
            json={
                "container_code": container_code,
                "readings": [
                    {"recorded_at": "2026-10-18T12:00:00Z", "temperature_celsius": 4.0}
                ],
            },
        )
        assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_cannot_ingest_with_unauthorized_organization(request, admin_session):
    """Carrier organization guard: another organization cannot ingest readings for other carrier's container."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter_a = identities(role="transporter", organization_type="transport")
    transporter_b = identities(role="transporter", organization_type="transport")
    lot = add_lot(admin_session, transporter_a, products[0])
    container_code = f"RF-{uuid4().hex[:8].upper()}"

    async with client() as api:
        # Carrier A opens shipment
        await login(api, transporter_a)
        await _open_test_shipment(api, container_code, str(lot.id))

    async with client() as api:
        # Carrier B attempts ingestion -> 403 Forbidden
        await login(api, transporter_b)
        res = await api.post(
            "/api/v1/telemetry/readings",
            json={
                "container_code": container_code,
                "readings": [
                    {"recorded_at": "2026-10-18T10:00:00Z", "temperature_celsius": 4.0}
                ],
            },
        )
        assert res.status_code in {403, 404}, res.text


def test_nfr_simulation_speed_requirement():
    """NFR: Verify script runs faster than real-time (all 5 scenarios complete in < 1 second)."""
    t0 = time.perf_counter()
    scenarios = load_scenarios()
    for sc in scenarios:
        res = run_scenario_simulation(scenario=sc, speedup=0)
        assert res["passed"] is True
    total_time = time.perf_counter() - t0
    assert total_time < 1.0, f"Expected < 1.0s, took {total_time:.3f}s"
