"""Integration checks for the two staging integrations (N3-160).

The unit tests mock the SMTP transport and the S3 client. These tests run
the real thing on the loopback interface:

* a real SMTP server receives the message the application sends, so the
  "the mail really leaves the outbox" claim is verified end to end;
* a real S3-compatible endpoint stores the dump and gives it back, so the
  "the backup really leaves the application server" claim is verified end
  to end.

Both are bounded, offline and finish in about a second.
"""

import json
import socket
from pathlib import Path

import pytest
from aiosmtpd.controller import Controller
from moto import mock_aws

from app.core.config import settings
from app.services import email_service
from app.services.email_service import deliver_email
from scripts.backup import (
    download_backup_from_external_store,
    sha256_of_file,
    upload_backup_to_external_store,
    verify_checksum,
    write_sidecars,
)


class _RecordingHandler:
    """Keeps every message the SMTP server accepts."""

    def __init__(self):
        self.messages: list[dict[str, str]] = []

    async def handle_DATA(self, server, session, envelope):  # noqa: N802
        self.messages.append(
            {
                "from": envelope.mail_from,
                "to": envelope.rcpt_tos[0] if envelope.rcpt_tos else "",
                "content": envelope.content.decode("utf-8", errors="replace"),
            }
        )
        return "250 Message accepted for delivery"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def smtp_server():
    """Run a real SMTP server on the loopback interface."""
    handler = _RecordingHandler()
    controller = Controller(handler, hostname="127.0.0.1", port=_free_port())
    controller.start()
    try:
        yield handler, controller.server.sockets[0].getsockname()[1]
    finally:
        controller.stop()


def test_the_application_really_delivers_through_the_smtp_transport(
    admin_session, identity_factory, smtp_server, monkeypatch
):
    """A message sent by the application arrives in a real mailbox."""
    handler, port = smtp_server
    identity = identity_factory()

    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "SMTP_PORT", port)
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(settings, "SMTP_FROM", "no-reply@agrochain.test")

    delivery = deliver_email(
        admin_session,
        recipient_email="grower@example.com",
        subject="Loi moi",
        body="body",
        kind=email_service.ORGANIZATION_INVITATION_KIND,
        organization_id=identity.organization_id,
    )

    assert delivery.status == "sent"
    assert len(handler.messages) == 1
    received = handler.messages[0]
    assert received["to"] == "grower@example.com"
    assert received["from"] == "no-reply@agrochain.test"
    assert "Loi moi" in received["content"]

    record = admin_session.get(email_service.EmailOutbox, delivery.id)
    assert record is not None
    assert record.status == "sent"
    assert record.sent_at is not None


def test_a_dump_survives_a_round_trip_through_an_s3_compatible_store(tmp_path):
    """The dump, its manifest and its checksum travel to the store and back."""
    dump = tmp_path / "agrochain-20261021T021500Z.dump"
    dump.write_bytes(b"agrochain-dump-bytes")
    write_sidecars(
        dump,
        sha256=sha256_of_file(dump),
        created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        database_name="ttcs_staging",
        database_host="db.internal",
        counts={"lots": 12, "events": 40},
    )

    with mock_aws():
        import boto3

        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        client.create_bucket(Bucket="ttcs-backups")

        report = upload_backup_to_external_store(
            dump,
            bucket="ttcs-backups",
            prefix="agrochain",
            client=client,
        )
        assert len(report["files"]) == 3
        keys = sorted(
            item["Key"]
            for item in client.list_objects_v2(Bucket="ttcs-backups")["Contents"]
        )
        assert keys == [
            "agrochain/agrochain-20261021T021500Z.dump",
            "agrochain/agrochain-20261021T021500Z.dump.manifest.json",
            "agrochain/agrochain-20261021T021500Z.dump.sha256",
        ]

        # The local copy goes away; only the store keeps the backup.
        dump.unlink()
        dump.with_suffix(dump.suffix + ".manifest.json").unlink()
        dump.with_suffix(dump.suffix + ".sha256").unlink()

        target = download_backup_from_external_store(
            bucket="ttcs-backups",
            prefix="agrochain",
            directory=tmp_path,
            client=client,
        )

    assert target.is_file()
    assert target.read_bytes() == b"agrochain-dump-bytes"
    assert verify_checksum(target) is True
    manifest = json.loads(
        Path(str(target) + ".manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["counts"] == {"lots": 12, "events": 40}


def test_the_external_copy_is_refused_when_the_manifest_is_missing(tmp_path):
    """A copy that cannot be verified must not be presented as usable."""
    dump = tmp_path / "agrochain-20261021T021500Z.dump"
    dump.write_bytes(b"agrochain-dump-bytes")
    write_sidecars(
        dump,
        sha256=sha256_of_file(dump),
        created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        database_name="ttcs_staging",
        database_host="db.internal",
        counts={"lots": 1},
    )

    with mock_aws():
        import boto3

        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        client.create_bucket(Bucket="ttcs-backups")
        upload_backup_to_external_store(
            dump,
            bucket="ttcs-backups",
            prefix="agrochain",
            client=client,
        )
        # The store loses the manifest.
        client.delete_object(
            Bucket="ttcs-backups",
            Key="agrochain/agrochain-20261021T021500Z.dump.manifest.json",
        )

        # The local copies go away too, so only what the store returns is
        # left on disk.
        dump.unlink()
        dump.with_suffix(dump.suffix + ".manifest.json").unlink()
        dump.with_suffix(dump.suffix + ".sha256").unlink()

        target = download_backup_from_external_store(
            bucket="ttcs-backups",
            prefix="agrochain",
            directory=tmp_path,
            client=client,
        )

    assert target.is_file()
    # Without the manifest the copy cannot be verified, so verify_checksum
    # must say so instead of silently accepting it.
    assert verify_checksum(target) is False
