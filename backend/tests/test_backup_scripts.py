"""Unit tests for the database backup and recovery tooling (N3-76).

These tests never touch a real database: they cover the naming, the
checksums, the manifest and the retention policy, which are the parts that
decide whether a backup can still be trusted.
"""

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import backup as backup_module
from scripts.backup import (
    BACKUP_PREFIX,
    BackupRecord,
    build_backup_filename,
    build_object_key,
    build_pg_dump_command,
    build_pg_restore_command,
    download_backup_from_external_store,
    list_backups,
    prune_backups,
    read_manifest,
    sha256_of_file,
    to_postgres_url,
    upload_backup_to_external_store,
    verify_checksum,
    write_sidecars,
)

SAMPLE_URL = "postgresql+psycopg://ttcs_admin:s3cret@db.internal:5432/ttcs_staging"


def _make_dump(
    directory: Path, moment: datetime, payload: bytes = b"dump-bytes"
) -> Path:
    path = directory / build_backup_filename(moment)
    path.write_bytes(payload)
    write_sidecars(
        path,
        sha256=sha256_of_file(path),
        created_at=moment,
        database_name="ttcs_staging",
        database_host="db.internal",
        counts={"lots": 12, "events": 40},
    )
    return path


def test_backup_filename_is_utc_and_sortable():
    moment = datetime(2026, 10, 21, 2, 15, 0, tzinfo=UTC)
    name = build_backup_filename(moment)
    assert name == f"{BACKUP_PREFIX}20261021T021500Z.dump"


def test_backup_filename_converts_local_time_to_utc():
    moment = datetime(2026, 10, 21, 9, 15, 0, tzinfo=timezone(timedelta(hours=7)))
    assert build_backup_filename(moment).endswith("20261021T021500Z.dump")


def test_sha256_matches_known_digest(tmp_path):
    path = tmp_path / "sample.dump"
    path.write_bytes(b"agrochain")
    assert sha256_of_file(path) == (
        "603f3dd18a20847a61b14e548d82c4535ee343cf8f2082b253de472feeedc0fb"
    )


def test_sidecars_store_checksum_and_counts(tmp_path):
    moment = datetime(2026, 10, 21, 2, 15, 0, tzinfo=UTC)
    path = _make_dump(tmp_path, moment)

    manifest = read_manifest(path)
    assert manifest["file"] == path.name
    assert manifest["sha256"] == sha256_of_file(path)
    assert manifest["counts"] == {"lots": 12, "events": 40}
    assert manifest["database_host"] == "db.internal"

    checksum_file = path.with_suffix(path.suffix + ".sha256")
    assert checksum_file.read_text(encoding="utf-8").startswith(manifest["sha256"])


def test_manifest_never_stores_the_password(tmp_path):
    moment = datetime(2026, 10, 21, 2, 15, 0, tzinfo=UTC)
    path = _make_dump(tmp_path, moment)
    assert "s3cret" not in json.dumps(read_manifest(path))


def test_list_backups_returns_newest_first(tmp_path):
    base = datetime(2026, 10, 21, 2, 0, 0, tzinfo=UTC)
    _make_dump(tmp_path, base)
    _make_dump(tmp_path, base + timedelta(days=1))
    _make_dump(tmp_path, base + timedelta(days=2))

    records = list_backups(tmp_path)
    assert [record.name for record in records] == [
        f"{BACKUP_PREFIX}20261023T020000Z.dump",
        f"{BACKUP_PREFIX}20261022T020000Z.dump",
        f"{BACKUP_PREFIX}20261021T020000Z.dump",
    ]


def test_list_backups_ignores_foreign_files(tmp_path):
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    _make_dump(tmp_path, datetime(2026, 10, 21, 2, 0, 0, tzinfo=UTC))
    records = list_backups(tmp_path)
    assert len(records) == 1
    assert records[0].name.endswith(".dump")


def test_list_backups_on_missing_directory_is_empty(tmp_path):
    assert list_backups(tmp_path / "nope") == []


def test_prune_keeps_only_the_newest_backups(tmp_path):
    base = datetime(2026, 10, 21, 2, 0, 0, tzinfo=UTC)
    for day in range(5):
        _make_dump(tmp_path, base + timedelta(days=day))

    removed = prune_backups(tmp_path, keep=2)

    remaining = list_backups(tmp_path)
    assert len(remaining) == 2
    assert remaining[0].name == f"{BACKUP_PREFIX}20261025T020000Z.dump"
    # The dump and both sidecars of the removed backups are gone.
    assert removed
    assert not (tmp_path / f"{BACKUP_PREFIX}20261021T020000Z.dump").exists()
    assert not (
        tmp_path / f"{BACKUP_PREFIX}20261021T020000Z.dump.manifest.json"
    ).exists()
    assert not (tmp_path / f"{BACKUP_PREFIX}20261021T020000Z.dump.sha256").exists()


def test_prune_rejects_a_keep_value_below_one(tmp_path):
    with pytest.raises(ValueError):
        prune_backups(tmp_path, keep=0)


def test_verify_checksum_detects_a_damaged_dump(tmp_path):
    moment = datetime(2026, 10, 21, 2, 15, 0, tzinfo=UTC)
    path = _make_dump(tmp_path, moment)
    assert verify_checksum(path) is True

    path.write_bytes(b"tampered")
    assert verify_checksum(path) is False


def test_verify_checksum_is_false_without_a_manifest(tmp_path):
    path = tmp_path / "agrochain-20261021T021500Z.dump"
    path.write_bytes(b"no manifest")
    assert verify_checksum(path) is False


