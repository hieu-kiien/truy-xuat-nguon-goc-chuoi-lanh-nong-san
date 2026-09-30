"""Infrastructure identity used by database migrations.

Row-level security policies and table grants are granted to a dedicated
*application* role that is deliberately kept separate from the migration/admin
role. The role name is deployment configuration, so migrations read it from the
environment (with the historical default) instead of hard-coding it. Without
this, a migration could only ever be applied to the exact database and role
names baked into the source, which makes automated testing impossible.
"""

import os

APPLICATION_ROLE_ENV_VAR = "DB_USER"
DEFAULT_APPLICATION_ROLE = "ttcs_app"


def application_database_role() -> str:
    """Return the least-privilege role the application connects as."""
    return os.getenv(APPLICATION_ROLE_ENV_VAR) or DEFAULT_APPLICATION_ROLE
