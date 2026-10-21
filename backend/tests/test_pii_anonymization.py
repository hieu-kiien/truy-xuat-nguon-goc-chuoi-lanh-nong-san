"""Erasing identifying data keeps the event hash chain valid (N3-75)."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.event import Event
from app.models.farm import Farm
from app.models.identity import Organization, User
from app.models.lot import Lot
from app.services import event_service, pii_service
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import client, login

lineage_products = fixtures.lineage_products


def _principal(identity) -> Principal:
    return Principal(
        user_id=identity.user_id,
        email=identity.email,
        full_name="Integration test user",
        organization_id=identity.organization_id,
        organization_name="Integration test organization",
        organization_type="farm",
        role="grower",
    )


def _farm_with_lot(db: Session, identity, product):
    farm = Farm(
        organization_id=identity.organization_id,
        name="Nông hộ Nguyễn Văn Minh",
        area_ha=Decimal("2"),
        latitude=Decimal("11.862450"),
        longitude=Decimal("108.538120"),
    )
    db.add(farm)
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        product_id=product.id,
        name="Lot of the farmer",
        lot_code=f"PII{uuid4().hex[:8].upper()}",
        harvested_on=date.today(),
        quantity=Decimal("10.000"),
        remaining_quantity=Decimal("10.000"),
        status="active",
    )
    db.add(lot)
    db.commit()
    return farm, lot


def test_a_payload_with_identity_data_is_rejected():
    with pytest.raises(HTTPException) as error:
        event_service.assert_payload_has_no_identity({"to_organization_name": "Acme"})
    assert error.value.status_code == 400


def test_the_guard_allows_reference_only_payloads():
    event_service.assert_payload_has_no_identity(
        {"to_organization_id": "x", "note": "ban giao", "quantity": "1"}
    )


def test_anonymization_keeps_the_hash_chain_valid(
    admin_session: Session, lineage_products, identity_factory
):
    grower = identity_factory(role="grower")
    farm, lot = _farm_with_lot(admin_session, grower, lineage_products[0])
    principal = _principal(grower)
    event_service.append_event(
        admin_session,
        principal,
        lot.id,
        event_type="harvest_recorded",
        payload={"product_id": str(lineage_products[0].id), "quantity": "10"},
    )
    admin_session.commit()
    before = list(
        admin_session.scalars(
            select(Event).where(Event.lot_id == lot.id).order_by(Event.sequence_number)
        ).all()
    )
    hashes_before = [item.event_hash for item in before]
    assert before

    request = pii_service.request_anonymization(
        admin_session, principal, farm.id, "Yêu cầu theo Nghị định 13/2023"
    )
    admin = identity_factory(role="system_admin", organization_type="inspection")
    admin_principal = _principal(admin)
    admin_principal = Principal(
        user_id=admin.user_id,
        email=admin.email,
        full_name="Admin",
        organization_id=admin.organization_id,
        organization_name="Admin org",
        organization_type="inspection",
        role="system_admin",
    )
    pii_service.execute_anonymization(admin_session, admin_principal, request.id)
    admin_session.commit()

    after = list(
        admin_session.scalars(
            select(Event).where(Event.lot_id == lot.id).order_by(Event.sequence_number)
        ).all()
    )
    assert [item.event_hash for item in after] == hashes_before
    report = event_service.verify_lot_integrity(admin_session, admin_principal, lot.id)
    assert report["valid"] is True
    assert report["checked_events"] == len(before)


def test_anonymization_hides_the_identity(
    admin_session: Session, lineage_products, identity_factory
):
    grower = identity_factory(role="grower")
    farm, _lot = _farm_with_lot(admin_session, grower, lineage_products[0])
    original_name = "Nông hộ Nguyễn Văn Minh"
    admin = identity_factory(role="system_admin", organization_type="inspection")

    request = pii_service.request_anonymization(
        admin_session, _principal(grower), farm.id, None
    )
    admin_principal = Principal(
        user_id=admin.user_id,
        email=admin.email,
        full_name="Admin",
        organization_id=admin.organization_id,
        organization_name="Admin org",
        organization_type="inspection",
        role="system_admin",
    )
    pii_service.execute_anonymization(admin_session, admin_principal, request.id)
    admin_session.commit()
    admin_session.expire_all()

    account = admin_session.get(User, grower.user_id)
    organization = admin_session.get(Organization, grower.organization_id)
    anonymized_farm = admin_session.get(Farm, farm.id)

    assert account.full_name != "Integration test user"
    assert account.full_name.startswith("Nông hộ ẩn danh")
    assert account.email.endswith("@anonymized.invalid")
    assert organization.name.startswith("Tổ chức ẩn danh")
    assert anonymized_farm.name.startswith("Vùng trồng ẩn danh")
    assert anonymized_farm.latitude is None
    assert anonymized_farm.longitude is None
    assert original_name not in account.full_name


@pytest.mark.asyncio
async def test_only_a_system_admin_may_execute_the_erase(
    request, admin_session: Session
):
    products = request.getfixturevalue("lineage_products")
    factory = request.getfixturevalue("identity_factory")
    grower = factory(role="grower")
    admin = factory(role="system_admin", organization_type="inspection")
    farm, _lot = _farm_with_lot(admin_session, grower, products[0])

    async with client() as api:
        await login(api, grower)
        created = await api.post(
            "/api/v1/pii/anonymization-requests",
            json={"farm_id": str(farm.id), "reason": "Yêu cầu xoá dữ liệu"},
        )
        assert created.status_code == 201, created.text
        request_id = created.json()["id"]

        denied = await api.post(
            f"/api/v1/pii/anonymization-requests/{request_id}/execute"
        )
        assert denied.status_code == 403, denied.text

    async with client() as api:
        await login(api, admin)
        executed = await api.post(
            f"/api/v1/pii/anonymization-requests/{request_id}/execute"
        )
        assert executed.status_code == 200, executed.text
        assert executed.json()["status"] == "completed"

    async with client() as api:
        await login(api, admin)
        again = await api.post(
            f"/api/v1/pii/anonymization-requests/{request_id}/execute"
        )
        assert again.status_code == 409, again.text


@pytest.mark.asyncio
async def test_the_public_trace_shows_the_anonymized_farm(
    request, admin_session: Session
):
    products = request.getfixturevalue("lineage_products")
    factory = request.getfixturevalue("identity_factory")
    grower = factory(role="grower")
    admin = factory(role="system_admin", organization_type="inspection")
    farm, lot = _farm_with_lot(admin_session, grower, products[0])

    async with client() as api:
        response = await api.get(f"/api/v1/public/trace/{lot.lot_code}")
        assert response.status_code == 200, response.text
        assert response.json()["trace"]["farm_name"] == "Nông hộ Nguyễn Văn Minh"

    request_row = pii_service.request_anonymization(
        admin_session, _principal(grower), farm.id, None
    )
    pii_service.execute_anonymization(
        admin_session,
        Principal(
            user_id=admin.user_id,
            email=admin.email,
            full_name="Admin",
            organization_id=admin.organization_id,
            organization_name="Admin org",
            organization_type="inspection",
            role="system_admin",
        ),
        request_row.id,
    )
    admin_session.commit()

    async with client() as api:
        response = await api.get(f"/api/v1/public/trace/{lot.lot_code}")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["trace"]["farm_name"].startswith("Vùng trồng ẩn danh")
        assert "Nguyễn" not in response.text
