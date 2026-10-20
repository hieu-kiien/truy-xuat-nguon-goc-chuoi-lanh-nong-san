"""Integration test suite for N3-62: per-product cold chain thresholds and delay.

AC: Mỗi sản phẩm có ngưỡng trên, ngưỡng dưới và độ trễ; chuyến chở nhiều sản
phẩm áp ngưỡng chặt nhất; đổi cấu hình không tính lại vi phạm đã ghi.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select, update

from app.models.product import Product
from app.models.shipment import Shipment
from app.schemas.cold_chain_config import ProductColdChainConfigUpsert
from app.services.cold_chain_detector import detect_temperature_violations
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login

lineage_products = fixtures.lineage_products


def _configure(
    api, product_id: str, *, min_temp: float, max_temp: float, delay_minutes: int
):
    return api.put(
        f"/api/v1/products/{product_id}/cold-chain-config",
        json={
            "min_temp_celsius": min_temp,
            "max_temp_celsius": max_temp,
            "delay_minutes": delay_minutes,
        },
    )


def test_cold_chain_config_schema_validation():
    """Schema guards: lower bound must stay below upper bound, delay bounded."""
    valid = ProductColdChainConfigUpsert(
        min_temp_celsius=Decimal("2"), max_temp_celsius=Decimal("8"), delay_minutes=30
    )
    assert valid.delay_minutes == 30

    with pytest.raises(ValidationError):
        ProductColdChainConfigUpsert(
            min_temp_celsius=Decimal("8"),
            max_temp_celsius=Decimal("2"),
            delay_minutes=30,
        )

    with pytest.raises(ValidationError):
        ProductColdChainConfigUpsert(
            min_temp_celsius=Decimal("2"),
            max_temp_celsius=Decimal("8"),
            delay_minutes=0,
        )

    with pytest.raises(ValidationError):
        ProductColdChainConfigUpsert(
            min_temp_celsius=Decimal("-60"),
            max_temp_celsius=Decimal("8"),
            delay_minutes=30,
        )


@pytest.mark.asyncio
async def test_system_admin_configures_thresholds_and_others_are_readonly(
    request, admin_session
):
    """Only system_admin writes product thresholds; any member may read them."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    admin = identities(role="system_admin", organization_type="administration")
    transporter = identities(role="transporter", organization_type="transport")

    async with client() as api:
        await login(api, admin)

        # Unconfigured product reports 404 before any threshold exists
        res = await api.get(f"/api/v1/products/{products[1].id}/cold-chain-config")
        assert res.status_code == 404, res.text

        res = await _configure(
            api, str(products[0].id), min_temp=2, max_temp=8, delay_minutes=30
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["product_id"] == str(products[0].id)
        assert data["product_name"] == products[0].name
        assert Decimal(data["min_temp_celsius"]) == Decimal("2")
        assert Decimal(data["max_temp_celsius"]) == Decimal("8")
        assert data["delay_minutes"] == 30

        # Invalid payload (min >= max) is rejected
        res = await _configure(
            api, str(products[0].id), min_temp=9, max_temp=1, delay_minutes=10
        )
        assert res.status_code == 422, res.text

        # Unknown product reports 404
        res = await _configure(
            api, str(uuid4()), min_temp=2, max_temp=8, delay_minutes=30
        )
        assert res.status_code == 404, res.text

    # A non-admin member may read but never write
    async with client() as api:
        await login(api, transporter)
        res = await api.get(f"/api/v1/products/{products[0].id}/cold-chain-config")
        assert res.status_code == 200, res.text

        res = await _configure(
            api, str(products[0].id), min_temp=1, max_temp=9, delay_minutes=5
        )
        assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_shipment_applies_strictest_limits_across_products(
    request, admin_session
):
    """A trip carrying several products applies the strictest thresholds/delay."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    admin = identities(role="system_admin", organization_type="administration")
    transporter = identities(role="transporter", organization_type="transport")

    # Sản phẩm rộng (vd. thịt sơ chế): 0..10 độ, độ trễ 30 phút
    async with client() as api:
        await login(api, admin)
        res = await _configure(
            api, str(products[0].id), min_temp=0, max_temp=10, delay_minutes=30
        )
        assert res.status_code == 200, res.text
        # Sản phẩm hẹp (vd. rau lá): 2..8 độ, độ trễ 10 phút
        res = await _configure(
            api, str(products[1].id), min_temp=2, max_temp=8, delay_minutes=10
        )
        assert res.status_code == 200, res.text

    lot_wide = add_lot(admin_session, transporter, products[0], quantity="20.000")
    lot_narrow = add_lot(admin_session, transporter, products[1], quantity="15.000")
    container_code = f"RF-{uuid4().hex[:8].upper()}"

    # 9.5 độ trong 20 phút: vượt ngưỡng chặt (8 độ, trễ 10 phút) nhưng vẫn
    # "an toàn" theo cấu hình rộng một mình (0..10 độ, trễ 30 phút).
    readings = [
        {"recorded_at": f"2026-10-18T09:{minute:02d}:00Z", "temperature_celsius": 9.5}
        for minute in (0, 5, 10, 15, 20)
    ]

    async with client() as api:
        await login(api, transporter)
        res = await api.post(
            "/api/v1/shipments/",
            json={
                "container_code": container_code,
                "lot_ids": [str(lot_wide.id), str(lot_narrow.id)],
            },
        )
        assert res.status_code == 201, res.text
        shipment = res.json()
        shipment_id = shipment["id"]

        # Snapshot ngưỡng chặt nhất được chốt khi mở chuyến
        limits_res = await api.get(
            f"/api/v1/telemetry/shipments/{shipment_id}/cold-chain-limits"
        )
        assert limits_res.status_code == 200, limits_res.text
        limits = limits_res.json()
        assert Decimal(limits["min_temp_celsius"]) == Decimal("2")
        assert Decimal(limits["max_temp_celsius"]) == Decimal("8")
        assert limits["delay_minutes"] == 10
        assert limits["from_snapshot"] is True
        assert len(limits["sources"]) == 2
        assert all(source["configured"] for source in limits["sources"])

        res = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": readings},
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["violations_detected"] == 1
        assert data["violations"][0]["violation_type"] == "high_temp"
        assert data["violations"][0]["duration_minutes"] == 20.0
        assert Decimal(data["applied_limits"]["min_temp_celsius"]) == Decimal("2")
        assert Decimal(data["applied_limits"]["max_temp_celsius"]) == Decimal("8")
        assert data["applied_limits"]["delay_minutes"] == 10

    # Với riêng cấu hình rộng, chuỗi số đo trên không phải vi phạm
    permissive_only = detect_temperature_violations(
        readings, min_temp_celsius=0.0, max_temp_celsius=10.0, delay_minutes=30
    )
    assert permissive_only == []


@pytest.mark.asyncio
async def test_config_change_does_not_recompute_recorded_violations(
    request, admin_session
):
    """Changing thresholds must not change the evaluation of an open trip."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    admin = identities(role="system_admin", organization_type="administration")
    transporter = identities(role="transporter", organization_type="transport")

    async with client() as api:
        await login(api, admin)
        res = await _configure(
            api, str(products[0].id), min_temp=2, max_temp=8, delay_minutes=30
        )
        assert res.status_code == 200, res.text

    lot_first = add_lot(admin_session, transporter, products[0], quantity="20.000")
    container_code = f"RF-{uuid4().hex[:8].upper()}"
    readings = [
        {"recorded_at": "2026-10-18T10:00:00Z", "temperature_celsius": 4.0},
        *[
            {
                "recorded_at": f"2026-10-18T10:{minute:02d}:00Z",
                "temperature_celsius": 12.0,
            }
            for minute in (10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
        ],
    ]

    async with client() as api:
        await login(api, transporter)
        res = await api.post(
            "/api/v1/shipments/",
            json={"container_code": container_code, "lot_ids": [str(lot_first.id)]},
        )
        assert res.status_code == 201, res.text
        shipment_id = res.json()["id"]

        res = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": readings},
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["violations_detected"] == 1
        assert data["violations"][0]["duration_minutes"] == 45.0

    # Admin widens the product thresholds mid-transit
    async with client() as api:
        await login(api, admin)
        res = await _configure(
            api, str(products[0].id), min_temp=2, max_temp=15, delay_minutes=10
        )
        assert res.status_code == 200, res.text

    async with client() as api:
        await login(api, transporter)
        # Chuyến đang chạy vẫn giữ snapshot cũ: 2..8 độ, trễ 30 phút
        limits_res = await api.get(
            f"/api/v1/telemetry/shipments/{shipment_id}/cold-chain-limits"
        )
        assert limits_res.status_code == 200, limits_res.text
        limits = limits_res.json()
        assert Decimal(limits["max_temp_celsius"]) == Decimal("8")
        assert limits["delay_minutes"] == 30
        assert limits["from_snapshot"] is True

        # Vi phạm đã ghi vẫn được tính với ngưỡng cũ
        violations_res = await api.get(
            f"/api/v1/telemetry/shipments/{shipment_id}/violations"
        )
        assert violations_res.status_code == 200, violations_res.text
        violations = violations_res.json()
        assert len(violations) == 1
        assert violations[0]["duration_minutes"] == 45.0

    # A brand-new trip picks up the new configuration
    lot_second = add_lot(admin_session, transporter, products[0], quantity="10.000")
    async with client() as api:
        await login(api, transporter)
        res = await api.post(
            "/api/v1/shipments/",
            json={
                "container_code": f"RF-{uuid4().hex[:8].upper()}",
                "lot_ids": [str(lot_second.id)],
            },
        )
        assert res.status_code == 201, res.text
        new_shipment_id = res.json()["id"]

        limits_res = await api.get(
            f"/api/v1/telemetry/shipments/{new_shipment_id}/cold-chain-limits"
        )
        assert limits_res.status_code == 200, limits_res.text
        new_limits = limits_res.json()
        assert Decimal(new_limits["max_temp_celsius"]) == Decimal("15")
        assert new_limits["delay_minutes"] == 10


@pytest.mark.asyncio
async def test_unconfigured_products_fall_back_to_default_limits(
    request, admin_session
):
    """Trips with unconfigured products keep the documented 2-8C / 30m defaults."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    lot = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-{uuid4().hex[:8].upper()}"

    async with client() as api:
        await login(api, transporter)
        res = await api.post(
            "/api/v1/shipments/",
            json={"container_code": container_code, "lot_ids": [str(lot.id)]},
        )
        assert res.status_code == 201, res.text
        shipment_id = res.json()["id"]

        limits_res = await api.get(
            f"/api/v1/telemetry/shipments/{shipment_id}/cold-chain-limits"
        )
        assert limits_res.status_code == 200, limits_res.text
        limits = limits_res.json()
        assert Decimal(limits["min_temp_celsius"]) == Decimal("2")
        assert Decimal(limits["max_temp_celsius"]) == Decimal("8")
        assert limits["delay_minutes"] == 30
        assert len(limits["sources"]) == 1
        assert limits["sources"][0]["configured"] is False


@pytest.mark.asyncio
async def test_legacy_shipment_resolves_live_then_persists_snapshot_on_ingest(
    request, admin_session
):
    """Trips without a snapshot (opened pre-N3-62) resolve once, then freeze."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    admin = identities(role="system_admin", organization_type="administration")
    transporter = identities(role="transporter", organization_type="transport")

    async with client() as api:
        await login(api, admin)
        res = await _configure(
            api, str(products[0].id), min_temp=1, max_temp=4, delay_minutes=15
        )
        assert res.status_code == 200, res.text

    lot = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-{uuid4().hex[:8].upper()}"

    async with client() as api:
        await login(api, transporter)
        res = await api.post(
            "/api/v1/shipments/",
            json={"container_code": container_code, "lot_ids": [str(lot.id)]},
        )
        assert res.status_code == 201, res.text
        shipment_id = res.json()["id"]

    # Mô phỏng chuyến tồn tại trước migration N3-62: bỏ snapshot
    admin_session.execute(
        update(Shipment)
        .where(Shipment.id == shipment_id)
        .values(
            cold_chain_min_temp_celsius=None,
            cold_chain_max_temp_celsius=None,
            cold_chain_delay_minutes=None,
            cold_chain_config_resolved_at=None,
        )
    )
    admin_session.commit()

    async with client() as api:
        await login(api, transporter)
        # Chưa snapshot: ngưỡng được resolving "live" từ cấu hình hiện tại
        limits_res = await api.get(
            f"/api/v1/telemetry/shipments/{shipment_id}/cold-chain-limits"
        )
        assert limits_res.status_code == 200, limits_res.text
        limits = limits_res.json()
        assert Decimal(limits["min_temp_celsius"]) == Decimal("1")
        assert Decimal(limits["delay_minutes"]) == 15
        assert limits["from_snapshot"] is False

        # Nạp số đo lần đầu chốt snapshot cho chuyến
        readings = [
            {"recorded_at": "2026-10-18T11:00:00Z", "temperature_celsius": 3.0},
            {"recorded_at": "2026-10-18T11:05:00Z", "temperature_celsius": 6.0},
        ]
        res = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": readings},
        )
        assert res.status_code == 201, res.text
        assert res.json()["applied_limits"]["from_snapshot"] is True

    snapshot = admin_session.scalar(select(Shipment).where(Shipment.id == shipment_id))
    assert snapshot is not None
    assert snapshot.cold_chain_min_temp_celsius == Decimal("1")
    assert snapshot.cold_chain_max_temp_celsius == Decimal("4")
    assert snapshot.cold_chain_delay_minutes == 15
    assert snapshot.cold_chain_config_resolved_at is not None


@pytest.mark.asyncio
async def test_shipment_lots_products_resolve_to_configured_profile(
    request, admin_session
):
    """A lot without product_id contributes nothing; configured products show up."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    admin = identities(role="system_admin", organization_type="administration")
    transporter = identities(role="transporter", organization_type="transport")

    async with client() as api:
        await login(api, admin)
        res = await _configure(
            api, str(products[1].id), min_temp=2, max_temp=8, delay_minutes=10
        )
        assert res.status_code == 200, res.text

    unconfigured = Product(name=f"n362-bare-{uuid4().hex}", unit="kg")
    admin_session.add(unconfigured)
    admin_session.commit()

    lot_with_product = add_lot(admin_session, transporter, products[1])
    lot_without_product = add_lot(admin_session, transporter, unconfigured)

    async with client() as api:
        await login(api, transporter)
        res = await api.post(
            "/api/v1/shipments/",
            json={
                "container_code": f"RF-{uuid4().hex[:8].upper()}",
                "lot_ids": [str(lot_with_product.id), str(lot_without_product.id)],
            },
        )
        assert res.status_code == 201, res.text
        limits_res = await api.get(
            f"/api/v1/telemetry/shipments/{res.json()['id']}/cold-chain-limits"
        )
        assert limits_res.status_code == 200, limits_res.text
        limits = limits_res.json()
        # Cấu hình chặt nhất: 2..8 độ, trễ 10 phút
        assert Decimal(limits["max_temp_celsius"]) == Decimal("8")
        assert limits["delay_minutes"] == 10
        configured_sources = [s for s in limits["sources"] if s["configured"]]
        assert len(configured_sources) == 1
        assert configured_sources[0]["product_id"] == str(products[1].id)
