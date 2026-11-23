# Open Data ELT Pipeline

Work in progress. Ingests Malaysian open data (data.gov.my, DOSM, BNM) with dlt, models it with dbt, serves a dashboard. Sources: [SOURCES.md](SOURCES.md).

## Run (so far)

```bash
uv sync
uv run elt probe              # check sources still match SOURCES.md
uv run elt load --backfill    # full history from parquet bulk files + BNM since 2017 (~2.5 min)
uv run elt load               # incremental: API rows since last load minus lookback (~40 s)
uv run elt transform          # dbt source freshness + dbt build (seeds, models, 69 tests)
uv run elt docs               # dbt docs site -> dbt/target/index.html
uv run pytest                 # offline tests incl. a full dbt build on synthetic data (-m live for real APIs)
```

Raw tables land in `data/warehouse.duckdb`, schema `raw`; dbt writes `staging`, `intermediate`, `marts` (star schema: `dim_date`, `dim_service`, `dim_cpi_division`, `fct_ridership_daily`, `fct_fuel_price_daily`, `fct_fx_daily`, `fct_cpi_monthly`, plus `mart_transport_weekly` / `mart_transport_monthly` for the dashboard).
