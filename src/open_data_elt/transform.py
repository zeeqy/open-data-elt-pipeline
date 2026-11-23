"""Run dbt in-process against the warehouse the loader wrote."""

import os
from pathlib import Path

from dbt.cli.main import dbtRunner

DBT_DIR = Path(__file__).resolve().parents[2] / "dbt"


def dbt(
    args: list[str], duckdb_path: Path | str = "data/warehouse.duckdb", target: str = "local"
) -> bool:
    """Run one dbt command; returns True on success."""
    os.environ["DUCKDB_PATH"] = str(Path(duckdb_path).resolve())
    dbt_target = "dev" if target == "local" else target
    result = dbtRunner().invoke(
        [
            *args,
            "--project-dir",
            str(DBT_DIR),
            "--profiles-dir",
            str(DBT_DIR),
            "--target",
            dbt_target,
        ]
    )
    return bool(result.success)


def build(
    duckdb_path: Path | str = "data/warehouse.duckdb",
    freshness: bool = True,
    target: str = "local",
) -> bool:
    """`dbt source freshness` (optional) then `dbt build` (seeds, models, tests)."""
    if freshness and not dbt(["source", "freshness"], duckdb_path, target):
        return False
    return dbt(["build"], duckdb_path, target)
