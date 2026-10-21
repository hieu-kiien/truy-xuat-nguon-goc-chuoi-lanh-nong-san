"""Send a real probe message through the configured SMTP server (N3-160).

Until an SMTP host is configured the application only records a message in
``email_outbox``; the recall notice and the member invitation never leave
the database. This script proves the opposite: it opens a connection to the
configured server, sends one message and reports what happened.

    python scripts/check_smtp.py --recipient canh-kiem@ictu.edu.vn

The script never prints the SMTP password and never prints the contents of
the probe message. It exits with 0 when the server accepted the message and
with 2 when no transport is configured at all.
"""

from __future__ import annotations

import argparse
import json
import smtplib
import sys
import time
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is in python path
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings  # noqa: E402

PROBE_SUBJECT = "[Kiem tra ha tang] Thu thu truoc khi kiem tra thu"


def build_probe_message(recipient: str) -> EmailMessage:
    """Build the probe message.

    The body says only that this is a connectivity check. It carries no
    business data and no credential.
    """
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = recipient
    message["Subject"] = PROBE_SUBJECT
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain="agrochain.local")
    message.set_content(
        "Day la thu kiem tra ha tang.\n"
        "Neu ban doc duoc thu nay, SMTP tren staging da duoc cau hinh dung.\n"
        "Thu nay khong chua du lieu nghiep vu.\n"
    )
    return message


def run_probe(recipient: str) -> dict[str, object]:
    """Open a connection, send the probe and describe the outcome."""
    if not settings.smtp_configured:
        return {
            "ok": False,
            "sent": False,
            "reason": "smtp_not_configured",
            "detail": (
                "SMTP_HOST is empty. Messages only reach the email_outbox table. "
                "Set SMTP_HOST, SMTP_PORT, SMTP_USER and SMTP_PASSWORD on the "
                "staging service and run this script again."
            ),
        }

    started = time.perf_counter()
    report: dict[str, object] = {
        "ok": False,
        "sent": False,
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "smtp_tls": settings.SMTP_USE_TLS,
        "smtp_user": settings.SMTP_USER,
        "from": settings.SMTP_FROM,
        "recipient": recipient,
    }

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        ) as client:
            client.ehlo()
            if settings.SMTP_USE_TLS:
                client.starttls()
                client.ehlo()
            if settings.SMTP_USER:
                client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            refused = client.send_message(build_probe_message(recipient))
    except Exception as error:  # noqa: BLE001 - report any transport failure
        report["reason"] = "transport_error"
        report["error"] = f"{type(error).__name__}: {error}"
        report["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        return report

    report["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    report["refused_recipients"] = sorted(refused or {})
    if refused:
        report["reason"] = "recipient_refused"
        return report

    report["ok"] = True
    report["sent"] = True
    report["reason"] = "delivered"
    return report


def main() -> int:
    """CLI entrypoint for the SMTP probe."""
    parser = argparse.ArgumentParser(
        description="Probe the configured SMTP server (N3-160)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--recipient",
        required=True,
        help="Address that receives the probe message",
    )
    args = parser.parse_args()

    report = run_probe(args.recipient)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get("sent"):
        return 0
    if report.get("reason") == "smtp_not_configured":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
