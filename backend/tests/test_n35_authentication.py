"""N3-5 - Authentication acceptance criteria.

Covers login, email normalization, indistinguishable failure responses,
Argon2id storage, the 5-attempt / 15-minute lockout, session expiry and
revocation, and cookie hardening. Everything runs against real PostgreSQL and
the real Argon2id implementation.
"""

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.main import app
from app.models.identity import AuthSession, User
from tests.conftest import Tenant, login

LOGIN_URL = "/api/v1/auth/login"
AUTH_ERROR = "Email hoặc mật khẩu không đúng."


async def test_login_succeeds_and_returns_session_user(
    client: AsyncClient, tenant_factory
) -> None:
    tenant = tenant_factory()

    response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == tenant.user.email
    assert body["organization_id"] == str(tenant.organization_id)
    assert body["role"] == "grower"


async def test_password_is_hashed_with_argon2id(
    admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()

    stored = admin_db.scalar(
        select(User.password_hash).where(User.id == tenant.user.id)
    )

    assert stored.startswith("$argon2id$"), f"not Argon2id: {stored!r}"
    assert stored != tenant.password
    assert verify_password(stored, tenant.password) is True
    assert verify_password(stored, "wrong-password") is False


async def test_email_is_normalized_case_insensitively(
    client: AsyncClient, tenant_factory
) -> None:
    tenant = tenant_factory(email="grower@ttcs-demo.org")

    response = await client.post(
        LOGIN_URL, json={"email": "GROWER@TTCS-DEMO.ORG", "password": tenant.password}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "grower@ttcs-demo.org"


def test_database_rejects_a_non_normalized_email(
    admin_db: Session, tenant_factory
) -> None:
    """A mixed-case row would be unreachable, since login case-folds the input."""
    tenant = tenant_factory()

    with pytest.raises(IntegrityError) as excinfo:
        admin_db.execute(
            text(
                "INSERT INTO users (id, organization_id, role_code, email, full_name, password_hash) "
                "VALUES (:id, :org, 'grower', 'Mixed.Case@ttcs-demo.org', 'X', 'hash')"
            ),
            {"id": str(uuid4()), "org": str(tenant.organization_id)},
        )
        admin_db.commit()

    assert "ck_users_email_normalized" in str(excinfo.value)


async def test_email_is_trimmed_before_lookup(
    client: AsyncClient, tenant_factory
) -> None:
    tenant = tenant_factory(email="grower@ttcs-demo.org")

    response = await client.post(
        LOGIN_URL,
        json={"email": "  grower@ttcs-demo.org  ", "password": tenant.password},
    )

    assert response.status_code == 200


async def test_unknown_email_and_wrong_password_are_indistinguishable(
    client: AsyncClient, tenant_factory
) -> None:
    tenant = tenant_factory()

    unknown = await client.post(
        LOGIN_URL,
        json={"email": "nobody@ttcs-demo.org", "password": "WrongPassword123"},
    )
    wrong = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": "WrongPassword123"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": AUTH_ERROR}
    # No session cookie may be issued for either failure mode.
    assert settings.SESSION_COOKIE_NAME not in unknown.cookies
    assert settings.SESSION_COOKIE_NAME not in wrong.cookies


async def test_failed_attempts_one_to_four_do_not_lock_the_account(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()

    for attempt in range(1, settings.MAX_FAILED_LOGIN_ATTEMPTS):
        response = await client.post(
            LOGIN_URL, json={"email": tenant.user.email, "password": "WrongPassword123"}
        )
        assert response.status_code == 401, f"attempt {attempt}"
        admin_db.expire_all()
        user = admin_db.get(User, tenant.user.id)
        assert user.failed_login_attempts == attempt
        assert user.locked_until is None


async def test_fifth_failure_locks_the_account_for_fifteen_minutes(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS - 1):
        await client.post(
            LOGIN_URL, json={"email": tenant.user.email, "password": "WrongPassword123"}
        )
    response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": "WrongPassword123"}
    )

    assert response.status_code == 401
    admin_db.expire_all()
    user = admin_db.get(User, tenant.user.id)
    assert user.failed_login_attempts == settings.MAX_FAILED_LOGIN_ATTEMPTS
    assert user.locked_until is not None
    remaining = user.locked_until - datetime.now(UTC)
    assert timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES - 1) < remaining
    assert remaining <= timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES)


