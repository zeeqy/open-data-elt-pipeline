"""dlt source and pipeline: sources -> raw tables in DuckDB (or MotherDuck).

- First run, or `--backfill`: read the parquet bulk files (no rate limit).
- Later runs: ask the API only for rows since (last loaded date - lookback).
- Every table merges on its primary key, so re-running never duplicates rows.
- Schema drift: new columns are added (`columns: evolve`); a missing required
  column stops the run (SchemaDriftError); a changed data type stops it too
  (`data_type: freeze`).
"""

import datetime as dt
import sys
from collections.abc import Iterable
from pathlib import Path

import dlt

from open_data_elt import extract, warehouse
from open_data_elt.sources import (
    BNM_CURRENCIES,
    BNM_START,
    CATALOGUE_SOURCES,
    CatalogueSource,
)

DATASET = "raw"
PIPELINES_DIR = Path("data/.dlt")
SCHEMA_CONTRACT = {"tables": "evolve", "columns": "evolve", "data_type": "freeze"}


def log(msg: str) -> None:
    print(f"[load] {msg}", file=sys.stderr, flush=True)


def _catalogue_resource(src: CatalogueSource, backfill: bool):
    if src.date_column is None:  # lookup table: small, always reload in full

        @dlt.resource(name=src.id, primary_key=list(src.primary_key), write_disposition="replace")
        def lookup():
            yield extract.fetch_parquet(src)

        return lookup

    @dlt.resource(name=src.id, primary_key=list(src.primary_key), write_disposition="merge")
    def dated():
        state = dlt.current.resource_state()
        last = state.get("last_date")
        if backfill or last is None:
            log(f"{src.id}: full load from parquet ({'backfill' if backfill else 'no state'})")
            rows = extract.fetch_parquet(src)
        else:
            since = dt.date.fromisoformat(last) - dt.timedelta(days=src.lookback_days)
            log(f"{src.id}: incremental via API since {since} (last loaded {last})")
            rows, meta = extract.fetch_api(src, since)
            state["meta"] = meta  # data_as_of / next_update, kept for freshness checks
        if rows:
            newest = max(r[src.date_column] for r in rows)
            state["last_date"] = max(newest.isoformat(), last or "")
        state["last_rows"] = len(rows)
        yield rows

    return dated


def _bnm_resource(backfill: bool, today: dt.date):
    @dlt.resource(
        name="bnm_exchange_rate", primary_key=["currency", "date"], write_disposition="merge"
    )
    def bnm():
        state = dlt.current.resource_state()
        last = state.get("last_date")
        if backfill or last is None:
            start = BNM_START
            log(f"bnm_exchange_rate: full load from {start[0]}-{start[1]:02d}")
        else:  # re-pull the month of the last fixing, plus anything after it
            last_d = dt.date.fromisoformat(last)
            start = (last_d.year, last_d.month)
            log(f"bnm_exchange_rate: incremental from {start[0]}-{start[1]:02d} (last {last})")
        newest = last
        for currency in BNM_CURRENCIES:
            for year, month in extract.months(start, today):
                rows = extract.fetch_bnm_month(currency, year, month)
                if rows:
                    newest = max(newest or "", max(r["date"] for r in rows).isoformat())
                    yield rows
        state["last_date"] = newest

    return bnm


@dlt.source(name="my_open_data", schema_contract=SCHEMA_CONTRACT)
def my_open_data(backfill: bool = False, only: Iterable[str] | None = None, today=None):
    today = today or dt.date.today()
    wanted = set(only) if only else None
    resources = [
        _catalogue_resource(src, backfill)
        for key, src in CATALOGUE_SOURCES.items()
        if wanted is None or key in wanted
    ]
    if wanted is None or "bnm_exchange_rate" in wanted:
        resources.append(_bnm_resource(backfill, today))
    return resources


def make_pipeline(destination=None, pipelines_dir: Path = PIPELINES_DIR, target: str = "local"):
    # One pipeline name per target, so local and MotherDuck keep separate state.
    destination = destination or warehouse.destination(target)
    return dlt.pipeline(
        pipeline_name="open_data_elt" if target == "local" else f"open_data_elt_{target}",
        destination=destination,
        dataset_name=DATASET,
        pipelines_dir=str(pipelines_dir),
    )


def run(
    backfill: bool = False,
    only: Iterable[str] | None = None,
    destination=None,
    pipelines_dir: Path = PIPELINES_DIR,
    today: dt.date | None = None,
    target: str = "local",
):
    pipeline = make_pipeline(destination, pipelines_dir, target)
    info = pipeline.run(my_open_data(backfill=backfill, only=only, today=today))
    return pipeline, info
