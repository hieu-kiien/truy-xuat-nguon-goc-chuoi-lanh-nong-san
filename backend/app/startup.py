"""Bootstrap PostgreSQL with the migration role, then run as the app role."""

import os
import subprocess
import sys
from collections.abc import Mapping

from app.core.config import settings
from app.seed_demo import seed_demo_data


def _runtime_environment(
    app_database_url: str, source: Mapping[str, str]
) -> dict[str, str]:
    runtime_environment = dict(source)
    runtime_environment["DATABASE_URL_ENV"] = app_database_url
    runtime_environment.pop("MIGRATION_DATABASE_URL_ENV", None)
    runtime_environment.pop("DB_ADMIN_PASSWORD", None)
    return runtime_environment


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "app.bootstrap_db_role"],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
    )
    seed_demo_data()

    runtime_environment = _runtime_environment(
        settings.DATABASE_URL.render_as_string(hide_password=False),
        os.environ,
    )

    port = runtime_environment.get("PORT", "8000")
    os.execvpe(
        "uvicorn",
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
        runtime_environment,
    )


if __name__ == "__main__":
    main()
