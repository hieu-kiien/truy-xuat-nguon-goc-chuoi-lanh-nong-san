import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# Đảm bảo Python tìm thấy module app/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app.models  # noqa: E402,F401
from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Trỏ tới Base.metadata để alembic autogenerate tự phát hiện thay đổi model
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.MIGRATION_DATABASE_URL.render_as_string(hide_password=True),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        settings.MIGRATION_DATABASE_URL,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
