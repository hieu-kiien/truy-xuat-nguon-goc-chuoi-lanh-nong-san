from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.api.v1.endpoints import auth as auth_endpoint
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
        assert (await client.get("/api/v1/auth/me")).status_code == 200

        token = client.cookies.get(settings.SESSION_COOKIE_NAME)
        assert token
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

        failures = [
            await client.post(
                "/api/v1/auth/login",
                json={"email": identity.email, "password": "wrong-password"},
            )
            for _ in range(5)
        ]
        assert all(response.status_code == 401 for response in failures)
        assert all(response.json() == unknown.json() for response in failures)

        user = admin_session.get(User, identity.user_id)
        assert user is not None
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


@pytest.mark.asyncio
async def test_demo_login_requires_flag_allowlist_and_explicit_environment(
    identity_factory, monkeypatch
):
    identity = identity_factory()
    monkeypatch.setattr(settings, "ENABLE_DEMO_LOGIN", True)
    monkeypatch.setattr(settings, "APP_ENV", "staging")
    monkeypatch.setattr(auth_endpoint, "DEMO_EMAILS", frozenset({identity.email}))

    async with _client() as client:
        not_allowlisted = await client.post(
            "/api/v1/auth/demo-login",
            json={"email": "not-demo@example.com"},
        )
        assert not_allowlisted.status_code == 404

        response = await client.post(
            "/api/v1/auth/demo-login",
            json={"email": identity.email},
        )
        assert response.status_code == 200, response.text
        assert response.json()["email"] == identity.email
        assert (await client.get("/api/v1/auth/me")).status_code == 200

    for blocked_env in ("production", "prod", "qa"):
        monkeypatch.setattr(settings, "APP_ENV", blocked_env)
        async with _client() as client:
            blocked = await client.post(
                "/api/v1/auth/demo-login",
                json={"email": identity.email},
            )
            assert blocked.status_code == 404
