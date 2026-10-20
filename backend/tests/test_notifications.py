"""Integration test suite for N3-56: the in-app notification centre.

The notification centre shows the three things that still need a user to act:
a handover waiting for confirmation, a recall that touches their lots and a
cold chain excursion on a lot they hold.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.main import app
from app.models.farm import Farm
from app.models.lot import Lot
from app.models.notification import Notification
from app.models.product import Product
from app.models.shipment import Shipment, ShipmentLot
from app.models.telemetry import ColdChainViolation
from app.services import event_service
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


def _seed_lot(
    db: Session, identity: IdentityFixture, *, lot_code: str | None = None
) -> Lot:
    farm = Farm(
        organization_id=identity.organization_id,
        name=f"notify-farm-{uuid4().hex[:8]}",
        area_ha=Decimal("1.0000"),
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
    )
    product = Product(name=f"notify-product-{uuid4().hex[:8]}", unit="kg")
    db.add_all([farm, product])
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        name="Lô thông báo",
        lot_code=lot_code or uuid4().hex[:8].upper(),
        product_id=product.id,
        harvested_on=date.today(),
        quantity=Decimal("10.000"),
        remaining_quantity=Decimal("10.000"),
        status="active",
    )
    db.add(lot)
    db.commit()
    return lot


def _seed_violation(
    db: Session,
    carrier: IdentityFixture,
    holder: IdentityFixture,
    lot: Lot,
) -> ColdChainViolation:
    """Record a cold chain excursion on a shipment that carries the lot."""
    shipment = Shipment(
        shipment_code=f"SH-{uuid4().hex[:8].upper()}",
        organization_id=carrier.organization_id,
        created_by_user_id=carrier.user_id,
        container_code=f"RF-{uuid4().hex[:6].upper()}",
        status="completed",
        created_at=datetime.now(UTC) - timedelta(hours=2),
        completed_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db.add(shipment)
    db.flush()
    db.add(ShipmentLot(shipment_id=shipment.id, lot_id=lot.id))
    started_at = datetime.now(UTC) - timedelta(hours=2)
    violation = ColdChainViolation(
        shipment_id=shipment.id,
        violation_type="high_temp",
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=45),
        duration_minutes=Decimal("45.00"),
        peak_temperature_celsius=Decimal("12.50"),
        is_settled=True,
    )
    db.add(violation)
    db.commit()

    # N3-63 appends the excursion to the chain of every lot on the shipment.
    holder_principal = Principal(
        user_id=holder.user_id,
        email=holder.email,
        full_name="Integration test user",
        organization_id=holder.organization_id,
        organization_name="Integration holder",
        organization_type="farm",
        role="grower",
    )
    event_service.append_event(
        db,
        holder_principal,
        lot.id,
        event_type="cold_chain_violation",
        payload={
            "shipment_id": str(shipment.id),
            "shipment_code": shipment.shipment_code,
            "container_code": shipment.container_code,
            "reefer_container_code": shipment.container_code,
            "violation_type": "high_temp",
            "started_at": started_at.isoformat(),
            "ended_at": (started_at + timedelta(minutes=45)).isoformat(),
            "duration_minutes": 45.0,
            "peak_temperature_celsius": 12.5,
        },
    )
    db.commit()
    return violation


@pytest.mark.asyncio
async def test_n3_56_pending_handover_reaches_the_receiver(
    admin_session: Session, identity_factory
):
    """A handover waiting for confirmation shows up in the receiver's centre."""
    sender = identity_factory(role="grower", organization_type="farm")
    receiver = identity_factory(
        role="organization_admin", organization_type="cooperative"
    )
    lot = _seed_lot(admin_session, sender)

    async with (
        _client() as sender_client,
        _client() as receiver_client,
    ):
        await _login(sender_client, sender)
        await _login(receiver_client, receiver)

        created = await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(lot.id),
                "to_organization_id": str(receiver.organization_id),
                "note": "Giao tại kho trung tâm",
            },
        )
        assert created.status_code == 201, created.text

        response = await receiver_client.get("/api/v1/notifications")
        assert response.status_code == 200, response.text
        payload = response.json()

        assert payload["unread_count"] == 1
        assert len(payload["items"]) == 1
        item = payload["items"][0]
        assert item["kind"] == "handover_pending"
        assert item["link_path"] == "/handovers"
        assert item["read_at"] is None
        assert lot.lot_code in item["body"]

        # The sender must not see the receiver's notification.
        sender_response = await sender_client.get("/api/v1/notifications")
        assert sender_response.status_code == 200
        assert sender_response.json()["unread_count"] == 0
        assert sender_response.json()["items"] == []


@pytest.mark.asyncio
async def test_n3_56_notifications_are_not_duplicated(
    admin_session: Session, identity_factory
):
    """Loading the centre twice keeps one row per underlying item."""
    sender = identity_factory(role="grower", organization_type="farm")
    receiver = identity_factory(
        role="organization_admin", organization_type="cooperative"
    )
    lot = _seed_lot(admin_session, sender)

    async with _client() as sender_client, _client() as receiver_client:
        await _login(sender_client, sender)
        await _login(receiver_client, receiver)

        created = await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(lot.id),
                "to_organization_id": str(receiver.organization_id),
            },
        )
        assert created.status_code == 201, created.text

        first = await receiver_client.get("/api/v1/notifications")
        second = await receiver_client.get("/api/v1/notifications")
        assert first.json()["unread_count"] == 1
        assert second.json()["unread_count"] == 1
        assert len(second.json()["items"]) == 1

        rows = list(
            admin_session.scalars(
                select(Notification).where(
                    Notification.recipient_user_id == receiver.user_id
                )
            ).all()
        )
        assert len(rows) == 1
        assert rows[0].organization_id == receiver.organization_id
        assert rows[0].kind == "handover_pending"