def test_postgres_url_drops_the_sqlalchemy_driver():
    assert to_postgres_url(SAMPLE_URL) == (
        "postgresql://ttcs_admin:s3cret@db.internal:5432/ttcs_staging"
    )
    assert to_postgres_url("postgres://a:b@h/c") == "postgresql://a:b@h/c"


def test_pg_dump_command_writes_a_custom_format_file(tmp_path):
    target = tmp_path / "out.dump"
    command = build_pg_dump_command(SAMPLE_URL, target)
    assert command[0] == "pg_dump"
    assert "--format=custom" in command
    assert str(target) in command
    assert command[-1] == to_postgres_url(SAMPLE_URL)


def test_pg_restore_command_cleans_the_target_database(tmp_path):
    dump = tmp_path / "in.dump"
    command = build_pg_restore_command(dump, SAMPLE_URL)
    assert command[0] == "pg_restore"
    assert "--clean" in command
    assert "--if-exists" in command
    assert str(dump) in command
    assert to_postgres_url(SAMPLE_URL) in command


def test_pg_restore_command_can_skip_the_clean_step(tmp_path):
    command = build_pg_restore_command(tmp_path / "in.dump", SAMPLE_URL, clean=False)
    assert "--clean" not in command


def test_backup_record_serializes_without_the_password(tmp_path):
    moment = datetime(2026, 10, 21, 2, 15, 0, tzinfo=UTC)
    record = BackupRecord(
        path=tmp_path / "a.dump",
        created_at=moment,
        size_bytes=10,
        sha256="abc",
        database_name="ttcs_staging",
        database_host="db.internal",
        counts={"lots": 1},
    )
    payload = record.to_dict()
    assert payload["created_at"] == moment.isoformat()
    assert payload["counts"] == {"lots": 1}
    assert "s3cret" not in json.dumps(payload)


def test_safe_target_hides_the_password():
    safe = backup_module._safe_target(SAMPLE_URL)
    assert safe == "db.internal:5432/ttcs_staging"
    assert "s3cret" not in safe


class FakeS3Client:
    """Records the uploads instead of talking to a real bucket."""

    def __init__(self, objects=None):
        self.uploads: list[tuple[str, str, str]] = []
        self.downloads: list[tuple[str, str, str]] = []
        self.objects = objects or []

    def upload_file(self, path, bucket, key):
        self.uploads.append((path, bucket, key))

    def list_objects_v2(self, Bucket, Prefix):
        return {
            "Contents": [
                {"Key": key, "Size": 1}
                for key in self.objects
                if key.startswith(Prefix)
            ]
        }

    def download_file(self, bucket, key, target):
        self.downloads.append((bucket, key, target))
        Path(target).write_bytes(b"downloaded-dump")


def test_object_key_joins_the_prefix_and_the_file_name():
    assert build_object_key("agrochain", "a.dump") == "agrochain/a.dump"
    assert build_object_key("/agrochain/", "a.dump") == "agrochain/a.dump"
    assert build_object_key("", "a.dump") == "a.dump"


def test_the_external_copy_ships_the_dump_with_its_manifest_and_checksum(tmp_path):
    moment = datetime(2026, 10, 21, 2, 15, 0, tzinfo=UTC)
    dump = _make_dump(tmp_path, moment)
    client = FakeS3Client()

    report = upload_backup_to_external_store(
        dump,
        bucket="ttcs-backups",
        prefix="agrochain",
        client=client,
    )

    uploaded_keys = sorted(key for _, _, key in client.uploads)
    assert uploaded_keys == [
        "agrochain/agrochain-20261021T021500Z.dump",
        "agrochain/agrochain-20261021T021500Z.dump.manifest.json",
        "agrochain/agrochain-20261021T021500Z.dump.sha256",
    ]
    assert all(bucket == "ttcs-backups" for _, bucket, _ in client.uploads)
    assert report["bucket"] == "ttcs-backups"
    assert len(report["files"]) == 3


def test_the_external_copy_refuses_a_dump_without_its_sidecars(tmp_path):
    moment = datetime(2026, 10, 21, 2, 15, 0, tzinfo=UTC)
    dump = _make_dump(tmp_path, moment)
    dump.with_suffix(dump.suffix + ".sha256").unlink()

    with pytest.raises(FileNotFoundError):
        upload_backup_to_external_store(
            dump,
            bucket="ttcs-backups",
            client=FakeS3Client(),
        )


def test_the_external_copy_needs_a_bucket(tmp_path):
    moment = datetime(2026, 10, 21, 2, 15, 0, tzinfo=UTC)
    dump = _make_dump(tmp_path, moment)
    with pytest.raises(ValueError, match="bucket"):
        upload_backup_to_external_store(dump, bucket="  ", client=FakeS3Client())


def test_downloading_picks_the_newest_dump_from_the_store(tmp_path):
    client = FakeS3Client(
        objects=[
            "agrochain/agrochain-20261020T021500Z.dump",
            "agrochain/agrochain-20261022T021500Z.dump",
            "agrochain/agrochain-20261021T021500Z.dump.manifest.json",
        ]
    )

    target = download_backup_from_external_store(
        bucket="ttcs-backups",
        prefix="agrochain",
        directory=tmp_path,
        client=client,
    )

    assert target.name == "agrochain-20261022T021500Z.dump"
    assert client.downloads == [
        ("ttcs-backups", "agrochain/agrochain-20261022T021500Z.dump", str(target))
    ]


def test_downloading_without_any_dump_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        download_backup_from_external_store(
            bucket="ttcs-backups",
            prefix="agrochain",
            directory=tmp_path,
            client=FakeS3Client(objects=["agrochain/readme.txt"]),
        )
