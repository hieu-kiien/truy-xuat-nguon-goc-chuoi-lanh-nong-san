"""Reserve the revision ID used by the pre-Sprint 2 staging migration.

Revision ID: 20261007_08
Revises: 20261007_07

The old deployment used this revision ID to upgrade the Mộc Châu admin role.
That behavior is represented by revisions 12 and 13 in the current chain.
"""

from collections.abc import Sequence

revision: str = "20261007_08"
down_revision: str | None = "20261007_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
