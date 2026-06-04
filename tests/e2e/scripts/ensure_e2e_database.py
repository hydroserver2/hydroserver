from __future__ import annotations

import os
from urllib.parse import urlparse

import psycopg
from psycopg import sql


DEFAULT_E2E_DATABASE_URL = "postgresql://hsdbadmin:admin@127.0.0.1:5432/hydroserver_e2e"
DEFAULT_ADMIN_DATABASE_URL = "postgresql://hsdbadmin:admin@127.0.0.1:5432/postgres"


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off"}


def main() -> None:
    e2e_database_url = os.environ.get("E2E_DATABASE_URL", DEFAULT_E2E_DATABASE_URL)
    admin_database_url = os.environ.get(
        "E2E_ADMIN_DATABASE_URL", DEFAULT_ADMIN_DATABASE_URL
    )
    reset_database = _env_flag("E2E_RESET_DATABASE", True)

    parsed = urlparse(e2e_database_url)
    database_name = parsed.path.lstrip("/")
    if not database_name:
        raise SystemExit("E2E_DATABASE_URL must include a database name.")

    admin_database_name = urlparse(admin_database_url).path.lstrip("/")
    if database_name == admin_database_name:
        raise SystemExit("E2E_DATABASE_URL must not target the admin database.")

    with psycopg.connect(admin_database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,),
            )
            exists = cur.fetchone() is not None
            if exists and reset_database:
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                    """,
                    (database_name,),
                )
                cur.execute(
                    sql.SQL("DROP DATABASE {}").format(
                        sql.Identifier(database_name)
                    )
                )
                exists = False
                print(f"Dropped database {database_name}.")

            if not exists:
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(database_name)
                    )
                )
                print(f"Created database {database_name}.")
            else:
                print(f"Database {database_name} already exists.")


if __name__ == "__main__":
    main()
