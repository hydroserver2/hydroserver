from __future__ import annotations

import os
from urllib.parse import urlparse

import psycopg
from psycopg import sql


DEFAULT_E2E_DATABASE_URL = "postgresql://hsdbadmin:admin@127.0.0.1:5432/hydroserver_e2e"
DEFAULT_ADMIN_DATABASE_URL = "postgresql://hsdbadmin:admin@127.0.0.1:5432/postgres"


def main() -> None:
    e2e_database_url = os.environ.get("E2E_DATABASE_URL", DEFAULT_E2E_DATABASE_URL)
    admin_database_url = os.environ.get(
        "E2E_ADMIN_DATABASE_URL", DEFAULT_ADMIN_DATABASE_URL
    )

    parsed = urlparse(e2e_database_url)
    database_name = parsed.path.lstrip("/")
    if not database_name:
        raise SystemExit("E2E_DATABASE_URL must include a database name.")

    with psycopg.connect(admin_database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,),
            )
            exists = cur.fetchone() is not None
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
