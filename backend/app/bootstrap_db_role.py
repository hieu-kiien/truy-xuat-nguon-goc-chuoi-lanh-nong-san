"""Create a least-privilege PostgreSQL role for application requests."""

from psycopg import sql
from sqlalchemy import create_engine

from app.core.config import settings


def bootstrap_database_role() -> None:
    if settings.DB_USER == settings.DB_ADMIN_USER:
        raise RuntimeError("Application and migration database roles must be distinct")
    if not settings.DB_PASSWORD or not settings.DB_ADMIN_PASSWORD:
        raise RuntimeError("Database passwords must be configured through environment")

    engine = create_engine(settings.MIGRATION_DATABASE_URL)
    try:
        with engine.begin() as connection:
            raw_connection = connection.connection.driver_connection
            with raw_connection.cursor() as cursor:
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
                        sql.Literal(settings.DB_PASSWORD),
                    )
                )
    finally:
        engine.dispose()


if __name__ == "__main__":
    bootstrap_database_role()
