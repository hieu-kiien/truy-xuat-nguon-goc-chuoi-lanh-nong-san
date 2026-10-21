"""Regression tests for the defects found while reviewing the Sprint 8 merge wave.

Each test names the symptom that was observed on `main` and pins the behaviour
that has to hold instead.
"""

from datetime import UTC, datetime, timedelta
from io import BytesIO
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pypdf import PdfReader
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.bootstrap_db_role import _grant_existing_table_permissions
from app.core.auth import Principal
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login

lineage_products = fixtures.lineage_products


def _principal(identity, role: str = "grower") -> Principal:
    return Principal(
        user_id=identity.user_id,
        email=identity.email,
        full_name="Regression test user",
        organization_id=identity.organization_id,
        organization_name="Regression organization",
        organization_type="farm",
        role=role,
    )


# --- 1. The RLS policy for shipment events lost its branch -----------------


@pytest.mark.asyncio
async def test_system_admin_opens_a_shipment_for_a_lot_of_another_organization(
    request, admin_session: Session
):
    """A carrier that does not hold the lot must still be able to open a trip.

    The INSERT policy on `events` had lost the shipment branch, so the insert
    was rejected by RLS and the endpoint answered 409.
    """
    products = request.getfixturevalue("lineage_products")
    factory = request.getfixturevalue("identity_factory")
    owner = factory(role="grower")
    admin = factory(role="system_admin", organization_type="inspection")
    lot = add_lot(admin_session, owner, products[0], quantity="50.000")

    async with client() as api:
        await login(api, admin)
        response = await api.post(
            "/api/v1/shipments/",
            json={
                "container_code": "REGRESSION-COLD-01",
                "lot_ids": [str(lot.id)],
            },
        )
        assert response.status_code == 201, response.text


# --- 2. An organization admin must not be able to mint an inspector -------


@pytest.mark.asyncio
async def test_organization_admin_cannot_invite_an_inspector(
    request, admin_session: Session
):
    """The inspector role reads every organization, so it cannot be granted."""
    factory = request.getfixturevalue("identity_factory")
    admin = factory(role="organization_admin", organization_type="cooperative")

    async with client() as api:
        await login(api, admin)
        response = await api.post(
            "/api/v1/organizations/invitations",
            json={
                "email": "escalated@example.com",
                "role_code": "inspector",
                "full_name": "Escalated Inspector",
            },
        )
        assert response.status_code == 403, response.text


# --- 3. Accepting an invitation for an existing address is a conflict ------


@pytest.mark.asyncio
async def test_accepting_an_invitation_for_an_existing_address_is_a_conflict(
    request, admin_session: Session
):
    """The address already has an account, so the token must not be usable."""
    factory = request.getfixturevalue("identity_factory")
    admin = factory(role="organization_admin", organization_type="cooperative")
    existing = factory(role="grower")

    async with client() as api:
        await login(api, admin)
        created = await api.post(
            "/api/v1/organizations/invitations",
            json={
                "email": existing.email,
                "role_code": "grower",
                "full_name": "Existing Grower",
            },
        )
        assert created.status_code == 201, created.text
        token = created.json()["invitation_url"].split("token=")[-1]

        accepted = await api.post(
            f"/api/v1/public/invitations/{token}/accept",
            json={
                "password": "Correct horse battery staple 2026!",
                "full_name": "Existing Grower",
            },
        )
        assert accepted.status_code == 409, accepted.text


# --- 4. A malformed parameter schema must be refused, not crash ------------


@pytest.mark.asyncio
async def test_processing_step_parameter_schema_must_describe_a_type(
    request, admin_session: Session
):
    """A schema value that is not an object used to raise an AttributeError."""
    factory = request.getfixturevalue("identity_factory")
    admin = factory(role="system_admin", organization_type="inspection")

    async with client() as api:
        await login(api, admin)
        response = await api.post(
            "/api/v1/processing-steps/",
            json={
                "code": f"REGRESSION-{uuid4().hex[:6].upper()}",
                "name": "Regressive step",
                "parameter_schema": {"water_temperature_celsius": "number"},
            },
        )
        assert response.status_code == 422, response.text


# --- 5. The PDF report must escape the markup ------------------------------


