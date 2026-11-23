"""Check that each source is reachable and still looks the way SOURCES.md says.

Downloads the parquet bulk files (no API calls, so no rate limit) and reports
rows, date range, columns and whether the declared primary key is unique.
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import requests

from open_data_elt.sources import BNM_ACCEPT, BNM_API, CATALOGUE_SOURCES, CatalogueSource

RAW_DIR = Path("data/raw")


@dataclass
class ProbeResult:
    source: str
    rows: int
    min_date: str | None
    max_date: str | None
    columns: list[str]
    pk_unique: bool


def download(url: str, dest: Path, timeout: int = 60) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def profile_parquet(path: Path, src: CatalogueSource) -> ProbeResult:
    con = duckdb.connect()
    rel = con.read_parquet(str(path))
    columns = rel.columns
    rows = con.sql("select count(*) from rel").fetchone()[0]
    min_d = max_d = None
    if src.date_column:
        min_d, max_d = con.sql(
            f'select min("{src.date_column}")::varchar, max("{src.date_column}")::varchar from rel'
        ).fetchone()
    keys = ", ".join(f'"{k}"' for k in src.primary_key)
    distinct = con.sql(f"select count(*) from (select distinct {keys} from rel)").fetchone()[0]
    return ProbeResult(src.id, rows, min_d, max_d, columns, distinct == rows)


def probe_bnm(timeout: int = 30) -> int:
    resp = requests.get(
        f"{BNM_API}/USD/year/2026/month/1",
        params={"session": "1200"},
        headers={"Accept": BNM_ACCEPT},
        timeout=timeout,
    )
    resp.raise_for_status()
    return len(resp.json()["data"]["rate"])


def run() -> list[ProbeResult]:
    results = []
    for src in CATALOGUE_SOURCES.values():
        path = download(src.parquet_url, RAW_DIR / f"{src.id}.parquet")
        results.append(profile_parquet(path, src))
    return results


def main() -> int:
    ok = True
    for r in run():
        ok &= r.pk_unique
        print(
            f"{r.source:<20} rows={r.rows:>7}  {r.min_date} -> {r.max_date}  "
            f"pk_unique={r.pk_unique}  cols={len(r.columns)}"
        )
        print(f"{'':<20} {', '.join(r.columns)}")
    print(f"{'bnm USD 2026-01':<20} days={probe_bnm()}")
    return 0 if ok else 1