@pytest.mark.asyncio
async def test_n3_56_marking_a_notification_read_clears_the_badge(
    admin_session: Session, identity_factory
):
    """Reading one notification updates the unread counter."""
    sender = identity_factory(role="grower", organization_type="farm")
    receiver = identity_factory(
        role="organization_admin", organization_type="cooperative"
    )
    lot = _seed_lot(admin_session, sender)

    async with _client() as sender_client, _client() as receiver_client:
        await _login(sender_client, sender)
        await _login(receiver_client, receiver)

        await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(lot.id),
                "to_organization_id": str(receiver.organization_id),
            },
        )

        listing = await receiver_client.get("/api/v1/notifications")
        notification_id = listing.json()["items"][0]["id"]

        marked = await receiver_client.post(
            f"/api/v1/notifications/{notification_id}/read"
        )
        assert marked.status_code == 200, marked.text
        assert marked.json()["read_at"] is not None

        after = await receiver_client.get("/api/v1/notifications")
        assert after.json()["unread_count"] == 0
        assert after.json()["items"][0]["read_at"] is not None


@pytest.mark.asyncio
async def test_n3_56_cold_chain_violation_on_my_lot_is_notified(
    admin_session: Session, identity_factory
):
    """An excursion recorded on a lot the caller holds raises a notification."""
    carrier = identity_factory(role="transporter", organization_type="transport")
    holder = identity_factory(role="grower", organization_type="farm")
    lot = _seed_lot(admin_session, holder)
    _seed_violation(admin_session, carrier, holder, lot)

    async with _client() as holder_client:
        await _login(holder_client, holder)
        response = await holder_client.get("/api/v1/notifications")
        assert response.status_code == 200, response.text
        payload = response.json()

        assert payload["unread_count"] == 1
        item = payload["items"][0]
        assert item["kind"] == "cold_chain_violation"
        assert item["link_path"] == f"/lots/{lot.id}"
        assert lot.lot_code in item["body"]


@pytest.mark.asyncio
async def test_n3_56_open_recall_reaches_the_affected_organization(
    admin_session: Session, identity_factory
):
    """An open recall order shows up for the organization that holds the lot."""
    inspector = identity_factory(role="inspector", organization_type="inspection")
    holder = identity_factory(role="grower", organization_type="farm")
    lot = _seed_lot(admin_session, holder)

    async with _client() as inspector_client, _client() as holder_client:
        await _login(inspector_client, inspector)
        await _login(holder_client, holder)

        opened = await inspector_client.post(
            "/api/v1/recalls/",
            json={
                "lot_id": str(lot.id),
                "reason": "Lô hàng thu hoạch đầy nghi phân định cấp kiểm tra an toàn thực phẩm.",
            },
        )
        assert opened.status_code == 201, opened.text

        response = await holder_client.get("/api/v1/notifications")
        assert response.status_code == 200, response.text
        payload = response.json()

        recalls = [
            item for item in payload["items"] if item["kind"] == "recall_affected"
        ]
        assert len(recalls) == 1
        assert recalls[0]["link_path"] == f"/lots/{lot.id}"
        assert opened.json()["recall_code"] in recalls[0]["body"]


@pytest.mark.asyncio
async def test_n3_56_mark_all_read_clears_every_notification(
    admin_session: Session, identity_factory
):
    """The read-all action empties the badge in one call."""
    sender = identity_factory(role="grower", organization_type="farm")
    receiver = identity_factory(
        role="organization_admin", organization_type="cooperative"
    )
    carrier = identity_factory(role="transporter", organization_type="transport")
    lot = _seed_lot(admin_session, sender)
    _seed_violation(admin_session, carrier, receiver, lot)

    async with _client() as sender_client, _client() as receiver_client:
        await _login(sender_client, sender)
        await _login(receiver_client, receiver)

        await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(lot.id),
                "to_organization_id": str(receiver.organization_id),
            },
        )

        before = await receiver_client.get("/api/v1/notifications")
        assert before.json()["unread_count"] >= 1

        response = await receiver_client.post("/api/v1/notifications/read-all")
        assert response.status_code == 200, response.text
        assert response.json()["updated"] >= 1

        after = await receiver_client.get("/api/v1/notifications")
        assert after.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_n3_56_notification_of_another_user_cannot_be_read(
    admin_session: Session, identity_factory
):
    """A notification belongs to its recipient only."""
    sender = identity_factory(role="grower", organization_type="farm")
    receiver = identity_factory(
        role="organization_admin", organization_type="cooperative"
    )
    outsider = identity_factory(
        role="organization_admin", organization_type="cooperative"
    )
    lot = _seed_lot(admin_session, sender)

    async with (
        _client() as sender_client,
        _client() as receiver_client,
        _client() as outsider_client,
    ):
        await _login(sender_client, sender)
        await _login(receiver_client, receiver)
        await _login(outsider_client, outsider)

        await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(lot.id),
                "to_organization_id": str(receiver.organization_id),
            },
        )

        listing = await receiver_client.get("/api/v1/notifications")
        notification_id = listing.json()["items"][0]["id"]

        response = await outsider_client.post(
            f"/api/v1/notifications/{notification_id}/read"
        )
        assert response.status_code == 404, response.text