@pytest.mark.asyncio
async def test_lot_pdf_report_escapes_user_data_in_the_markup(
    request, admin_session: Session
):
    """User data must reach the PDF as text, not as ReportLab markup.

    A lot name or an event note is written by a user, so a name that looks
    like markup would otherwise be interpreted by the PDF engine.
    """
    products = request.getfixturevalue("lineage_products")
    factory = request.getfixturevalue("identity_factory")
    owner = factory(role="grower")
    lot = add_lot(admin_session, owner, products[0], quantity="20.000")
    admin_session.execute(
        text("UPDATE lots SET name = :name WHERE id = :id"),
        {"name": "Rau & củ <b>đậm</b>", "id": lot.id},
    )
    admin_session.commit()

    async with client() as api:
        await login(api, owner)
        response = await api.get(f"/api/v1/lots/{lot.id}/report.pdf")
        assert response.status_code == 200, response.text
        assert response.content[:4] == b"%PDF"

    extracted = PdfReader(BytesIO(response.content)).pages[0].extract_text()
    # Escaped, the name reaches the page as literal text. Without escaping the
    # PDF engine would consume the tags and render the word as bold.
    assert "Rau & củ <b>đậm</b>" in extracted


# --- 6. Deleting a product that a lot still uses ---------------------------


@pytest.mark.asyncio
async def test_deleting_a_product_used_by_a_lot_is_a_conflict(
    request, admin_session: Session
):
    """The foreign key used to surface as a 500 instead of a 409."""
    products = request.getfixturevalue("lineage_products")
    factory = request.getfixturevalue("identity_factory")
    owner = factory(role="grower")
    admin = factory(role="system_admin", organization_type="inspection")
    add_lot(admin_session, owner, products[0], quantity="20.000")

    async with client() as api:
        await login(api, admin)
        response = await api.delete(f"/api/v1/products/{products[0].id}")
        assert response.status_code == 409, response.text


# --- 7. A reading from the future must be refused --------------------------


@pytest.mark.asyncio
async def test_telemetry_rejects_a_reading_from_the_future(
    request, admin_session: Session
):
    """A future reading stretches a cold chain excursion into the future."""
    products = request.getfixturevalue("lineage_products")
    factory = request.getfixturevalue("identity_factory")
    owner = factory(role="cooperative", organization_type="cooperative")
    lot = add_lot(admin_session, owner, products[0], quantity="50.000")

    async with client() as api:
        await login(api, owner)
        shipment = await api.post(
            "/api/v1/shipments/",
            json={
                "container_code": "REGRESSION-FUTURE-01",
                "lot_ids": [str(lot.id)],
            },
        )
        assert shipment.status_code == 201, shipment.text
        response = await api.post(
            "/api/v1/telemetry/readings",
            json={
                "container_code": "REGRESSION-FUTURE-01",
                "readings": [
                    {
                        "recorded_at": (
                            datetime.now(UTC) + timedelta(days=30)
                        ).isoformat(),
                        "temperature_celsius": "3.5",
                    }
                ],
            },
        )
        assert response.status_code == 422, response.text


# --- 8. The bootstrap must repeat every privilege of the migrations --------


def test_bootstrap_repeats_the_grants_of_the_new_tables_and_functions():
    """A role created after the migrations would end up without privileges.

    The migrations skip every GRANT when the application role does not exist
    yet, so the bootstrap has to repeat them.
    """
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [
            ("integrity_checks",),
            ("processing_steps",),
            ("lot_processing_steps",),
            ("lot_input_lots",),
            ("email_outbox",),
            ("organization_invitations",),
            ("temperature_hourly_aggregates",),
        ],
        [],
    ]

    _grant_existing_table_permissions(mock_cursor, "ttcs_app")

    executed = [str(call[0][0]) for call in mock_cursor.execute.call_args_list]
    for table, grant in (
        ("integrity_checks", "GRANT SELECT, INSERT ON integrity_checks"),
        ("processing_steps", "GRANT SELECT, INSERT, UPDATE ON processing_steps"),
        ("lot_processing_steps", "GRANT SELECT, INSERT ON lot_processing_steps"),
        ("lot_input_lots", "GRANT SELECT, INSERT ON lot_input_lots"),
        ("email_outbox", "GRANT SELECT, INSERT, UPDATE ON email_outbox"),
        (
            "organization_invitations",
            "GRANT SELECT, INSERT, UPDATE ON organization_invitations",
        ),
        (
            "temperature_hourly_aggregates",
            "GRANT SELECT, INSERT ON temperature_hourly_aggregates",
        ),
    ):
        assert any(grant in query for query in executed), (
            f"{table} must be granted by the bootstrap as well"
        )


