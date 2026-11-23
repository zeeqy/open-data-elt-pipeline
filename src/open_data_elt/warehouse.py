"""Where the data lives: a local DuckDB file, or the same tables on MotherDuck.

Both are DuckDB, so the dlt loader and the dbt SQL are identical; only the
connection changes. MotherDuck needs MOTHERDUCK_TOKEN (free Lite plan).
"""

import os
from pathlib import Path

import dlt

TARGETS = ("local", "motherduck")
DUCKDB_PATH = Path("data/warehouse.duckdb")
MOTHERDUCK_DATABASE = "open_data"


def motherduck_token() -> str:
    token = os.environ.get("MOTHERDUCK_TOKEN", "").strip()
    if not token:
        raise RuntimeError("MOTHERDUCK_TOKEN is not set (see .env.example)")
    return token


def ensure_motherduck_database(name: str = MOTHERDUCK_DATABASE) -> None:
    """dlt and dbt expect the database to exist; create it on first use."""
    import duckdb

    with duckdb.connect(f"md:?motherduck_token={motherduck_token()}") as con:
        con.execute(f'create database if not exists "{name}"')


def destination(target: str = "local"):
    if target == "local":
        DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return dlt.destinations.duckdb(str(DUCKDB_PATH))
    if target == "motherduck":
        ensure_motherduck_database()
        return dlt.destinations.motherduck(
            credentials={"database": MOTHERDUCK_DATABASE, "password": motherduck_token()}
        )
    raise ValueError(f"unknown target {target!r}, expected one of {TARGETS}")
