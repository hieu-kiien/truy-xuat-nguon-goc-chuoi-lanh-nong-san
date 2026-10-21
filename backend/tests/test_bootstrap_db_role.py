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
            ("products",),
            ("events",),
            ("handovers",),
            ("shipments",),
            ("product_cold_chain_configs",),
        ],
        [("contact_email",)],
        [
            ("current_holder_organization_id",),
            ("status",),
        ],
        [("overdue_at",)],
        [
            ("cold_chain_min_temp_celsius",),
            ("cold_chain_max_temp_celsius",),
            ("cold_chain_delay_minutes",),
            ("cold_chain_config_resolved_at",),
        ],
        [
            ("app_current_user_id",),
            ("app_current_organization_id",),
            ("app_current_role",),
        ],
    ]

    _grant_existing_table_permissions(mock_cursor, "ttcs_app")
    assert mock_cursor.execute.call_count >= 20
    executed_queries = [str(call[0][0]) for call in mock_cursor.execute.call_args_list]
    assert any(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON product_cold_chain_configs" in query
        for query in executed_queries
    ), "N3-62 config table must be readable and writable by the app role"
    assert any(
        "GRANT UPDATE (cold_chain_min_temp_celsius" in query
        for query in executed_queries
    ), "N3-62 shipment snapshot columns must be updatable by the app role"
    assert any(
        "GRANT UPDATE (contact_email) ON organizations" in query
        for query in executed_queries
    ), "N3-57 contact address must be updatable by the app role"


def test_grant_existing_table_permissions_shipments_without_last_reading_at():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [("shipments",)],  # tables
        [("status",), ("completed_at",), ("notes",)],  # columns without last_reading_at
        [],  # routines
    ]

    _grant_existing_table_permissions(mock_cursor, "ttcs_app")
    queries = [str(call[0][0]) for call in mock_cursor.execute.call_args_list]
    assert any(
        "GRANT UPDATE (status, completed_at, notes) ON shipments" in q for q in queries
    )
    assert not any("last_reading_at" in q for q in queries)


def test_grant_existing_table_permissions_shipments_with_last_reading_at():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [
        [("shipments",)],  # tables
        [
            ("status",),
            ("completed_at",),
            ("notes",),
            ("last_reading_at",),
        ],  # columns with last_reading_at
        [],  # routines
    ]

    _grant_existing_table_permissions(mock_cursor, "ttcs_app")
    queries = [str(call[0][0]) for call in mock_cursor.execute.call_args_list]
    assert any(
        "GRANT UPDATE (status, completed_at, notes) ON shipments" in q for q in queries
    )
    assert any("GRANT UPDATE (last_reading_at) ON shipments" in q for q in queries)


def test_bootstrap_idempotent_two_consecutive_runs():
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
    # Return valid query results for 2 consecutive runs
    mock_cursor.fetchone.side_effect = [
        (False, True),  # run 1: rolsuper=False, rolcreaterole=True
        (1,),  # run 1: role exists
        ("ttcs",),  # run 1: current_database
        (False, True),  # run 2: rolsuper=False, rolcreaterole=True
        (1,),  # run 2: role exists
        ("ttcs",),  # run 2: current_database
    ]
    mock_cursor.fetchall.side_effect = [
        [("shipments",)],  # run 1: tables
        [("status",), ("completed_at",), ("notes",)],  # run 1: shipments columns
        [],  # run 1: routines
        [("shipments",), ("cold_chain_violations",)],  # run 2: tables
        [
            ("status",),
            ("completed_at",),
            ("notes",),
            ("last_reading_at",),
        ],  # run 2: shipments columns
        [],  # run 2: routines
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
        bootstrap_database_role()

    executed_queries = [str(call[0][0]) for call in mock_cursor.execute.call_args_list]
    alter_calls = [q for q in executed_queries if "ALTER ROLE" in q]
    assert len(alter_calls) == 2


def test_safe_exception_details_masks_secrets():
    from app.startup import _safe_exception_details

    class DummyDiag:
        message_primary = "column 'last_reading_at' does not exist in postgresql://admin:super_secret@localhost:5432/db"

    class DummyOrig(Exception):
        pgcode = "42703"
        diag = DummyDiag()

    class DummyException(Exception):
        orig = DummyOrig()

    result = _safe_exception_details(DummyException("raw sensitive secret"))
    assert "super_secret" not in result
    assert "42703" in result
    assert "last_reading_at" in result
    assert "postgresql://admin:***@localhost:5432/db" in result


def test_startup_main_logs_exception_and_stops_on_bootstrap_error():
    import pytest

    from app.core.config import Settings
    from app.startup import main as startup_main

    with (
        patch.object(Settings, "validate_runtime"),
        patch(
            "app.startup.bootstrap_database_role",
            side_effect=RuntimeError("simulated bootstrap failure"),
        ),
        patch("app.startup.logger.critical") as mock_critical,
    ):
        with pytest.raises(SystemExit) as exc_info:
            startup_main()
        assert exc_info.value.code == 1
        mock_critical.assert_called_once()
        assert "simulated bootstrap failure" in mock_critical.call_args[0][1]


def test_startup_main_success_flow():
    from app.core.config import Settings
    from app.startup import main as startup_main

    with (
        patch.object(Settings, "validate_runtime"),
        patch("app.startup.bootstrap_database_role") as mock_bootstrap,
        patch("app.startup.run_migrations") as mock_migrations,
        patch("app.startup.seed_demo_data") as mock_seed,
        patch("app.startup.os.execvpe") as mock_exec,
    ):
        startup_main()
        mock_bootstrap.assert_called_once()
        mock_migrations.assert_called_once()
        mock_seed.assert_called_once()
        mock_exec.assert_called_once()
