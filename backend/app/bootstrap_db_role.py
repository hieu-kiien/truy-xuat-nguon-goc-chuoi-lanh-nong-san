"""Create a least-privilege PostgreSQL role for application requests."""

from psycopg import sql
from sqlalchemy import create_engine

from app.core.config import settings


def bootstrap_database_role() -> None:
    app_url = settings.DATABASE_URL
    admin_url = settings.MIGRATION_DATABASE_URL

    if app_url.username == admin_url.username:
        raise RuntimeError(
            "Application and migration database users must be different; "
            "configure a least-privilege DB_USER for runtime requests"
        )
    if not app_url.password or not admin_url.password:
        raise RuntimeError("Database passwords must be configured through environment")

    engine = create_engine(admin_url)
    try:
        with engine.begin() as connection:
            raw_connection = connection.connection.driver_connection
            with raw_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT rolsuper OR rolcreaterole FROM pg_catalog.pg_roles "
                    "WHERE rolname = current_user"
                )
                row = cursor.fetchone()
                if not row or not row[0]:
                    raise RuntimeError(
                        "Migration database user must have CREATEROLE permission "
                        "to provision the least-privilege application role"
                    )

                cursor.execute(
                    "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = %s",
                    (settings.DB_USER,),
                )
                if cursor.fetchone() is None:
                    cursor.execute(
                        sql.SQL(
                            "CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB "
                            "NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                        ).format(sql.Identifier(settings.DB_USER))
                    )

                cursor.execute(
                    sql.SQL(
                        "ALTER ROLE {} WITH LOGIN NOINHERIT PASSWORD {} NOSUPERUSER "
                        "NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                    ).format(
                        sql.Identifier(settings.DB_USER),
                        sql.Literal(app_url.password),
                    )
                )
    finally:
        engine.dispose()


if __name__ == "__main__":
    bootstrap_database_role()
