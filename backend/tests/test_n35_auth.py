from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from app.core.config import settings
from app.core.security import hash_session_token
from app.main import app
from app.models.identity import AuthSession, User
from tests.conftest import IdentityFixture


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


async def _login(client: AsyncClient, identity: IdentityFixture) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": identity.email, "password": identity.password},
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_login_hash_cookie_session_expiration_and_logout(
    admin_session, identity_factory
):
    identity = identity_factory()
    stored_user = admin_session.get(User, identity.user_id)
    assert stored_user is not None
    assert stored_user.password_hash.startswith("$argon2id$")

    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": identity.email.upper(), "password": identity.password},
        )
        assert response.status_code == 200, response.text
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie
        assert "secure" in cookie
        assert f"max-age={settings.SESSION_TTL_MINUTES * 60}" in cookie
        assert "x-session-token" not in response.headers
        assert (await client.get("/api/v1/auth/me")).status_code == 200

        token = client.cookies.get(settings.SESSION_COOKIE_NAME)
        assert token
        assert token not in response.text
        session = admin_session.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == hash_session_token(token)
            )
        )
        assert session is not None
        assert session.token_hash != token
        async with _client() as header_only_client:
            header_only = await header_only_client.get(
                "/api/v1/auth/me", headers={"X-Session-Token": token}
            )
            assert header_only.status_code == 401

        admin_session.execute(
            update(AuthSession)
            .where(AuthSession.token_hash == hash_session_token(token))
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        admin_session.commit()
        assert (await client.get("/api/v1/auth/me")).status_code == 401

        await _login(client, identity)
        logout = await client.post("/api/v1/auth/logout")
        assert logout.status_code == 204
        assert "max-age=0" in logout.headers["set-cookie"].lower()
        assert (await client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_login_error_is_generic_and_fifth_failure_locks_for_15_minutes(
    admin_session, identity_factory
):
    identity = identity_factory()
    async with _client() as client:
        unknown = await client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
        )
        assert unknown.status_code == 401

        first_four_failures = [
            await client.post(
                "/api/v1/auth/login",
                json={"email": identity.email, "password": "wrong-password"},
            )
            for _ in range(4)
        ]
        assert all(response.status_code == 401 for response in first_four_failures)
        assert all(
            response.json() == unknown.json() for response in first_four_failures
        )

        user = admin_session.get(User, identity.user_id)
        assert user is not None
        admin_session.refresh(user)
        assert user.failed_login_attempts == 4
        assert user.locked_until is None

        fifth_failure = await client.post(
            "/api/v1/auth/login",
            json={"email": identity.email, "password": "wrong-password"},
        )
        assert fifth_failure.status_code == 401
        assert fifth_failure.json() == unknown.json()
        admin_session.refresh(user)
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
        remaining = user.locked_until - datetime.now(UTC)
        assert timedelta(minutes=14, seconds=50) < remaining <= timedelta(minutes=15)

        correct_while_locked = await client.post(
            "/api/v1/auth/login",
            json={"email": identity.email, "password": identity.password},
        )
        assert correct_while_locked.status_code == 401
        assert correct_while_locked.json() == unknown.json()

        user.locked_until = datetime.now(UTC) - timedelta(seconds=1)
        admin_session.commit()
        unlocked = await client.post(
            "/api/v1/auth/login",
            json={"email": identity.email, "password": identity.password},
        )
        assert unlocked.status_code == 200
        admin_session.refresh(user)
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


@pytest.mark.asyncio
async def test_cors_does_not_expose_session_credentials():
    async with _client() as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert "access-control-expose-headers" not in response.headers
