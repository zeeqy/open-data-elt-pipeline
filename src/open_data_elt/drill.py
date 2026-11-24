"""Incident drill: the source renames `ron97` to `ron97_price`. What happens?

Runs the real `elt load` / `elt transform` commands, as separate processes,
against a copy of the local warehouse in data/drill/ (the real one is never
touched) and prints a transcript. docs/INCIDENT.md is written from it.

  1. Guard on  (normal): the load stops before writing anything, alert fires.
  2. Guard off (what if we had no load-time check?): the load succeeds, the
     revision window overwrites real prices with NULL, and dbt's not_null test
     catches it at the transform step.
  3. Recovery: the source is fixed, the next normal load repairs the rows.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb

DRILL_DIR = Path("data/drill")
RENAME = "fuelprice:ron97=ron97_price"


def run(title: str, args: list[str], extra_env: dict[str, str]) -> tuple[int, str]:
    env = {**os.environ, "ELT_DATA_DIR": str(DRILL_DIR), **extra_env}
    for key in ("ELT_DRILL_RENAME", "ELT_DRILL_SKIP_GUARD"):
        if key not in extra_env:
            env.pop(key, None)
    cmd = [sys.executable, "-m", "open_data_elt.cli", *args]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8")
    out = proc.stdout + proc.stderr
    flags = " ".join(f"{k}={v}" for k, v in extra_env.items())
    print(f"\n$ {flags + ' ' if flags else ''}elt {' '.join(args)}   -> exit {proc.returncode}")
    keep = ("[load]", "[drill]", "LOAD FAILED", "raw.", "FAIL ", "ERROR=", "Done. PASS")
    for line in out.splitlines():
        if any(k in line for k in keep):
            print("   " + line.strip()[:220])
    (DRILL_DIR / f"{title}.log").write_text(out, encoding="utf-8")
    return proc.returncode, out


def snapshot(label: str) -> None:
    with duckdb.connect(str(DRILL_DIR / "warehouse.duckdb"), read_only=True) as con:
        cols = [
            r[0]
            for r in con.execute(
                "select column_name from information_schema.columns "
                "where table_schema = 'raw' and table_name = 'fuelprice'"
            ).fetchall()
        ]
        has_new = "ron97_price" in cols
        rows, null_ron97 = con.execute(
            "select count(*), count(*) filter (where ron97 is null and series_type = 'level' "
            "and date > date '2018-01-01') from raw.fuelprice"
        ).fetchone()
        last = con.execute(
            "select date::varchar, ron97"
            + (", ron97_price" if has_new else "")
            + " from raw.fuelprice where series_type = 'level' order by date desc limit 3"
        ).fetchall()
    print(
        f"   [{label}] raw.fuelprice rows={rows}, level rows with NULL ron97 since 2018="
        f"{null_ron97}, column ron97_price exists={has_new}"
    )
    print(f"   [{label}] latest (date, ron97{', ron97_price' if has_new else ''}): {last}")


def main() -> int:
    src = Path("data/warehouse.duckdb")
    if not src.exists():
        print("Run `uv run elt load --backfill` first; the drill copies data/warehouse.duckdb.")
        return 1
    shutil.rmtree(DRILL_DIR, ignore_errors=True)
    DRILL_DIR.mkdir(parents=True)
    shutil.copyfile(src, DRILL_DIR / "warehouse.duckdb")
    print(f"Copied {src} -> {DRILL_DIR / 'warehouse.duckdb'} (dlt state restores from it).")
    snapshot("before")

    print("\n== 1. Source renames ron97 -> ron97_price, guard ON (normal pipeline)")
    code1, out1 = run("1_guard_on", ["load", "--only", "fuelprice"], {"ELT_DRILL_RENAME": RENAME})
    snapshot("after 1")
    from open_data_elt import alert

    log1 = DRILL_DIR / "1_guard_on.log"
    print(
        "   Telegram alert text:\n      "
        + alert.build_message("load", log1).replace("\n", "\n      ")
    )

    print("\n== 2. Same rename, guard OFF (what a pipeline without the check would do)")
    env2 = {"ELT_DRILL_RENAME": RENAME, "ELT_DRILL_SKIP_GUARD": "1"}
    code2, _ = run("2_guard_off_load", ["load", "--only", "fuelprice"], env2)
    snapshot("after 2 load")
    code2t, _ = run("2_guard_off_transform", ["transform", "--skip-freshness"], {})

    print("\n== 3. Source fixed; next normal run")
    code3, _ = run("3_recover_load", ["load", "--only", "fuelprice"], {})
    snapshot("after 3 load")
    code3t, _ = run("3_recover_transform", ["transform", "--skip-freshness"], {})

    expected = (
        code1 != 0 and "SchemaDriftError" in out1,
        code2 == 0,
        code2t != 0,
        code3 == 0,
        code3t == 0,
    )
    print(f"\nDrill outcome as expected: {all(expected)} {expected}")
    print(f"Full logs in {DRILL_DIR}/")
    return 0 if all(expected) else 1


if __name__ == "__main__":
    sys.exit(main())
