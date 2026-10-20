"""Integration test suite for N3-27: processing steps of cooperative lots.

A cooperative records that a lot went through a processing step with its
parameters. Every record becomes one event on the lot chain, the parameters
follow the schema of the step, and the public page only shows the names of
the steps.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models.event import Event
from app.models.farm import Farm
from app.models.lot import Lot
from app.models.processing_step import LotProcessingStep, ProcessingStep
from app.models.product import Product
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
        name=f"step-farm-{uuid4().hex[:8]}",
        area_ha=Decimal("1.0000"),
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
    )
    product = Product(name=f"step-product-{uuid4().hex[:8]}", unit="kg")
    db.add_all([farm, product])
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        name="Lô qua sơ chế",
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


def _seed_step(db: Session, code: str, name: str, schema: dict) -> ProcessingStep:
    step = ProcessingStep(
        code=f"{code}-{uuid4().hex[:6].upper()}",
        name=name,
        parameter_schema=schema,
        is_active=True,
    )
    db.add(step)
    db.commit()
    return step


@pytest.mark.asyncio
async def test_n3_27_recording_a_step_writes_one_event(
    admin_session: Session, identity_factory
):
    """Every processing step becomes one event on the lot chain."""
    cooperative = identity_factory(role="cooperative", organization_type="cooperative")
    lot = _seed_lot(admin_session, cooperative)
    step = _seed_step(
        admin_session,
        "WASH",
        "Rửa",
        {"water_temperature_celsius": {"type": "number", "label": "Nhiệt độ nước rửa"}},
    )

    async with _client() as client:
        await _login(client, cooperative)
        response = await client.post(
            f"/api/v1/lots/{lot.id}/processing-steps",
            json={
                "processing_step_id": str(step.id),
                "parameters": {"water_temperature_celsius": 12.5},
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["processing_step_code"].startswith("WASH-")
        assert payload["parameters"] == {"water_temperature_celsius": 12.5}

    events = list(
        admin_session.scalars(
            select(Event).where(
                Event.lot_id == lot.id,
                Event.event_type == "processing_step_recorded",
            )
        ).all()
    )
    assert len(events) == 1
    assert events[0].payload["processing_step_code"].startswith("WASH-")
    assert events[0].payload["parameters"] == {"water_temperature_celsius": 12.5}


@pytest.mark.asyncio
async def test_n3_27_parameters_must_follow_the_schema(
    admin_session: Session, identity_factory
):
    """A value the schema does not describe is refused."""
    cooperative = identity_factory(role="cooperative", organization_type="cooperative")
    lot = _seed_lot(admin_session, cooperative)
    step = _seed_step(
        admin_session,
        "PACK",
        "Đóng gói",
        {"packaging_type": {"type": "string"}},
    )

    async with _client() as client:
        await _login(client, cooperative)
        unexpected = await client.post(
            f"/api/v1/lots/{lot.id}/processing-steps",
            json={
                "processing_step_id": str(step.id),
                "parameters": {"shift": "ca đêm"},
            },
        )
        assert unexpected.status_code == 422, unexpected.text

        wrong_type = await client.post(
            f"/api/v1/lots/{lot.id}/processing-steps",
            json={
                "processing_step_id": str(step.id),
                "parameters": {"packaging_type": 7},
            },
        )
        assert wrong_type.status_code == 422, wrong_type.text

    rows = list(
        admin_session.scalars(
            select(LotProcessingStep).where(LotProcessingStep.lot_id == lot.id)
        ).all()
    )
    assert rows == []


@pytest.mark.asyncio
async def test_n3_27_the_catalogue_is_managed_by_an_administrator(
    admin_session: Session, identity_factory
):
    """Only an administrator adds a processing step to the catalogue."""
    cooperative = identity_factory(role="cooperative", organization_type="cooperative")
    system_admin = identity_factory(
        role="system_admin", organization_type="administration"
    )

    async with _client() as cooperative_client, _client() as admin_client:
        await _login(cooperative_client, cooperative)
        await _login(admin_client, system_admin)

        refused = await cooperative_client.post(
            "/api/v1/processing-steps/",
            json={"code": f"WASH-{uuid4().hex[:6].upper()}", "name": "Rửa"},
        )
        assert refused.status_code == 403, refused.text

        accepted = await admin_client.post(
            "/api/v1/processing-steps/",
            json={
                "code": f"WASH-{uuid4().hex[:6].upper()}",
                "name": "Rửa",
                "parameter_schema": {},
            },
        )
        assert accepted.status_code == 201, accepted.text

        catalogue = await cooperative_client.get("/api/v1/processing-steps/")
        assert catalogue.status_code == 200
        assert any(item["code"].startswith("WASH-") for item in catalogue.json())


@pytest.mark.asyncio
async def test_n3_27_public_page_shows_only_the_step_names(
    admin_session: Session, identity_factory
):
    """The public trace names the steps but never exposes the parameters."""
    cooperative = identity_factory(role="cooperative", organization_type="cooperative")
    lot = _seed_lot(admin_session, cooperative)
    step = _seed_step(
        admin_session,
        "WASH",
        "Rửa",
        {"water_temperature_celsius": {"type": "number"}},
    )

    async with _client() as client:
        await _login(client, cooperative)
        created = await client.post(
            f"/api/v1/lots/{lot.id}/processing-steps",
            json={
                "processing_step_id": str(step.id),
                "parameters": {"water_temperature_celsius": 12.5},
            },
        )
        assert created.status_code == 201, created.text

    async with _client() as public_client:
        response = await public_client.get(f"/api/v1/public/trace/{lot.lot_code}")
        assert response.status_code == 200, response.text
        trace = response.json()["trace"]

    assert trace["processing_summary"] == "Rửa"
    assert "12.5" not in response.text
    assert "water_temperature_celsius" not in response.text


@pytest.mark.asyncio
async def test_n3_27_a_lot_of_another_organization_cannot_be_recorded(
    admin_session: Session, identity_factory
):
    """Only the organization holding the lot records a processing step."""
    cooperative = identity_factory(role="cooperative", organization_type="cooperative")
    outsider = identity_factory(role="grower", organization_type="farm")
    lot = _seed_lot(admin_session, cooperative)
    step = _seed_step(admin_session, "SORT", "Phân loại", {})

    async with _client() as outsider_client:
        await _login(outsider_client, outsider)
        response = await outsider_client.post(
            f"/api/v1/lots/{lot.id}/processing-steps",
            json={"processing_step_id": str(step.id), "parameters": {}},
        )
        assert response.status_code in {403, 404}, response.text
