from unittest.mock import MagicMock, patch

from app.bootstrap_db_role import (
    _grant_existing_table_permissions,
    bootstrap_database_role,
)
from app.core.config import Settings


def test_bootstrap_skipped_when_same_username():
    mock_settings = Settings(
        _env_file=None,
        DATABASE_URL_ENV="postgresql://app_user:pwd@localhost:5432/ttcs",
        MIGRATION_DATABASE_URL_ENV="postgresql://app_user:pwd@localhost:5432/ttcs",
        DB_USER="app_user",
        DB_ADMIN_USER="other_user",
        DB_PASSWORD="",
        DB_ADMIN_PASSWORD="",
    )
    with (
        patch("app.bootstrap_db_role.settings", mock_settings),
        patch("app.bootstrap_db_role.create_engine") as mock_engine,
    ):
        bootstrap_database_role()
        mock_engine.assert_not_called()


def test_bootstrap_non_superuser_mode():
    mock_settings = Settings(
        _env_file=None,
        DATABASE_URL_ENV="postgresql://admin:adminpwd@localhost:5432/ttcs",
        MIGRATION_DATABASE_URL_ENV="postgresql://admin:adminpwd@localhost:5432/ttcs",
        DB_USER="ttcs_app",
        DB_ADMIN_USER="admin",
        DB_PASSWORD="apppwd",
        DB_ADMIN_PASSWORD="adminpwd",
    )

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (False, True),  # rolsuper=False, rolcreaterole=True
        None,  # role does not exist
        ("ttcs",),  # current_database
    ]
    mock_cursor.fetchall.side_effect = [
        [],  # tables
        [],  # routines
    ]

    mock_connection = MagicMock()
    mock_connection.connection.driver_connection.cursor.return_value.__enter__.return_value = mock_cursor

    mock_engine = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_connection

    with (
        patch("app.bootstrap_db_role.settings", mock_settings),
        patch("app.bootstrap_db_role.create_engine", return_value=mock_engine),
    ):
        bootstrap_database_role()

    executed_queries = [str(call[0][0]) for call in mock_cursor.execute.call_args_list]
    create_role_calls = [q for q in executed_queries if "CREATE ROLE" in q]
    assert len(create_role_calls) == 1
    assert "NOBYPASSRLS" not in create_role_calls[0]
    assert "NOSUPERUSER" not in create_role_calls[0]


def test_bootstrap_superuser_mode():
    mock_settings = Settings(
        _env_file=None,
        DATABASE_URL_ENV="postgresql://admin:adminpwd@localhost:5432/ttcs",
        MIGRATION_DATABASE_URL_ENV="postgresql://admin:adminpwd@localhost:5432/ttcs",
        DB_USER="ttcs_app",
        DB_ADMIN_USER="admin",
        DB_PASSWORD="apppwd",
        DB_ADMIN_PASSWORD="adminpwd",
    )

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (True, True),  # rolsuper=True
        (1,),  # role exists
        ("ttcs",),  # current_database
    ]
    mock_cursor.fetchall.side_effect = [
        [],  # tables
        [],  # routines
    ]

    mock_connection = MagicMock()
    mock_connection.connection.driver_connection.cursor.return_value.__enter__.return_value = mock_cursor

    mock_engine = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_connection

    with (
        patch("app.bootstrap_db_role.settings", mock_settings),
        patch("app.bootstrap_db_role.create_engine", return_value=mock_engine),
    ):
        bootstrap_database_role()

    executed_queries = [str(call[0][0]) for call in mock_cursor.execute.call_args_list]
    alter_role_calls = [q for q in executed_queries if "ALTER ROLE" in q]
    assert len(alter_role_calls) == 1
    assert "NOBYPASSRLS" in alter_role_calls[0]
    assert "NOSUPERUSER" in alter_role_calls[0]


def test_grant_existing_table_permissions():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [
            ("organizations",),
            ("roles",),
            ("users",),
            ("sessions",),
            ("farms",),
            ("lots",),
        ],
        [
            ("app_current_user_id",),
            ("app_current_organization_id",),
            ("app_current_role",),
        ],
    ]

    _grant_existing_table_permissions(mock_cursor, "ttcs_app")
    assert mock_cursor.execute.call_count >= 8