def test_bootstrap_grants_the_public_and_invitation_functions():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [],
        [
            ("app_public_lot_trace",),
            ("app_public_lot_route",),
            ("app_read_invitation",),
            ("app_accept_invitation",),
            ("app_deactivate_member",),
            ("app_anonymize_organization",),
        ],
    ]

    _grant_existing_table_permissions(mock_cursor, "ttcs_app")

    executed = [str(call[0][0]) for call in mock_cursor.execute.call_args_list]
    for function in (
        "app_public_lot_trace",
        "app_public_lot_route",
        "app_read_invitation",
        "app_accept_invitation",
        "app_deactivate_member",
        "app_anonymize_organization",
    ):
        assert any(
            "GRANT EXECUTE" in query and function in query for query in executed
        ), f"{function} must be executable by the application role"


def test_the_maintenance_role_may_read_the_previous_checks(admin_session: Session):
    """The scanner must see the earlier checks of every lot.

    ``integrity_checks`` has FORCE ROW LEVEL SECURITY, so on a managed
    PostgreSQL where the migration role is not a superuser the policy applies
    to it as well. Without a policy for the maintenance role the scanner reads
    no earlier check: the rotation never ends and every run raises a new
    alert for a chain that was already broken.
    """
    policies = list(
        admin_session.execute(
            text(
                "SELECT policyname FROM pg_policies "
                "WHERE tablename = 'integrity_checks' AND policyname = "
                "'integrity_checks_read_maintenance'"
            )
        ).all()
    )
    assert policies, "the maintenance role needs a policy to read the checks"

    definition = admin_session.execute(
        text(
            "SELECT qual FROM pg_policies WHERE policyname = "
            "'integrity_checks_read_maintenance'"
        )
    ).scalar()
    assert definition is not None
    assert "current_user" in definition.lower()


def test_a_maintenance_role_that_is_not_a_superuser_reads_the_checks(
    admin_session: Session,
):
    """The policy really lets a non superuser owner read the checks."""
    role_name = "ttcs_maintenance_probe"
    probe = admin_session.execute(
        text(
            "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = "
            f"'{role_name}') THEN CREATE ROLE {role_name} NOLOGIN NOSUPERUSER; END IF; END $$;"
        )
    )
    assert probe is not None
    try:
        admin_session.execute(text(f"GRANT USAGE ON SCHEMA public TO {role_name}"))
        admin_session.execute(
            text(
                "GRANT EXECUTE ON FUNCTION public.app_current_organization_id() "
                f"TO {role_name}"
            )
        )
        admin_session.execute(
            text(f"GRANT EXECUTE ON FUNCTION public.app_current_role() TO {role_name}")
        )
        admin_session.execute(text(f"GRANT SELECT ON integrity_checks TO {role_name}"))
        admin_session.commit()
        visible = admin_session.execute(
            text("SELECT count(*) FROM integrity_checks")
        ).scalar()
        admin_session.execute(text(f"SET ROLE {role_name}"))
        try:
            readable = admin_session.execute(
                text("SELECT count(*) FROM integrity_checks")
            ).scalar()
        finally:
            admin_session.execute(text("RESET ROLE"))
        admin_session.commit()
    finally:
        admin_session.execute(text(f"REVOKE ALL ON integrity_checks FROM {role_name}"))
        admin_session.execute(
            text(
                f"REVOKE ALL ON FUNCTION public.app_current_organization_id() FROM {role_name}"
            )
        )
        admin_session.execute(
            text(f"REVOKE ALL ON FUNCTION public.app_current_role() FROM {role_name}")
        )
        admin_session.execute(text(f"REVOKE ALL ON SCHEMA public FROM {role_name}"))
        admin_session.execute(text(f"DROP OWNED BY {role_name}"))
        admin_session.execute(text(f"DROP ROLE {role_name}"))
        admin_session.commit()

    assert readable == visible, (
        "a role that is not the application role must be able to read the checks"
    )