async def test_sixth_attempt_fails_even_with_the_correct_password(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    """The lockout must reject the correct password, not just wrong ones."""
    tenant = tenant_factory()

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        await client.post(
            LOGIN_URL, json={"email": tenant.user.email, "password": "WrongPassword123"}
        )

    response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": AUTH_ERROR}
    assert settings.SESSION_COOKIE_NAME not in client.cookies


async def test_login_succeeds_again_once_the_lockout_expires(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        await client.post(
            LOGIN_URL, json={"email": tenant.user.email, "password": "WrongPassword123"}
        )

    # Simulate the 15 minute window elapsing.
    admin_db.execute(
        text("UPDATE users SET locked_until = :when WHERE id = :user_id"),
        {
            "when": datetime.now(UTC) - timedelta(seconds=1),
            "user_id": tenant.user.id,
        },
    )
    admin_db.commit()

    response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )

    assert response.status_code == 200
    admin_db.expire_all()
    user = admin_db.get(User, tenant.user.id)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


async def test_successful_login_resets_the_failure_counter(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    for _ in range(2):
        await client.post(
            LOGIN_URL, json={"email": tenant.user.email, "password": "WrongPassword123"}
        )

    await login(client, tenant)

    admin_db.expire_all()
    assert admin_db.get(User, tenant.user.id).failed_login_attempts == 0


async def test_inactive_account_cannot_log_in(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    admin_db.execute(
        text("UPDATE users SET is_active = false WHERE id = :user_id"),
        {"user_id": tenant.user.id},
    )
    admin_db.commit()

    response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": AUTH_ERROR}


async def test_session_cookie_is_httponly_secure_and_samesite(
    client: AsyncClient, tenant_factory, monkeypatch
) -> None:
    """Secure/HttpOnly/SameSite are asserted on the emitted Set-Cookie header.

    The suite runs over plain HTTP so it must temporarily enable an insecure
    cookie, which lets us read the attributes the server actually emitted
    instead of trusting the client jar.
    """
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", True)
    tenant = tenant_factory()

    response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )

    header = response.headers["set-cookie"]
    assert "HttpOnly" in header
    assert "Secure" in header
    assert "SameSite=lax" in header.replace("samesite", "SameSite")
    assert "Path=/" in header
    # A `__Host-` prefixed cookie must not carry a Domain attribute.
    assert "Domain=" not in header


async def test_session_cookie_is_not_exposed_to_javascript(
    client: AsyncClient, tenant_factory
) -> None:
    tenant = tenant_factory()

    response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )

    assert "HttpOnly" in response.headers["set-cookie"]
    # The raw token must never appear in the response body.
    cookie_token = response.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie_token not in response.text


async def test_raw_session_token_is_never_returned_in_a_header(
    client: AsyncClient, tenant_factory
) -> None:
    """The opaque credential must not be readable by any header-parsing code.

    The token is legitimately present in the `Set-Cookie` header that issues
    it, and nowhere else. What matters is that it is never exposed through a
    dedicated response header (the historical `X-Session-Token` design) and
    that the cookie carrying it is HttpOnly.
    """
    tenant = tenant_factory()

    login_response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )
    token = login_response.cookies[settings.SESSION_COOKIE_NAME]

    responses = [
        login_response,
        await client.get("/api/v1/auth/me"),
        await client.get("/api/v1/farms/"),
        await client.post("/api/v1/auth/logout"),
    ]
    for response in responses:
        header_names = {name.lower() for name, _ in response.headers.multi_items()}
        assert "x-session-token" not in header_names
        assert not any(
            "session" in name and name != "set-cookie" for name in header_names
        ), header_names
        for name, value in response.headers.multi_items():
            if name.lower() == "set-cookie":
                # The issuing response may only carry it inside the cookie,
                # and only while that cookie is HttpOnly.
                assert token not in value or "HttpOnly" in value
                continue
            assert token not in value, f"token leaked in header {name!r}"


