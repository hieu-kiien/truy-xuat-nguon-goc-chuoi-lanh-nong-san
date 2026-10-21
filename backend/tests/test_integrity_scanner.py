"""Integration test suite for N3-74: the scheduled integrity scanner.

The scanner verifies the event chain of every lot that is due, records the
result as a check that no person produced, and raises an alert the first time
a chain is found broken.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.jobs import integrity_scanner
from app.models.event import Event
from app.models.farm import Farm
from app.models.integrity_alert import IntegrityAlert
from app.models.integrity_check import IntegrityCheck
from app.models.lot import Lot
from app.models.product import Product
from app.services import event_service
from tests.conftest import IdentityFixture
from tests.lineage_helpers import client, login


def _create_lot(db: Session, identity: IdentityFixture) -> tuple[Farm, Product, Lot]:
    suffix = uuid4().hex
    farm = Farm(
        organization_id=identity.organization_id,
        name=f"scanner-farm-{suffix}",
        area_ha=Decimal("1.0000"),
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
    )
    product = Product(name=f"scanner-product-{suffix}", unit="kg")
    db.add_all([farm, product])
    db.flush()
    lot = Lot(
        organization_id=identity.organization_id,
        current_holder_organization_id=identity.organization_id,
        farm_id=farm.id,
        name="Scanner test lot",
        lot_code=f"S{uuid4().hex[:8].upper()}",
        product_id=product.id,
        harvested_on=date.today(),
        quantity=Decimal("3.000"),
        remaining_quantity=Decimal("3.000"),
        status="active",
    )
    db.add(lot)
    db.commit()
    return farm, product, lot


def _principal(identity: IdentityFixture) -> Principal:
    return Principal(
        user_id=identity.user_id,
        email=identity.email,
        full_name="Scanner test user",
        organization_id=identity.organization_id,
        organization_name="Scanner test organization",
        organization_type="farm",
        role="grower",
    )


def _append_chain(db: Session, principal: Principal, lot_id, count: int) -> None:
    for sequence in range(1, count + 1):
        event_service.append_event(
            db,
            principal,
            lot_id,
            event_type="scanner_test",
            payload={"value": sequence},
        )
    db.commit()


def _tamper_with_event(db: Session, lot_id, sequence_number: int) -> None:
    """Simulate the SQL tamper scenario the scanner has to catch."""
    db.execute(text("ALTER TABLE events DISABLE TRIGGER USER"))
    db.execute(
        text(
            "UPDATE events SET payload = CAST(:payload AS jsonb) "
            "WHERE lot_id = :lot_id AND sequence_number = :sequence_number"
        ),
        {
            "payload": '{"value": 999}',
            "lot_id": lot_id,
            "sequence_number": sequence_number,
        },
    )
    db.execute(text("ALTER TABLE events ENABLE TRIGGER USER"))
    db.commit()


def _cleanup(db: Session, farm: Farm, product: Product, lot_ids: list) -> None:
    if lot_ids:
        with db.begin_nested():
            db.execute(text("ALTER TABLE events DISABLE TRIGGER USER"))
            db.execute(text("ALTER TABLE integrity_checks DISABLE TRIGGER USER"))
            db.execute(text("ALTER TABLE integrity_alerts DISABLE TRIGGER USER"))
            db.execute(delete(IntegrityAlert).where(IntegrityAlert.lot_id.in_(lot_ids)))
            db.execute(delete(IntegrityCheck).where(IntegrityCheck.lot_id.in_(lot_ids)))
            db.execute(delete(Event).where(Event.lot_id.in_(lot_ids)))
            db.execute(text("ALTER TABLE integrity_alerts ENABLE TRIGGER USER"))
            db.execute(text("ALTER TABLE integrity_checks ENABLE TRIGGER USER"))
            db.execute(text("ALTER TABLE events ENABLE TRIGGER USER"))
        db.execute(delete(Lot).where(Lot.id.in_(lot_ids)))
    db.execute(delete(Farm).where(Farm.id == farm.id))
    db.execute(delete(Product).where(Product.id == product.id))
    db.commit()


def test_n3_74_scan_records_a_system_check(request, admin_session):
    """A valid chain produces one check marked as produced by the scheduler."""
    identities = request.getfixturevalue("identity_factory")
    identity = identities(role="grower", organization_type="farm")
    farm, product, lot = _create_lot(admin_session, identity)
    try:
        _append_chain(admin_session, _principal(identity), lot.id, 3)

        summary = integrity_scanner.run_integrity_scan(admin_session, lot_ids=[lot.id])

        assert summary["checked_lots"] == 1
        assert summary["broken_lots"] == 0
        assert summary["alerts_raised"] == 0

        checks = list(
            admin_session.scalars(
                select(IntegrityCheck).where(IntegrityCheck.lot_id == lot.id)
            ).all()
        )
        assert len(checks) == 1
        check = checks[0]
        assert check.valid is True
        assert check.checked_events == 3
        assert check.checked_by_source == "system"
        assert check.checked_by_user_id is None
        assert check.organization_id == identity.organization_id
    finally:
        _cleanup(admin_session, farm, product, [lot.id])


def test_n3_74_scan_is_not_due_again_before_the_rotation(request, admin_session):
    """A lot that was just checked and did not change is not checked again."""
    identities = request.getfixturevalue("identity_factory")
    identity = identities(role="grower", organization_type="farm")
    farm, product, lot = _create_lot(admin_session, identity)
    try:
        _append_chain(admin_session, _principal(identity), lot.id, 2)

        integrity_scanner.run_integrity_scan(admin_session, lot_ids=[lot.id])
        second = integrity_scanner.run_integrity_scan(admin_session, lot_ids=[lot.id])

        assert second["checked_lots"] == 0

        checks = list(
            admin_session.scalars(
                select(IntegrityCheck).where(IntegrityCheck.lot_id == lot.id)
            ).all()
        )
        assert len(checks) == 1
    finally:
        _cleanup(admin_session, farm, product, [lot.id])


def test_n3_74_scan_detects_a_tampered_chain_and_raises_one_alert(
    request, admin_session
):
    """A broken chain is recorded, alerted once, and not alerted again."""
    identities = request.getfixturevalue("identity_factory")
    identity = identities(role="grower", organization_type="farm")
    farm, product, lot = _create_lot(admin_session, identity)
    try:
        _append_chain(admin_session, _principal(identity), lot.id, 3)
        integrity_scanner.run_integrity_scan(admin_session, lot_ids=[lot.id])

        _tamper_with_event(admin_session, lot.id, 2)

        summary = integrity_scanner.run_integrity_scan(
            admin_session, lot_ids=[lot.id], include_all=True
        )
        assert summary["checked_lots"] == 1
        assert summary["broken_lots"] == 1
        assert summary["alerts_raised"] == 1

        checks = list(
            admin_session.scalars(
                select(IntegrityCheck)
                .where(IntegrityCheck.lot_id == lot.id)
                .order_by(IntegrityCheck.checked_at.asc())
            ).all()
        )
        assert len(checks) == 2
        assert checks[0].valid is True
        assert checks[1].valid is False
        assert checks[1].first_invalid_sequence == 2
        assert checks[1].issues

        alerts = list(
            admin_session.scalars(
                select(IntegrityAlert).where(IntegrityAlert.lot_id == lot.id)
            ).all()
        )
        assert len(alerts) == 1
        assert alerts[0].first_invalid_sequence == 2
        assert alerts[0].organization_id == identity.organization_id

        # The chain stays broken, so a second run must not raise another alert.
        again = integrity_scanner.run_integrity_scan(
            admin_session, lot_ids=[lot.id], include_all=True
        )
        assert again["broken_lots"] == 1
        assert again["alerts_raised"] == 0

        alerts = list(
            admin_session.scalars(
                select(IntegrityAlert).where(IntegrityAlert.lot_id == lot.id)
            ).all()
        )
        assert len(alerts) == 1
    finally:
        _cleanup(admin_session, farm, product, [lot.id])


def test_n3_74_rotation_picks_up_lots_that_were_not_checked_for_a_while(
    request, admin_session
):
    """A lot whose last check is older than the rotation window is due again."""
    identities = request.getfixturevalue("identity_factory")
    identity = identities(role="grower", organization_type="farm")
    farm, product, lot = _create_lot(admin_session, identity)
    try:
        _append_chain(admin_session, _principal(identity), lot.id, 2)
        integrity_scanner.run_integrity_scan(admin_session, lot_ids=[lot.id])

        # Age the recorded check so the lot falls outside the rotation window.
        admin_session.execute(text("ALTER TABLE integrity_checks DISABLE TRIGGER USER"))
        admin_session.execute(
            text(
                "UPDATE integrity_checks SET checked_at = :checked_at "
                "WHERE lot_id = :lot_id"
            ),
            {
                "checked_at": datetime.now(UTC) - timedelta(days=8),
                "lot_id": lot.id,
            },
        )
        admin_session.execute(text("ALTER TABLE integrity_checks ENABLE TRIGGER USER"))
        admin_session.commit()

        summary = integrity_scanner.run_integrity_scan(
            admin_session, lot_ids=[lot.id], rotation_days=7
        )
        assert summary["checked_lots"] == 1
        assert summary["broken_lots"] == 0
    finally:
        _cleanup(admin_session, farm, product, [lot.id])


@pytest.mark.asyncio
async def test_n3_74_summary_endpoint_reports_the_broken_lots(request, admin_session):
    """The administrator view sees how many lots are broken and which ones."""
    identities = request.getfixturevalue("identity_factory")
    identity = identities(role="grower", organization_type="farm")
    inspector = identities(role="inspector", organization_type="inspection")
    farm, product, lot = _create_lot(admin_session, identity)
    try:
        _append_chain(admin_session, _principal(identity), lot.id, 2)
        integrity_scanner.run_integrity_scan(admin_session, lot_ids=[lot.id])
        _tamper_with_event(admin_session, lot.id, 1)
        integrity_scanner.run_integrity_scan(
            admin_session, lot_ids=[lot.id], include_all=True
        )

        async with client() as api:
            await login(api, inspector)
            response = await api.get("/api/v1/events/integrity/summary")
            assert response.status_code == 200, response.text
            payload = response.json()

        assert payload["last_checked_at"] is not None
        assert payload["broken_lot_count"] >= 1
        broken_ids = {row["lot_id"] for row in payload["broken_lots"]}
        assert str(lot.id) in broken_ids
        broken_row = next(
            row for row in payload["broken_lots"] if row["lot_id"] == str(lot.id)
        )
        assert broken_row["first_invalid_sequence"] == 1
        assert broken_row["lot_code"] == lot.lot_code
        assert payload["recent_alerts"]
    finally:
        _cleanup(admin_session, farm, product, [lot.id])
