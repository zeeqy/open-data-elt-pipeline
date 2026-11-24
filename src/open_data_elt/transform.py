"""Run dbt in-process against the warehouse the loader wrote."""

import os
import shutil
from pathlib import Path

from dbt.cli.main import dbtRunner

from open_data_elt import warehouse

DBT_DIR = Path(__file__).resolve().parents[2] / "dbt"
# `dbt docs generate` overwrites run_results.json, so keep the build's copy.
BUILD_RESULTS = DBT_DIR / "target" / "build_run_results.json"


def dbt(
    args: list[str], duckdb_path: Path | str = warehouse.DUCKDB_PATH, target: str = "local"
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
    duckdb_path: Path | str = warehouse.DUCKDB_PATH,
    freshness: bool = True,
    target: str = "local",
) -> bool:
    """`dbt source freshness` (optional) then `dbt build` (seeds, models, tests)."""
    if freshness and not dbt(["source", "freshness"], duckdb_path, target):
        return False
    ok = dbt(["build"], duckdb_path, target)
    results = DBT_DIR / "target" / "run_results.json"
    if results.exists():
        shutil.copyfile(results, BUILD_RESULTS)
    return ok


DASHBOARD_DIR = DBT_DIR.parent / "dashboard"


def site(target: str = "local") -> bool:
    """Build the static site: dashboard (Observable Framework) + dbt docs at /dbt-docs/."""
    import subprocess
    import sys

    # Run dbt in a child process: in-process dbt keeps the DuckDB file locked
    # (on Windows), and the dashboard's data loaders must open it afterwards.
    dbt_cmd = [
        sys.executable,
        "-c",
        "from dbt.cli.main import cli; cli()",
        "docs",
        "generate",
        "--static",
        "--project-dir",
        str(DBT_DIR),
        "--profiles-dir",
        str(DBT_DIR),
        "--target",
        "dev" if target == "local" else target,
    ]
    env = {**os.environ, "DUCKDB_PATH": str(Path(warehouse.DUCKDB_PATH).resolve())}
    if subprocess.run(dbt_cmd, env=env).returncode != 0:
        return False
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm not found; install Node.js 20+ and run `npm ci` in dashboard/")
    env = {**os.environ, "DASHBOARD_TARGET": target}
    if subprocess.run([npm, "run", "build"], cwd=DASHBOARD_DIR, env=env).returncode != 0:
        return False
    docs_dir = DASHBOARD_DIR / "dist" / "dbt-docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DBT_DIR / "target" / "static_index.html", docs_dir / "index.html")
    print(f"site ready: {DASHBOARD_DIR / 'dist'}")
    return True
