"""Nightly database backup, retention policy and recovery drill (N3-76).

Backup:
    python scripts/backup.py backup --directory /var/backups/agrochain

List and retention:
    python scripts/backup.py list --directory /var/backups/agrochain
    python scripts/backup.py prune --directory /var/backups/agrochain --keep 14

Recovery drill (restores into a scratch database and measures the time):
    python scripts/backup.py drill --dump <file.dump> --target postgresql://...

The dump is produced with ``pg_dump --format=custom`` so a restore can run
selectively. Every dump is written next to a manifest that records the
checksum and the row counts of the business tables, so a restore drill can
prove that the restored copy still holds the same data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure backend root is in python path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("backup")

BACKUP_PREFIX = "agrochain-"
BACKUP_SUFFIX = ".dump"
MANIFEST_SUFFIX = ".manifest.json"
CHECKSUM_SUFFIX = ".sha256"
DEFAULT_KEEP = 14

# Business tables whose row counts are recorded to prove a restore is complete.
COUNTED_TABLES = (
    "organizations",
    "users",
    "lots",
    "events",
    "shipments",
    "temperature_readings",
    "cold_chain_violations",
    "integrity_checks",
    "recall_orders",
)


@dataclass(frozen=True)
class BackupRecord:
    """One backup file together with the metadata stored next to it."""

    path: Path
    created_at: datetime
    size_bytes: int
    sha256: str
    database_name: str | None = None
    database_host: str | None = None
    counts: dict[str, int] | None = None

    @property
    def name(self) -> str:
        return self.path.name

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record for the CLI output."""
        return {
            "path": str(self.path),
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "database_name": self.database_name,
            "database_host": self.database_host,
            "counts": self.counts or {},
        }


def build_backup_filename(now: datetime | None = None) -> str:
    """Name a dump after the UTC moment it was taken."""
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return f"{BACKUP_PREFIX}{moment.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}{BACKUP_SUFFIX}"