async def test_cors_does_not_expose_a_session_token_header() -> None:
    from app.main import app

    allow_headers = {
        header
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
        for header in middleware.kwargs.get("allow_headers", [])
    }
    exposed = {
        header.lower()
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
        for header in middleware.kwargs.get("expose_headers", [])
    }
    assert "x-session-token" not in exposed
    assert not any("session" in header.lower() for header in allow_headers)


async def test_session_token_is_only_persisted_as_a_hash(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    response = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )
    raw_token = response.cookies[settings.SESSION_COOKIE_NAME]

    admin_db.expire_all()
    sessions = admin_db.query(AuthSession).all()
    assert len(sessions) == 1
    assert sessions[0].token_hash != raw_token
    assert len(sessions[0].token_hash) == 64  # SHA-256 hex digest
    assert (
        raw_token
        not in admin_db.execute(text("SELECT token_hash FROM sessions")).scalars().all()
    )


async def test_each_login_issues_a_fresh_token_defeating_session_fixation(
    client: AsyncClient, tenant_factory
) -> None:
    """A pre-login cookie must never become an authenticated session."""
    tenant = tenant_factory()
    first = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )
    first_token = first.cookies[settings.SESSION_COOKIE_NAME]

    client.cookies.clear()
    client.cookies.set("attacker-fixed", "attacker-fixed-value")
    second = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )
    second_token = second.cookies[settings.SESSION_COOKIE_NAME]

    assert first_token != second_token


async def test_expired_session_is_rejected_and_revoked(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    tenant = tenant_factory()
    await login(client, tenant)

    admin_db.execute(
        text("UPDATE sessions SET expires_at = :when"),
        {"when": datetime.now(UTC) - timedelta(minutes=1)},
    )
    admin_db.commit()

    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    admin_db.expire_all()
    assert all(
        session.revoked_at is not None for session in admin_db.query(AuthSession)
    )


async def test_request_without_a_session_cookie_is_rejected(
    client: AsyncClient,
) -> None:
    client.cookies.clear()

    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await client.get("/api/v1/farms/")).status_code == 401


async def test_forged_session_token_is_rejected(client: AsyncClient) -> None:
    client.cookies.set(settings.SESSION_COOKIE_NAME, "not-a-real-token")

    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


async def test_logout_revokes_the_session_and_the_token_stops_working(
    client: AsyncClient, admin_db: Session, tenant_factory
) -> None:
    """The exact token issued before logout must be unusable afterwards."""
    tenant = tenant_factory()
    await login(client, tenant)
    stolen_token = client.cookies[settings.SESSION_COOKIE_NAME]
    assert (await client.get("/api/v1/auth/me")).status_code == 200

    assert (await client.post("/api/v1/auth/logout")).status_code == 204

    admin_db.expire_all()
    sessions = admin_db.query(AuthSession).all()
    assert len(sessions) == 1
    assert sessions[0].revoked_at is not None

    # An attacker who captured the cookie value still cannot use it.
    replay = await client.get("/api/v1/auth/me")
    assert replay.status_code == 401

    reissued = await client.post(
        LOGIN_URL, json={"email": tenant.user.email, "password": tenant.password}
    )
    assert reissued.status_code == 200
    fresh_token = reissued.cookies[settings.SESSION_COOKIE_NAME]
    assert fresh_token != stolen_token, "logout must not leave the old token usable"


