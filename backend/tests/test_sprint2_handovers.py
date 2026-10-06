from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.crypto import GENESIS_PREV_HASH
from app.main import app
from app.models.event import Event
from app.models.farm import Farm
from app.models.handover import Handover
from app.models.lot import Lot
from app.models.product import Product
from app.services import handover_service
from app.services.event_service import verify_event_chain
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


def _add_lot(
    db: Session,
    organization_id,
    farm_id,
    product_id,
    lot_code: str,
) -> Lot:
    lot = Lot(
        organization_id=organization_id,
        current_holder_organization_id=organization_id,
        farm_id=farm_id,
        name="Dâu tây",
        lot_code=lot_code,
        product_id=product_id,
        quantity=Decimal("12.000"),
        remaining_quantity=Decimal("12.000"),
        status="active",
    )
    db.add(lot)
    db.commit()
    return lot


@pytest.mark.asyncio
async def test_handover_accept_reject_and_custody_are_atomic(
    admin_session: Session, identity_factory, monkeypatch
):
    sender = identity_factory(role="grower", organization_type="farm")
    receiver = identity_factory(
        role="organization_admin", organization_type="cooperative"
    )
    outsider = identity_factory(role="cooperative", organization_type="cooperative")
    farm = Farm(
        organization_id=sender.organization_id,
        name=f"handover-farm-{uuid4().hex[:8]}",
        area_ha=Decimal("1.0000"),
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
    )
    product = Product(name=f"handover-product-{uuid4().hex[:8]}", unit="kg")
    admin_session.add_all([farm, product])
    admin_session.commit()
    first_lot = _add_lot(
        admin_session,
        sender.organization_id,
        farm.id,
        product.id,
        uuid4().hex[:8].upper(),
    )
    rejected_lot = _add_lot(
        admin_session,
        sender.organization_id,
        farm.id,
        product.id,
        uuid4().hex[:8].upper(),
    )

    async with _client() as sender_client, _client() as receiver_client, _client() as outsider_client:
        await _login(sender_client, sender)
        await _login(receiver_client, receiver)
        await _login(outsider_client, outsider)

        organizations = await sender_client.get("/api/v1/handovers/organizations")
        assert organizations.status_code == 200
        assert sender.organization_id not in {
            organization["id"] for organization in organizations.json()
        }

        self_handover = await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(first_lot.id),
                "to_organization_id": str(sender.organization_id),
            },
        )
        assert self_handover.status_code == 422

        created = await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(first_lot.id),
                "to_organization_id": str(receiver.organization_id),
                "note": "Giao tại kho trung tâm",
            },
        )
        assert created.status_code == 201, created.text
        handover_id = created.json()["id"]
        assert created.json()["status"] == "pending"
        assert created.json()["from_organization_name"].startswith("integration-")

        duplicate = await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(first_lot.id),
                "to_organization_id": str(receiver.organization_id),
            },
        )
        assert duplicate.status_code == 409

        append_event = handover_service.event_service.append_event

        def append_then_fail(db, principal, lot_id, **event_data):
            append_event(db, principal, lot_id, **event_data)
            raise RuntimeError("simulated failure after event append")

        receiver_principal = Principal(
            user_id=receiver.user_id,
            email=receiver.email,
            full_name="Integration test user",
            organization_id=receiver.organization_id,
            organization_name="Integration receiver",
            organization_type="cooperative",
            role="organization_admin",
        )
        with monkeypatch.context() as patcher:
            patcher.setattr(
                handover_service.event_service, "append_event", append_then_fail
            )
            with pytest.raises(RuntimeError, match="simulated failure"):
                handover_service.accept_handover(
                    admin_session, receiver_principal, UUID(handover_id)
                )

        admin_session.expire_all()
        persisted_handover = admin_session.get(Handover, UUID(handover_id))
        persisted_lot = admin_session.get(Lot, first_lot.id)
        persisted_events = list(
            admin_session.scalars(
                select(Event).where(Event.lot_id == first_lot.id)
            ).all()
        )
        assert persisted_handover is not None
        assert persisted_handover.status == "pending"
        assert persisted_lot is not None
        assert persisted_lot.current_holder_organization_id == sender.organization_id
        assert persisted_lot.status == "pending_handover"
        assert [event.event_type for event in persisted_events] == ["handover_pending"]

        incoming = await receiver_client.get("/api/v1/handovers/incoming")
        assert incoming.status_code == 200
        assert incoming.json()[0]["from_organization_name"] == created.json()[
            "from_organization_name"
        ]

        forbidden = await outsider_client.post(
            f"/api/v1/handovers/{handover_id}/accept"
        )
        assert forbidden.status_code == 403

        accepted = await receiver_client.post(
            f"/api/v1/handovers/{handover_id}/accept"
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["status"] == "accepted"
        repeated_accept = await receiver_client.post(
            f"/api/v1/handovers/{handover_id}/accept"
        )
        assert repeated_accept.status_code == 409

        receiver_lot = await receiver_client.get(f"/api/v1/lots/{first_lot.id}")
        assert receiver_lot.status_code == 200
        assert (
            receiver_lot.json()["current_holder_organization_id"]
            == str(receiver.organization_id)
        )
        sender_lot_after_accept = await sender_client.get(
            f"/api/v1/lots/{first_lot.id}"
        )
        assert sender_lot_after_accept.status_code == 403

        pending = await sender_client.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(rejected_lot.id),
                "to_organization_id": str(receiver.organization_id),
            },
        )
        assert pending.status_code == 201, pending.text
        pending_id = pending.json()["id"]
        short_reason = await receiver_client.post(
            f"/api/v1/handovers/{pending_id}/reject",
            json={"reason": "Không"},
        )
        assert short_reason.status_code == 422
        rejected = await receiver_client.post(
            f"/api/v1/handovers/{pending_id}/reject",
            json={"reason": "Thiếu chứng từ bàn giao."},
        )
        assert rejected.status_code == 200, rejected.text
        assert rejected.json()["status"] == "rejected"
        sender_lot_after_reject = await sender_client.get(
            f"/api/v1/lots/{rejected_lot.id}"
        )
        assert sender_lot_after_reject.status_code == 200
        assert (
            sender_lot_after_reject.json()["current_holder_organization_id"]
            == str(sender.organization_id)
        )
        assert sender_lot_after_reject.json()["status"] == "active"

    for lot in (first_lot, rejected_lot):
        events = list(
            admin_session.scalars(
                select(Event)
                .where(Event.lot_id == lot.id)
                .order_by(Event.sequence_number)
            ).all()
        )
        assert events[0].prev_hash == GENESIS_PREV_HASH
        assert verify_event_chain(events)["valid"] is True

    admin_session.execute(
        delete(Handover).where(Handover.lot_id.in_([first_lot.id, rejected_lot.id]))
    )
    with admin_session.begin_nested():
        admin_session.execute(text("ALTER TABLE events DISABLE TRIGGER USER"))
        admin_session.execute(
            delete(Event).where(Event.lot_id.in_([first_lot.id, rejected_lot.id]))
        )
        admin_session.execute(text("ALTER TABLE events ENABLE TRIGGER USER"))
    admin_session.execute(delete(Lot).where(Lot.id.in_([first_lot.id, rejected_lot.id])))
    admin_session.execute(delete(Farm).where(Farm.id == farm.id))
    admin_session.execute(delete(Product).where(Product.id == product.id))
    admin_session.commit()