def sha256_of_file(path: Path) -> str:
    """Stream a file and return its hex digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sidecars(
    dump_path: Path,
    *,
    sha256: str,
    created_at: datetime,
    database_name: str | None,
    database_host: str | None,
    counts: dict[str, int] | None,
) -> Path:
    """Write the manifest and the sha256 file that travel with a dump."""
    manifest_path = dump_path.with_suffix(dump_path.suffix + MANIFEST_SUFFIX)
    manifest = {
        "file": dump_path.name,
        "created_at": created_at.isoformat(),
        "size_bytes": dump_path.stat().st_size,
        "sha256": sha256,
        "database_name": database_name,
        "database_host": database_host,
        "counts": counts or {},
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    dump_path.with_suffix(dump_path.suffix + CHECKSUM_SUFFIX).write_text(
        f"{sha256}  {dump_path.name}\n", encoding="utf-8"
    )
    return manifest_path


def read_manifest(dump_path: Path) -> dict[str, Any]:
    """Read the manifest that belongs to a dump."""
    manifest_path = dump_path.with_suffix(dump_path.suffix + MANIFEST_SUFFIX)
    if not manifest_path.is_file():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def list_backups(directory: Path | str) -> list[BackupRecord]:
    """List every dump in a directory, newest first."""
    root = Path(directory)
    if not root.is_dir():
        return []
    records: list[BackupRecord] = []
    for path in sorted(root.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}")):
        manifest = read_manifest(path)
        created_at = datetime.now(UTC)
        if manifest.get("created_at"):
            try:
                created_at = datetime.fromisoformat(manifest["created_at"])
            except ValueError:
                pass
        records.append(
            BackupRecord(
                path=path,
                created_at=created_at,
                size_bytes=manifest.get("size_bytes", path.stat().st_size),
                sha256=manifest.get("sha256", ""),
                database_name=manifest.get("database_name"),
                database_host=manifest.get("database_host"),
                counts=manifest.get("counts") or None,
            )
        )
    records.sort(key=lambda record: record.created_at, reverse=True)
    return records


def prune_backups(directory: Path | str, keep: int = DEFAULT_KEEP) -> list[Path]:
    """Delete the oldest dumps so only ``keep`` of them remain."""
    if keep < 1:
        raise ValueError("keep must be at least 1")
    removed: list[Path] = []
    for record in list_backups(directory)[keep:]:
        for path in (
            record.path,
            record.path.with_suffix(record.path.suffix + MANIFEST_SUFFIX),
            record.path.with_suffix(record.path.suffix + CHECKSUM_SUFFIX),
        ):
            if path.exists():
                path.unlink()
                removed.append(path)
    return removed


def to_postgres_url(url: str) -> str:
    """Turn a SQLAlchemy URL into the plain scheme the PostgreSQL tools accept."""
    for prefix in ("postgresql+psycopg://", "postgresql+pg8000://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix) :]
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def build_pg_dump_command(
    database_url: str, target: Path, pg_dump_binary: str = "pg_dump"
) -> list[str]:
    """Build the pg_dump invocation that writes a custom format dump."""
    return [
        pg_dump_binary,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(target),
        to_postgres_url(database_url),
    ]


def build_pg_restore_command(
    dump_path: Path,
    database_url: str,
    pg_restore_binary: str = "pg_restore",
    *,
    clean: bool = True,
) -> list[str]:
    """Build the pg_restore invocation that loads a dump into a database."""
    command = [pg_restore_binary, "--no-owner", "--no-privileges"]
    if clean:
        command += ["--clean", "--if-exists"]
    command += ["--dbname", to_postgres_url(database_url), str(dump_path)]
    return command


def collect_table_counts(database_url: str, tables: tuple[str, ...]) -> dict[str, int]:
    """Count the rows of the business tables so a restore can be verified."""
    import psycopg

    counts: dict[str, int] = {}
    with psycopg.connect(to_postgres_url(database_url)) as connection:
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(f"SELECT count(*) FROM public.{table}")  # noqa: S608
                row = cursor.fetchone()
                counts[table] = int(row[0]) if row else 0
    return counts


def verify_table_counts(
    database_url: str, expected: dict[str, int]
) -> dict[str, dict[str, int | None]]:
    """Compare the restored row counts with the counts taken at backup time."""
    actual = collect_table_counts(database_url, tuple(expected.keys()))
    report: dict[str, dict[str, int | None]] = {}
    for table, expected_count in expected.items():
        actual_count = actual.get(table)
        report[table] = {
            "expected": expected_count,
            "actual": actual_count,
            "matches": actual_count == expected_count,
        }
    return report


def run_command(command: list[str]) -> None:
    """Run a PostgreSQL tool and fail loudly when it does not succeed."""
    logger.info("Running: %s", " ".join(command[:1] + ["..."] + command[-1:]))
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"{command[0]} failed with exit code {completed.returncode}: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )


def run_backup(
    directory: Path | str,
    database_url: str,
    *,
    keep: int = DEFAULT_KEEP,
    pg_dump_binary: str = "pg_dump",
    now: datetime | None = None,
    skip_counts: bool = False,
) -> BackupRecord:
    """Take one dump, write its sidecars and apply the retention policy."""
    if shutil.which(pg_dump_binary) is None and not Path(pg_dump_binary).is_file():
        raise RuntimeError(
            f"'{pg_dump_binary}' was not found. Install the PostgreSQL client tools first."
        )
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    moment = now or datetime.now(UTC)
    target = root / build_backup_filename(moment)

    counts: dict[str, int] | None = None
    if not skip_counts:
        counts = collect_table_counts(database_url, COUNTED_TABLES)

    run_command(build_pg_dump_command(database_url, target, pg_dump_binary))

    digest = sha256_of_file(target)
    write_sidecars(
        target,
        sha256=digest,
        created_at=moment,
        database_name=_database_name(database_url),
        database_host=_database_host(database_url),
        counts=counts,
    )
    prune_backups(root, keep=keep)
    logger.info("Backup written to %s (%d bytes)", target, target.stat().st_size)
    return BackupRecord(
        path=target,
        created_at=moment,
        size_bytes=target.stat().st_size,
        sha256=digest,
        database_name=_database_name(database_url),
        database_host=_database_host(database_url),
        counts=counts,
    )


def verify_checksum(dump_path: Path) -> bool:
    """Check a dump against the checksum recorded next to it."""
    manifest = read_manifest(dump_path)
    expected = manifest.get("sha256")
    if not expected:
        return False
    return sha256_of_file(dump_path) == expected


def run_restore(
    dump_path: Path,
    database_url: str,
    *,
    pg_restore_binary: str = "pg_restore",
    clean: bool = True,
) -> float:
    """Restore a dump and return how long the restore took in seconds."""
    started = time.perf_counter()
    run_command(
        build_pg_restore_command(
            dump_path, database_url, pg_restore_binary, clean=clean
        )
    )
    return round(time.perf_counter() - started, 3)


def run_restore_drill(
    dump_path: Path,
    target_url: str,
    *,
    pg_restore_binary: str = "pg_restore",
) -> dict[str, Any]:
    """Restore a dump into a scratch database and prove the data came back.

    The drill compares the row counts taken when the backup was made with the
    counts found after the restore, and measures the recovery time.
    """
    manifest = read_manifest(dump_path)
    expected_counts = manifest.get("counts") or {}
    duration = run_restore(dump_path, target_url, pg_restore_binary=pg_restore_binary)
    count_report = verify_table_counts(target_url, expected_counts)
    mismatches = [
        table for table, entry in count_report.items() if not entry["matches"]
    ]
    return {
        "dump": dump_path.name,
        "target": _safe_target(target_url),
        "duration_seconds": duration,
        "counts": count_report,
        "mismatches": mismatches,
        "passed": not mismatches,
        "drilled_at": datetime.now(UTC).isoformat(),
    }


def _database_name(database_url: str) -> str | None:
    from urllib.parse import urlparse

    path = urlparse(to_postgres_url(database_url)).path
    return path.lstrip("/") or None


def _database_host(database_url: str) -> str | None:
    from urllib.parse import urlparse

    return urlparse(to_postgres_url(database_url)).hostname


def _safe_target(database_url: str) -> str:
    """Describe a database target without leaking its password."""
    from urllib.parse import urlparse

    parsed = urlparse(to_postgres_url(database_url))
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    name = (parsed.path or "/").lstrip("/") or "postgres"
    return f"{host}:{port}/{name}"


def _default_backup_directory() -> str:
    return os.environ.get("BACKUP_DIR", str(backend_dir.parent / "backups"))


def main() -> int:
    """CLI entrypoint for the backup and recovery tooling."""
    parser = argparse.ArgumentParser(
        description="AgroChain database backup and recovery tooling (N3-76)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Take one database dump")
    backup_parser.add_argument("--directory", default=_default_backup_directory())
    backup_parser.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    backup_parser.add_argument("--pg-dump-binary", default="pg_dump")

    list_parser = subparsers.add_parser("list", help="List the available dumps")
    list_parser.add_argument("--directory", default=_default_backup_directory())

    prune_parser = subparsers.add_parser(
        "prune", help="Delete old dumps to honour the retention policy"
    )
    prune_parser.add_argument("--directory", default=_default_backup_directory())
    prune_parser.add_argument("--keep", type=int, default=DEFAULT_KEEP)

    verify_parser = subparsers.add_parser(
        "verify", help="Check a dump against its recorded checksum"
    )
    verify_parser.add_argument("--dump", required=True)

    restore_parser = subparsers.add_parser(
        "restore", help="Restore a dump into a database"
    )
    restore_parser.add_argument("--dump", required=True)
    restore_parser.add_argument("--target", required=True)
    restore_parser.add_argument("--pg-restore-binary", default="pg_restore")

    drill_parser = subparsers.add_parser(
        "drill", help="Restore into a scratch database and verify the result"
    )
    drill_parser.add_argument("--dump", required=True)
    drill_parser.add_argument("--target", required=True)
    drill_parser.add_argument("--pg-restore-binary", default="pg_restore")

    args = parser.parse_args()

    from app.core.config import settings

    database_url = settings.MIGRATION_DATABASE_URL.render_as_string(hide_password=False)

    if args.command == "backup":
        record = run_backup(
            args.directory,
            database_url,
            keep=args.keep,
            pg_dump_binary=args.pg_dump_binary,
        )
        print(json.dumps(record.to_dict(), indent=2))
        return 0

    if args.command == "list":
        records = list_backups(args.directory)
        for record in records:
            print(
                f"{record.created_at.isoformat()}  {record.size_bytes:>12}  "
                f"{record.name}  sha256={record.sha256[:12]}"
            )
        print(f"{len(records)} backup(s) in {args.directory}")
        return 0

    if args.command == "prune":
        removed = prune_backups(args.directory, keep=args.keep)
        for path in removed:
            print(f"removed {path}")
        print(f"{len(removed)} file(s) removed")
        return 0

    if args.command == "verify":
        dump_path = Path(args.dump)
        if not dump_path.is_file():
            print(f"dump not found: {dump_path}", file=sys.stderr)
            return 1
        if verify_checksum(dump_path):
            print(f"checksum OK: {dump_path.name}")
            return 0
        print(f"checksum MISMATCH: {dump_path.name}", file=sys.stderr)
        return 1

    if args.command == "restore":
        duration = run_restore(
            Path(args.dump), args.target, pg_restore_binary=args.pg_restore_binary
        )
        print(f"restored in {duration}s")
        return 0

    if args.command == "drill":
        report = run_restore_drill(
            Path(args.dump), args.target, pg_restore_binary=args.pg_restore_binary
        )
        print(json.dumps(report, indent=2))
        return 0 if report["passed"] else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
