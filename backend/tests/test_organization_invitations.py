"""Integration test suite for N3-30: organization member invitations.

An invitation link works once and expires after 72 hours. The invited person
sets a password and joins the inviting organization, and an administrator can
deactivate a member who has left.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models.email_outbox import EmailOutbox
from app.models.identity import Organization, User
from app.models.organization_invitation import OrganizationInvitation

PASSWORD = "Mật khẩu đủ dài 2026!"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


def _token_for(admin_session: Session, recipient: str) -> str:
    """Find the invitation token that was mailed to one address."""
    outbox = admin_session.scalar(
        select(EmailOutbox).where(
            EmailOutbox.kind == "organization_invitation",
            EmailOutbox.recipient_email == recipient,
        )
    )
    assert outbox is not None, f"no invitation e-mail for {recipient}"
    marker = "/moi-dai-nhiep?token="
    assert marker in outbox.body, outbox.body
    return outbox.body.split(marker, 1)[1].split()[0].strip()


@pytest.mark.asyncio
async def test_n3_30_invitation_is_sent_and_can_be_accepted(
    admin_session: Session, identity_factory
):
    """The invited person sets a password and joins the right organization."""
    admin = identity_factory(role="organization_admin", organization_type="cooperative")
    invitee_email = "new.member@example.com"

    async with _client() as admin_client:
        await _login(admin_client, admin)
        created = await admin_client.post(
            "/api/v1/organizations/invitations",
            json={"email": invitee_email, "role_code": "grower"},
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["email"] == invitee_email
        assert body["role_code"] == "grower"
        assert body["status"] == "pending"
        # The invitation expires after 72 hours.
        expires = datetime.fromisoformat(body["expires_at"])
        created_at = datetime.fromisoformat(body["created_at"])
        assert timedelta(hours=71) < (expires - created_at) <= timedelta(hours=72)

    token = _token_for(admin_session, invitee_email)
    organization = admin_session.get(Organization, admin.organization_id)
    assert organization is not None

    async with _client() as public_client:
        preview = await public_client.get(f"/api/v1/public/invitations/{token}")
        assert preview.status_code == 200, preview.text
        assert preview.json()["email"] == invitee_email
        assert preview.json()["organization_name"] == organization.name

        accepted = await public_client.post(
            f"/api/v1/public/invitations/{token}/accept",
            json={"password": PASSWORD, "full_name": "Thành viên mới"},
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["email"] == invitee_email
        assert accepted.json()["role_code"] == "grower"

    new_user = admin_session.scalar(select(User).where(User.email == invitee_email))
    assert new_user is not None
    assert new_user.organization_id == admin.organization_id
    assert new_user.role_code == "grower"
    assert new_user.is_active is True

    invitation = admin_session.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.email == invitee_email
        )
    )
    assert invitation is not None
    assert invitation.accepted_at is not None
    assert invitation.accepted_user_id == new_user.id


@pytest.mark.asyncio
async def test_n3_30_invitation_link_works_only_once(
    admin_session: Session, identity_factory
):
    """A second use of the same link is refused."""
    admin = identity_factory(role="organization_admin", organization_type="cooperative")
    email = "one.use@example.com"

    async with _client() as admin_client:
        await _login(admin_client, admin)
        await admin_client.post(
            "/api/v1/organizations/invitations",
            json={"email": email, "role_code": "grower"},
        )

    token = _token_for(admin_session, email)

    async with _client() as public_client:
        first = await public_client.post(
            f"/api/v1/public/invitations/{token}/accept",
            json={"password": PASSWORD, "full_name": "Người nhận"},
        )
        assert first.status_code == 200, first.text

        second = await public_client.post(
            f"/api/v1/public/invitations/{token}/accept",
            json={"password": PASSWORD, "full_name": "Người nhận"},
        )
        assert second.status_code == 410, second.text


@pytest.mark.asyncio
async def test_n3_30_expired_invitation_is_refused(
    admin_session: Session, identity_factory
):
    """An invitation older than 72 hours can no longer be used."""
    admin = identity_factory(role="organization_admin", organization_type="cooperative")
    email = "expired@example.com"

    async with _client() as admin_client:
        await _login(admin_client, admin)
        await admin_client.post(
            "/api/v1/organizations/invitations",
            json={"email": email, "role_code": "grower"},
        )

    token = _token_for(admin_session, email)

    invitation = admin_session.scalar(
        select(OrganizationInvitation).where(OrganizationInvitation.email == email)
    )
    assert invitation is not None
    # Age the invitation beyond its 72 hour window.
    invitation.created_at = datetime.now(UTC) - timedelta(days=8)
    invitation.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    admin_session.commit()

    async with _client() as public_client:
        response = await public_client.post(
            f"/api/v1/public/invitations/{token}/accept",
            json={"password": PASSWORD, "full_name": "Người nhận"},
        )
        assert response.status_code == 410, response.text


@pytest.mark.asyncio
async def test_n3_30_invitation_requires_an_administrator(
    admin_session: Session, identity_factory
):
    """A grower cannot invite members."""
    grower = identity_factory(role="grower", organization_type="farm")

    async with _client() as grower_client:
        await _login(grower_client, grower)
        response = await grower_client.post(
            "/api/v1/organizations/invitations",
            json={"email": "khong-allowed@example.com", "role_code": "grower"},
        )
        assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_n3_30_duplicate_pending_invitation_is_refused(
    admin_session: Session, identity_factory
):
    """One pending invitation per address and organization."""
    admin = identity_factory(role="organization_admin", organization_type="cooperative")

    async with _client() as admin_client:
        await _login(admin_client, admin)
        first = await admin_client.post(
            "/api/v1/organizations/invitations",
            json={"email": "twice@example.com", "role_code": "grower"},
        )
        assert first.status_code == 201, first.text

        second = await admin_client.post(
            "/api/v1/organizations/invitations",
            json={"email": "twice@example.com", "role_code": "grower"},
        )
        assert second.status_code == 409, second.text


@pytest.mark.asyncio
async def test_n3_30_invitation_can_be_revoked(
    admin_session: Session, identity_factory
):
    """A revoked invitation can no longer be used."""
    admin = identity_factory(role="organization_admin", organization_type="cooperative")
    email = "revoked@example.com"

    async with _client() as admin_client:
        await _login(admin_client, admin)
        created = await admin_client.post(
            "/api/v1/organizations/invitations",
            json={"email": email, "role_code": "grower"},
        )
        assert created.status_code == 201, created.text
        invitation_id = created.json()["id"]

        revoked = await admin_client.post(
            f"/api/v1/organizations/invitations/{invitation_id}/revoke"
        )
        assert revoked.status_code == 200, revoked.text
        assert revoked.json()["status"] == "revoked"

    token = _token_for(admin_session, email)

    async with _client() as public_client:
        response = await public_client.post(
            f"/api/v1/public/invitations/{token}/accept",
            json={"password": PASSWORD, "full_name": "Người nhận"},
        )
        assert response.status_code == 410, response.text


@pytest.mark.asyncio
async def test_n3_30_administrator_deactivates_a_member(
    admin_session: Session, identity_factory
):
    """A member who has left can be deactivated by the administrator."""
    admin = identity_factory(role="organization_admin", organization_type="cooperative")
    email = "leaving@example.com"

    async with _client() as admin_client, _client() as public_client:
        await _login(admin_client, admin)
        created = await admin_client.post(
            "/api/v1/organizations/invitations",
            json={"email": email, "role_code": "grower"},
        )
        assert created.status_code == 201, created.text

        token = _token_for(admin_session, email)
        accepted = await public_client.post(
            f"/api/v1/public/invitations/{token}/accept",
            json={"password": PASSWORD, "full_name": "Người nghỉ việc"},
        )
        assert accepted.status_code == 200, accepted.text
        member_id = accepted.json()["user_id"]

        response = await admin_client.post(
            f"/api/v1/organizations/members/{member_id}/deactivate"
        )
        assert response.status_code == 200, response.text
        assert response.json()["is_active"] is False

        members = await admin_client.get("/api/v1/organizations/members")
        assert members.status_code == 200
        assert any(
            item["id"] == member_id and item["is_active"] is False
            for item in members.json()
        )


@pytest.mark.asyncio
async def test_n3_30_grower_cannot_deactivate_a_member(
    admin_session: Session, identity_factory
):
    """Only an administrator may deactivate a member."""
    grower = identity_factory(role="grower", organization_type="farm")
    other = identity_factory(role="grower", organization_type="farm")

    async with _client() as grower_client:
        await _login(grower_client, grower)
        response = await grower_client.post(
            f"/api/v1/organizations/members/{other.user_id}/deactivate"
        )
        assert response.status_code == 403, response.text
