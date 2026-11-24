"""Query the marts for the dashboard's data loaders.

Observable Framework runs each `dashboard/src/data/*.csv.py` at build time and
serves whatever it prints. The loaders call `emit_csv(sql)`. Set
DASHBOARD_TARGET=motherduck to read MotherDuck (as the Pages build does).
"""

import csv
import json
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DB = ROOT / "data" / "warehouse.duckdb"
RUN_RESULTS = ROOT / "dbt" / "target" / "build_run_results.json"  # see transform.py


def connect() -> duckdb.DuckDBPyConnection:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if os.environ.get("DASHBOARD_TARGET", "local") == "motherduck":
        from open_data_elt.warehouse import MOTHERDUCK_DATABASE, motherduck_token

        return duckdb.connect(f"md:{MOTHERDUCK_DATABASE}?motherduck_token={motherduck_token()}")
    return duckdb.connect(str(LOCAL_DB), read_only=True)


def emit_csv(sql: str, out=None) -> None:
    out = out or sys.stdout
    with connect() as con:
        cur = con.execute(sql)
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow([d[0] for d in cur.description])
        writer.writerows(cur.fetchall())


def dbt_test_summary(path: Path = RUN_RESULTS) -> dict:
    """Counts by status from the last `dbt build` (tests and unit tests only)."""
    if not path.exists():
        return {"available": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    tests = [r for r in data["results"] if r["unique_id"].split(".")[0] in ("test", "unit_test")]
    counts: dict[str, int] = {}
    for r in tests:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {
        "available": True,
        "generated_at": data["metadata"]["generated_at"],
        "total": len(tests),
        "by_status": counts,
        "failed": [r["unique_id"] for r in tests if r["status"] not in ("pass", "success")],
    }


def emit_meta(out=None) -> None:
    """Newest date per source + dbt test summary, as JSON."""
    out = out or sys.stdout
    with connect() as con:
        latest = dict(
            con.execute(
                """
                select 'ridership', max(date_day)::varchar from marts.fct_ridership_daily
                union all
                select 'fuel', max(effective_date)::varchar from marts.fct_fuel_price_daily
                union all select 'cpi', max(month_start)::varchar from marts.fct_cpi_monthly
                union all select 'fx', max(fixing_date)::varchar from marts.fct_fx_daily
                """
            ).fetchall()
        )
        price = con.execute(
            """
            select date_day::varchar, effective_date::varchar, ron97_price,
                   ron95_citizen_price, diesel_price
            from marts.fct_fuel_price_daily order by date_day desc limit 1
            """
        ).fetchone()
    fuel_now = dict(
        zip(["as_of", "effective_date", "ron97", "ron95_citizen", "diesel"], price, strict=True)
    )
    json.dump(
        {"latest": latest, "fuel_now": fuel_now, "dbt_tests": dbt_test_summary()}, out, indent=2
    )
