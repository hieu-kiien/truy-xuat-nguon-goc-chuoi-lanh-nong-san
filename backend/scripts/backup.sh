#!/usr/bin/env bash
# Nightly database backup for the AgroChain staging database (N3-76).
#
# Run it from cron, for example every night at 02:15:
#   15 2 * * * cd /opt/agrochain/backend && ./scripts/backup.sh >> /var/log/agrochain-backup.log 2>&1
#
# The backup directory must live outside the application container so the
# dumps survive a redeploy.

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${BACKUP_DIR}/../backups}"
KEEP="${BACKUP_KEEP:-14}"
PYTHON_BIN="${PYTHON_BIN:-python}"

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump was not found. Install the PostgreSQL client tools." >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

cd "${BACKEND_DIR}"
"${PYTHON_BIN}" scripts/backup.py backup \
  --directory "${BACKUP_DIR}" \
  --keep "${KEEP}"

# Fail loudly when the newest dump does not match its recorded checksum.
NEWEST_DUMP="$(ls -1t "${BACKUP_DIR}"/agrochain-*.dump 2>/dev/null | head -n 1 || true)"
if [[ -z "${NEWEST_DUMP}" ]]; then
  echo "No backup was produced in ${BACKUP_DIR}" >&2
  exit 1
fi

"${PYTHON_BIN}" scripts/backup.py verify --dump "${NEWEST_DUMP}"
echo "Backup finished: ${NEWEST_DUMP}"
