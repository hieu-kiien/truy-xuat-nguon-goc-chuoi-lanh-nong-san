"""Restore the Mộc Châu demo account to organization-scoped permissions.

Revision ID: 20261007_13
Revises: 20261007_12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261007_13"
down_revision: str | None = "20261007_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET role_code = 'organization_admin',
            full_name = 'Trần Thị Hương (Quản trị HTX Mộc Châu)'
        WHERE email = 'admin@mocchau.vn';
        """
    )
    op.execute(
        """
        UPDATE users
        SET full_name = 'Vũ Hải Đăng (Quản trị hệ thống)'
        WHERE email = 'admin@system.vn';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET role_code = 'system_admin',
            full_name = 'Trần Thị Hương (Quản trị viên Hệ thống)'
        WHERE email = 'admin@mocchau.vn';
        """
    )
    op.execute(
        """
        UPDATE users
        SET full_name = 'Vũ Hải Đăng (Quản trị viên Hệ thống Toàn quyền)'
        WHERE email = 'admin@system.vn';
        """
    )
