# 08 Open Data ELT Pipeline

A small but real data engineering pipeline: ingest Malaysian open data on a schedule, model it with dbt, test it, serve a dashboard.
Tracks shown: data engineering, cloud, data analysis.

## Data
data.gov.my API (check current docs). Pick 3 to 4 related datasets that update often, e.g. daily public transport ridership, weekly fuel prices, monthly CPI, plus BNM exchange rates. Record sources in `SOURCES.md`.

## Pipeline
1. Extract/load: Python (dlt or plain requests) into raw tables. Incremental, idempotent, handles schema drift.
2. Warehouse: DuckDB locally, plus one free cloud warehouse (MotherDuck or BigQuery sandbox; pick and justify).
3. Transform: dbt project with staging, intermediate and marts (star schema). dbt tests (unique, not_null, relationships, freshness) and the docs site.
4. Orchestrate: Dagster or GitHub Actions cron, whichever is simplest while still showing lineage. Failure alert to Telegram.
5. Serve: dashboard (Evidence or Streamlit) answering 3 questions, e.g. do fuel price changes move ridership? Publish dbt docs on GitHub Pages.

## Proof
- Lineage graph screenshot, data quality test results, a backfill command.
- A documented incident: simulate the source renaming a column and show how the pipeline caught it.
- `docs/ARCHITECTURE.md` with Mermaid diagram and running cost (should be RM 0).