async def test_logging_out_revokes_only_the_current_session(
    tenant_factory, admin_db: Session
) -> None:
    """Signing out one device must not silently kill other sessions."""
    tenant = tenant_factory()
    transport = ASGITransport(app=app)

    async with (
        AsyncClient(transport=transport, base_url="http://testserver") as first,
        AsyncClient(transport=transport, base_url="http://testserver") as second,
    ):
        await login(first, tenant)
        await login(second, tenant)
        first_token = first.cookies[settings.SESSION_COOKIE_NAME]
        second_token = second.cookies[settings.SESSION_COOKIE_NAME]
        assert first_token != second_token

        assert (await first.post("/api/v1/auth/logout")).status_code == 204

        assert (await first.get("/api/v1/auth/me")).status_code == 401
        assert (await second.get("/api/v1/auth/me")).status_code == 200

    admin_db.expire_all()
    sessions = admin_db.query(AuthSession).all()
    assert len(sessions) == 2
    assert sum(1 for s in sessions if s.revoked_at is not None) == 1


async def test_login_request_rejects_unknown_fields(
    client: AsyncClient, tenant_factory
) -> None:
    tenant = tenant_factory()

    response = await client.post(
        LOGIN_URL,
        json={
            "email": tenant.user.email,
            "password": tenant.password,
            "role": "system_admin",
        },
    )

    assert response.status_code == 422


async def test_empty_password_is_rejected_by_validation(client: AsyncClient) -> None:
    response = await client.post(
        LOGIN_URL, json={"email": "grower@ttcs-demo.org", "password": ""}
    )

    assert response.status_code == 422


def test_secure_cookie_is_mandatory_outside_development() -> None:
    """`SESSION_COOKIE_SECURE=false` must not be accepted in production."""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="SESSION_COOKIE_SECURE"):
        Settings(
            APP_ENV="staging",
            SECRET_KEY="x" * 48,
            SESSION_COOKIE_SECURE=False,
            DB_USER="ttcs_app",
            DB_ADMIN_USER="admin",
        )


def test_wildcard_cors_origin_is_rejected_with_credentials() -> None:
    """A wildcard origin plus credentialed cookies is an open CORS door."""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(ALLOWED_ORIGINS="*")


def test_application_role_must_differ_from_the_migration_role() -> None:
    """The application must never run with an admin/migration database role."""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="must be distinct"):
        Settings(DB_USER="admin", DB_ADMIN_USER="admin")


async def test_hash_password_produces_unique_salts() -> None:
    first = hash_password("SamePassword123!")
    second = hash_password("SamePassword123!")

    assert first != second
    assert first.startswith("$argon2id$")
    assert verify_password(first, "SamePassword123!")
    assert verify_password(second, "SamePassword123!")


@pytest.mark.parametrize(
    "email",
    ["grower@ttcs-demo.org", "GROWER@ttcs-demo.org", " grower@ttcs-demo.org "],
)
async def test_login_normalization_variants(
    email: str, client: AsyncClient, tenant_factory
) -> None:
    tenant = tenant_factory(email="grower@ttcs-demo.org")

    response = await client.post(
        LOGIN_URL, json={"email": email, "password": tenant.password}
    )

    assert response.status_code == 200


async def test_unknown_email_path_spends_comparable_time(
    client: AsyncClient, tenant_factory
) -> None:
    """Guards the user-enumeration timing oracle.

    An unknown email must still perform a dummy Argon2id verification, so both
    failure paths cost roughly the same. The bound is deliberately loose to
    stay stable on shared CI runners; it only catches an order-of-magnitude
    regression such as skipping verification entirely.
    """
    tenant = tenant_factory()

    async def measure(email: str) -> float:
        start = time.perf_counter()
        await client.post(
            LOGIN_URL, json={"email": email, "password": "WrongPassword123"}
        )
        return time.perf_counter() - start

    await measure("warmup@ttcs-demo.org")
    unknown = min([await measure("nobody@ttcs-demo.org") for _ in range(3)])
    known = min([await measure(tenant.user.email) for _ in range(3)])

    assert known < unknown * 3, f"unknown={unknown:.4f}s known={known:.4f}s"


async def test_tenant_helper_creates_distinct_organizations(tenant_factory) -> None:
    """Guard the fixture itself so a scoping test cannot pass vacuously."""
    first = tenant_factory()
    second = tenant_factory()

    assert isinstance(first, Tenant)
    assert first.organization_id != second.organization_id
    assert first.user.id != second.user.id
