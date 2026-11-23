"""Read rows from the sources and make them consistent before dlt loads them.

Both paths (API JSON and parquet bulk file) must give the same types, or dlt
would create variant columns. So every date becomes a `datetime.date`, NaN
becomes None and measure columns become float.
"""

import calendar
import datetime as dt
import math
from collections.abc import Iterator
from pathlib import Path

import duckdb
import requests

from open_data_elt import http
from open_data_elt.sources import (
    BNM_ACCEPT,
    BNM_API,
    BNM_SESSION,
    DATA_GOV_API,
    CatalogueSource,
)

RAW_DIR = Path("data/raw")


class SchemaDriftError(RuntimeError):
    """A column the models depend on is missing from the source."""


def check_columns(columns: list[str] | set[str], src: CatalogueSource) -> set[str]:
    """Fail if a required column is gone; return the set of new, unexpected columns."""
    cols = set(columns)
    missing = set(src.required_columns) - cols
    if missing:
        raise SchemaDriftError(
            f"{src.id}: required column(s) {sorted(missing)} missing from source. "
            f"Columns received: {sorted(cols)}. Did the source rename a column?"
        )
    return cols - set(src.required_columns)


def to_date(value) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def normalize_row(row: dict, src: CatalogueSource, origin: str) -> dict:
    out = {}
    for key, value in row.items():
        if isinstance(value, float) and math.isnan(value):
            value = None
        if key == src.date_column:
            value = to_date(value)
        elif (
            src.date_column
            and key not in src.primary_key
            and isinstance(value, int | float)
            and not isinstance(value, bool)
        ):
            value = float(value)
        out[key] = value
    out["_origin"] = origin
    return out


def _rows_checked(rows: list[dict], src: CatalogueSource, origin: str) -> list[dict]:
    if rows:
        columns = set().union(*(r.keys() for r in rows))
        check_columns(columns, src)
    return [normalize_row(r, src, origin) for r in rows]


def fetch_api(src: CatalogueSource, since: dt.date) -> tuple[list[dict], dict]:
    """Rows on/after `since` plus the catalogue meta block (data_as_of, next_update)."""
    resp = http.get(
        DATA_GOV_API,
        params={
            "id": src.id,
            "date_start": f"{since.isoformat()}@{src.date_column}",
            "meta": "true",
        },
    )
    body = resp.json()
    return _rows_checked(body["data"], src, "api"), body["meta"]


def fetch_parquet(src: CatalogueSource, raw_dir: Path = RAW_DIR) -> list[dict]:
    path = raw_dir / f"{src.id}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(http.get(src.parquet_url).content)
    return read_parquet_rows(path, src)


def read_parquet_rows(path: Path, src: CatalogueSource) -> list[dict]:
    con = duckdb.connect()
    cur = con.execute(f"select * from read_parquet('{path.as_posix()}')")
    columns = [d[0] for d in cur.description]
    check_columns(columns, src)
    rows = (dict(zip(columns, r, strict=True)) for r in cur.fetchall())
    return [normalize_row(r, src, "parquet") for r in rows]


def months(start: tuple[int, int], end: dt.date) -> Iterator[tuple[int, int]]:
    year, month = start
    while (year, month) <= (end.year, end.month):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def fetch_bnm_month(currency: str, year: int, month: int) -> list[dict]:
    try:
        resp = http.get(
            f"{BNM_API}/{currency}/year/{year}/month/{month}",
            params={"session": BNM_SESSION},
            headers={"Accept": BNM_ACCEPT},
        )
    except requests.HTTPError as err:
        if err.response is not None and err.response.status_code == 404:
            return []  # BNM answers 404 for a month with no fixings yet
        raise
    data = resp.json()["data"]
    rates = data["rate"] if isinstance(data["rate"], list) else [data["rate"]]
    last_day = dt.date(year, month, calendar.monthrange(year, month)[1])
    return [
        {
            "currency": data["currency_code"],
            "date": to_date(r["date"]),
            "unit": float(data["unit"]),
            "buying_rate": r.get("buying_rate"),
            "selling_rate": r.get("selling_rate"),
            "middle_rate": r.get("middle_rate"),
            "session": BNM_SESSION,
            "_origin": "api",
        }
        for r in rates
        if r.get("date") and to_date(r["date"]) <= last_day
    ]
