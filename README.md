# Open Data ELT Pipeline

Work in progress. Ingests Malaysian open data (data.gov.my, DOSM, BNM) with dlt, models it with dbt, serves a dashboard. Sources: [SOURCES.md](SOURCES.md).

## Run (so far)

```bash
uv sync
uv run elt probe              # check sources still match SOURCES.md
uv run elt load --backfill    # full history from parquet bulk files + BNM since 2017 (~2.5 min)
uv run elt load               # incremental: API rows since last load minus lookback (~40 s)
uv run pytest                 # offline tests (add -m live for real-API tests)
```

Raw tables land in `data/warehouse.duckdb`, schema `raw`.
