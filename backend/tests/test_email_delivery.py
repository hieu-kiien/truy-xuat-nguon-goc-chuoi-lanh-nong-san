"""Outbound e-mail delivery must really leave the outbox (N3-160).

The acceptance criterion is not "the message was recorded" but "the recall
notice and the member invitation actually went out". These tests cover both
sides of that line: without an SMTP host nothing is sent, and with one the
message reaches the transport and the outbox row is marked as sent.
"""

import smtplib

from app.core.config import settings
from app.services import email_service
from app.services.email_service import deliver_email


def test_without_an_smtp_host_the_message_stays_in_the_outbox(
    admin_session, identity_factory, monkeypatch
):
    identity = identity_factory()
    monkeypatch.setattr(settings, "SMTP_HOST", "")

    contacted = {"count": 0}

    class UnreachableSMTP:
        def __init__(self, *args, **kwargs):
            contacted["count"] += 1
            raise AssertionError("SMTP must not be contacted without a host")

    monkeypatch.setattr(smtplib, "SMTP", UnreachableSMTP)

    delivery = deliver_email(
        admin_session,
        recipient_email="grower@example.com",
        subject="Loi moi",
        body="body",
        kind=email_service.ORGANIZATION_INVITATION_KIND,
        organization_id=identity.organization_id,
    )

    assert delivery.status == "recorded"
    assert delivery.attempts == 0
    assert contacted["count"] == 0


def test_with_an_smtp_host_the_message_is_handed_to_the_transport(
    admin_session, identity_factory, monkeypatch
):
    identity = identity_factory()
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USER", "mailer")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)

    seen: dict[str, object] = {}

    class RecordingSMTP:
        def __init__(self, host, port, timeout=None):
            seen["host"] = host
            seen["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def ehlo(self):
            return 250, b"ok"

        def starttls(self):
            seen["tls"] = True

        def login(self, user, password):
            seen["login"] = (user, password)

        def send_message(self, message):
            seen["to"] = message["To"]
            seen["subject"] = message["Subject"]

    monkeypatch.setattr(smtplib, "SMTP", RecordingSMTP)

    delivery = deliver_email(
        admin_session,
        recipient_email="grower@example.com",
        subject="Loi moi",
        body="body",
        kind=email_service.ORGANIZATION_INVITATION_KIND,
        organization_id=identity.organization_id,
    )

    assert delivery.status == "sent"
    assert delivery.delivered is True
    assert delivery.attempts == 1
    assert seen["host"] == "smtp.example.test"
    assert seen["port"] == 587
    assert seen["tls"] is True
    assert seen["login"] == ("mailer", "app-password")
    assert seen["to"] == "grower@example.com"

    record = admin_session.get(email_service.EmailOutbox, delivery.id)
    assert record is not None
    assert record.status == "sent"
    assert record.sent_at is not None
    assert record.error is None


def test_a_transport_error_is_retried_and_reported(
    admin_session, identity_factory, monkeypatch
):
    identity = identity_factory()
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "EMAIL_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(settings, "EMAIL_RETRY_DELAY_SECONDS", 0.0)

    attempts = {"count": 0}

    class FailingSMTP:
        def __init__(self, *args, **kwargs):
            attempts["count"] += 1

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def ehlo(self):
            return 250, b"ok"

        def starttls(self):
            return None

        def login(self, user, password):
            return None

        def send_message(self, message):
            raise smtplib.SMTPConnectError(421, "service unavailable")

    monkeypatch.setattr(smtplib, "SMTP", FailingSMTP)

    delivery = deliver_email(
        admin_session,
        recipient_email="grower@example.com",
        subject="Loi moi",
        body="body",
        kind=email_service.ORGANIZATION_INVITATION_KIND,
        organization_id=identity.organization_id,
    )

    assert delivery.status == "failed"
    assert delivery.delivered is False
    assert delivery.attempts == 2
    assert attempts["count"] == 2

    record = admin_session.get(email_service.EmailOutbox, delivery.id)
    assert record is not None
    assert record.status == "failed"
    assert "SMTPConnectError" in (record.error or "")
