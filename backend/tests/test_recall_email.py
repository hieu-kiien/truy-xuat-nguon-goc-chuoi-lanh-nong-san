"""Integration test suite for N3-57: recall notices by e-mail.

Opening a recall order must notify every organization involved through the
mail service. The notice names the recall code and the path to the order, and
never the list of affected lots.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models.email_outbox import EmailOutbox
from app.models.farm import Farm
from app.models.identity import Organization
from app.models.lot import Lot
from app.models.product import Product
from app.services import email_service
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


def _seed_lot(db: Session, identity: IdentityFixture) -> Lot:
    farm = Farm(
        organization_id=identity.organization_id,
        name=f"mail-farm-{uuid4().hex[:8]}",
        area_ha=Decimal("1.0000"),
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
    )
    product = Product(name=f"mail-product-{uuid4().hex[:8]}", unit="kg")
    db.add_all([farm, product])
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        name="Lô thu hoạch",
        lot_code=uuid4().hex[:8].upper(),
        product_id=product.id,
        harvested_on=date.today(),
        quantity=Decimal("10.000"),
        remaining_quantity=Decimal("10.000"),
        status="active",
    )
    db.add(lot)
    db.commit()
    return lot


def _set_contact_email(db: Session, organization_id, address: str) -> None:
    organization = db.get(Organization, organization_id)
    assert organization is not None
    organization.contact_email = address
    db.commit()


@pytest.mark.asyncio
async def test_n3_57_open_recall_sends_a_notice_to_the_holder(
    admin_session: Session, identity_factory
):
    """The organization holding the lot receives the recall notice."""
    inspector = identity_factory(role="inspector", organization_type="inspection")
    holder = identity_factory(role="grower", organization_type="farm")
    lot = _seed_lot(admin_session, holder)
    _set_contact_email(admin_session, holder.organization_id, "bao-cao@example.com")

    async with _client() as inspector_client:
        await _login(inspector_client, inspector)
        opened = await inspector_client.post(
            "/api/v1/recalls/",
            json={
                "lot_id": str(lot.id),
                "reason": "Lô hàng thu hoạch đầy nghi phân định cấp kiểm tra an toàn thực phẩm.",
            },
        )
        assert opened.status_code == 201, opened.text
        recall_code = opened.json()["recall_code"]

    rows = list(
        admin_session.scalars(
            select(EmailOutbox).where(EmailOutbox.kind == "recall_notice")
        ).all()
    )
    assert len(rows) == 1
    message = rows[0]
    assert message.recipient_email == "bao-cao@example.com"
    assert message.status in {"sent", "recorded"}
    assert message.organization_id == inspector.organization_id
    assert recall_code in message.body
    # The body names the code and the path, but never the list of lots.
    assert f"/lots/{lot.id}" in message.body
    assert lot.lot_code not in message.body


@pytest.mark.asyncio
async def test_n3_57_organizations_without_a_contact_address_are_skipped(
    admin_session: Session, identity_factory
):
    """No contact address means no notice, and no failure of the recall."""
    inspector = identity_factory(role="inspector", organization_type="inspection")
    holder = identity_factory(role="grower", organization_type="farm")
    lot = _seed_lot(admin_session, holder)

    async with _client() as inspector_client:
        await _login(inspector_client, inspector)
        opened = await inspector_client.post(
            "/api/v1/recalls/",
            json={
                "lot_id": str(lot.id),
                "reason": "Lô hàng thu hoạch đầy nghi phân định cấp kiểm tra an toàn thực phẩm.",
            },
        )
        assert opened.status_code == 201, opened.text

    rows = list(
        admin_session.scalars(
            select(EmailOutbox).where(EmailOutbox.kind == "recall_notice")
        ).all()
    )
    assert rows == []


@pytest.mark.asyncio
async def test_n3_57_contact_email_can_be_set_by_the_organization_admin(
    admin_session: Session, identity_factory
):
    """The organization admin publishes the official contact address."""
    admin = identity_factory(role="organization_admin", organization_type="cooperative")

    async with _client() as admin_client:
        await _login(admin_client, admin)
        response = await admin_client.put(
            "/api/v1/organizations/me/contact-email",
            json={"contact_email": "  Hop-Truong@Example.COM "},
        )
        assert response.status_code == 200, response.text
        assert response.json()["contact_email"] == "hop-truong@example.com"

        read = await admin_client.get("/api/v1/organizations/me")
        assert read.status_code == 200
        assert read.json()["contact_email"] == "hop-truong@example.com"


@pytest.mark.asyncio
async def test_n3_57_contact_email_rejects_a_malformed_address(
    admin_session: Session, identity_factory
):
    """A malformed address is refused before it reaches the database."""
    admin = identity_factory(role="organization_admin", organization_type="cooperative")

    async with _client() as admin_client:
        await _login(admin_client, admin)
        response = await admin_client.put(
            "/api/v1/organizations/me/contact-email",
            json={"contact_email": "khong-phai-email"},
        )
        assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_n3_57_only_the_administrator_can_change_the_contact_address(
    admin_session: Session, identity_factory
):
    """A grower cannot publish the official contact address."""
    grower = identity_factory(role="grower", organization_type="farm")

    async with _client() as grower_client:
        await _login(grower_client, grower)
        response = await grower_client.put(
            "/api/v1/organizations/me/contact-email",
            json={"contact_email": "grower@example.com"},
        )
        assert response.status_code == 403, response.text


def test_n3_57_delivery_is_retried_and_recorded(admin_session: Session, monkeypatch):
    """A rejected delivery is retried up to three times and then marked failed."""

    attempts: list[int] = []

    def failing_smtp(recipient: str, subject: str, body: str) -> None:
        attempts.append(1)
        raise OSError("SMTP không khả dụng")

    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_service.settings, "EMAIL_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(email_service.settings, "EMAIL_RETRY_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(email_service, "_send_via_smtp", failing_smtp)

    delivery = email_service.deliver_email(
        admin_session,
        recipient_email="nhan@example.com",
        subject="Thử gửi",
        body="Nội dung",
        kind="recall_notice",
    )

    assert len(attempts) == 3
    assert delivery.status == "failed"
    assert delivery.attempts == 3
    assert delivery.error is not None

    row = admin_session.get(EmailOutbox, delivery.id)
    assert row is not None
    assert row.status == "failed"
    assert row.attempts == 3


def test_n3_57_delivery_without_smtp_is_recorded(admin_session: Session, monkeypatch):
    """Without an SMTP server the message is still recorded as evidence."""

    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "")

    delivery = email_service.deliver_email(
        admin_session,
        recipient_email="nhan@example.com",
        subject="Thử gửi",
        body="Nội dung",
        kind="recall_notice",
    )

    assert delivery.status == "recorded"
    assert delivery.delivered is True
    row = admin_session.get(EmailOutbox, delivery.id)
    assert row is not None
    assert row.recipient_email == "nhan@example.com"
