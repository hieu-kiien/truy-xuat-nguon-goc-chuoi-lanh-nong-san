"""Outbound e-mail delivery (N3-57, N3-30).

The service records every message in the outbox before handing it to the
transport, so a delivery that fails still leaves evidence and can be retried.
When no SMTP server is configured the message is only recorded, which keeps a
staging environment honest without pretending a mail was sent.

A message body never carries business data that the recipient must not see:
the recall notice only names the recall code and the path to the order, never
the list of affected lots (N3-57).
"""

import logging
import smtplib
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.email_outbox import EmailOutbox

logger = logging.getLogger(__name__)

RECALL_NOTICE_KIND = "recall_notice"
ORGANIZATION_INVITATION_KIND = "organization_invitation"


@dataclass(frozen=True)
class EmailDelivery:
    """The outcome of one delivery attempt sequence."""

    id: UUID
    recipient_email: str
    kind: str
    status: str
    attempts: int
    error: str | None = None

    @property
    def delivered(self) -> bool:
        return self.status in {"sent", "recorded"}


def _send_via_smtp(recipient: str, subject: str, body: str) -> None:
    """Hand the message to the configured SMTP server."""
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    ) as client:
        if settings.SMTP_USE_TLS:
            client.starttls()
        if settings.SMTP_USER:
            client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        client.send_message(message)


def deliver_email(
    db: Session,
    *,
    recipient_email: str,
    subject: str,
    body: str,
    kind: str,
    organization_id: UUID | None = None,
    related_id: str | None = None,
) -> EmailDelivery:
    """Record and deliver one message, retrying a rejected delivery.

    The record is written first so the attempt history survives a failure.
    A delivery is retried up to ``EMAIL_MAX_ATTEMPTS`` times.
    """
    recipient = recipient_email.strip().lower()
    record = EmailOutbox(
        organization_id=organization_id,
        recipient_email=recipient,
        subject=subject,
        body=body,
        kind=kind,
        related_id=related_id,
        status="recorded",
        attempts=0,
        created_at=datetime.now(UTC),
    )
    db.add(record)
    db.flush()

    if not settings.SMTP_HOST:
        # No transport configured: keep the evidence and report it as recorded.
        db.commit()
        logger.info(
            "Recorded %s message for %s (no SMTP server configured)",
            kind,
            recipient,
        )
        return EmailDelivery(
            id=record.id,
            recipient_email=recipient,
            kind=kind,
            status="recorded",
            attempts=0,
        )

    last_error: str | None = None
    for attempt in range(1, settings.EMAIL_MAX_ATTEMPTS + 1):
        record.attempts = attempt
        try:
            _send_via_smtp(recipient, subject, body)
        except Exception as exc:  # noqa: BLE001 - any transport error is retried
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "E-mail delivery attempt %s/%s failed for %s: %s",
                attempt,
                settings.EMAIL_MAX_ATTEMPTS,
                recipient,
                last_error,
            )
            db.commit()
            if attempt < settings.EMAIL_MAX_ATTEMPTS:
                time.sleep(settings.EMAIL_RETRY_DELAY_SECONDS)
            continue

        record.status = "sent"
        record.sent_at = datetime.now(UTC)
        record.error = None
        db.commit()
        return EmailDelivery(
            id=record.id,
            recipient_email=recipient,
            kind=kind,
            status="sent",
            attempts=attempt,
        )

    record.status = "failed"
    record.error = last_error
    db.commit()
    return EmailDelivery(
        id=record.id,
        recipient_email=recipient,
        kind=kind,
        status="failed",
        attempts=settings.EMAIL_MAX_ATTEMPTS,
        error=last_error,
    )


def recall_notice_body(
    recall_code: str, root_lot_id: UUID, *, organization_name: str
) -> str:
    """Build the recall notice body.

    The body names the recall code and the path to the order only. It never
    lists the affected lots, because the recipient must open the order to see
    them (N3-57 non-functional requirement).
    """
    link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/lots/{root_lot_id}"
    return (
        f"Kính gửi {organization_name},\n\n"
        f"Có một lệnh thu hồi liên quan tới tổ chức của quý vị.\n"
        f"Mã lệnh: {recall_code}\n"
        f"Mở lệnh: {link}\n\n"
        "Trân trọng,\nHệ thống truy xuất nguồn gốc nông sản"
    )


def invitation_body(
    organization_name: str, inviter_name: str, invitation_url: str
) -> str:
    """Build the organization invitation body (N3-30)."""
    return (
        f"{inviter_name} đã mời bạn tham gia tổ chức {organization_name} "
        f"trên hệ thống truy xuất nguồn gốc nông sản.\n\n"
        f"Đặt mật khẩu và nhận quyền: {invitation_url}\n\n"
        "Link mời chỉ dùng được một lần và hết hạn sau 72 giờ."
    )
