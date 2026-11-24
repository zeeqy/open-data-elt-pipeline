# LEARN: 08 Open Data ELT Pipeline

## 1. What it does (3 sentences)

Every morning a GitHub Actions job pulls Malaysian open data (daily rail and bus ridership, weekly fuel prices, monthly CPI, BNM's USD/MYR rate) into a warehouse with dlt, only fetching what is new. dbt cleans it, builds a star schema and runs 50 tests plus freshness checks; if anything fails, a Telegram message says which step and why. A static dashboard on GitHub Pages then answers three questions, such as whether fuel price changes move rail ridership (they do not, visibly), and it all costs RM 0.

## 2. Major decisions

| Decision | We chose | Alternative | Why |
|---|---|---|---|
| Loader | dlt | Plain `requests` + hand-written SQL | Incremental state, merge on keys, schema evolution and contracts are built in. State is stored inside the warehouse, so a fresh CI runner knows where to continue. |
| Backfill vs daily | Parquet bulk files for history, API for daily rows | API for everything | data.gov.my allows 4 requests/minute; the bulk files have no stated limit and hold the full history in one download. |
| Idempotency | Merge on primary key + a revision window (35 days, 100 for CPI) | Append only, or full reload daily | Reruns add 0 rows; late corrections from the source are picked up. Full reloads would waste API calls. |
| Schema drift | Allow new columns, fail on missing required columns or type changes | Let dlt evolve everything | Evolution alone hides a renamed column (it looks like "column added"). The drill showed it would null 6 real prices. |
| Cloud warehouse | MotherDuck (Lite, free) | BigQuery sandbox | Same engine as local DuckDB, so the same dbt SQL runs in both places. Sandbox tables expire after 60 days. |
| Orchestration | GitHub Actions cron | Dagster | One daily job does not need a scheduler service. Lineage comes from dbt docs. |
| Dashboard | Observable Framework | Evidence (in the original plan), Streamlit | Evidence's static build is deprecated and its new CLI needs a Docker server. Framework builds a static site for GitHub Pages; Streamlit needs a server. |
| Fuel series | `ron95_citizen_price` (BUDI95 price after 30 Sep 2025, single price before) and RON97 as the floating price | Raw `ron95` column | After the BUDI95 change, `ron95` became the unsubsidised price that most citizens do not pay. |
| Ridership zeros | Dropped, like nulls | Kept as 0 | Checked: zeros only appear as unbroken runs (Rapid Kuantan stopped reporting; LRT Shah Alam before opening), never as single days. |
| CI data | Synthetic raw tables + full `dbt build` in pytest | Call the real APIs in CI | Fast, deterministic, and respects the rate limit. A separate `-m live` test hits the real sources. |

## 3. Concepts I must understand

- **ELT vs ETL**: load raw data first, transform inside the warehouse with SQL. Raw stays untouched, so models can be rebuilt any time. *dbt/models/*
- **Incremental load + cursor**: remember the newest date loaded and ask only for rows after it (minus a window). dlt stores this "resource state" in the warehouse. *src/open_data_elt/pipeline.py*
- **Idempotent**: running twice gives the same result as running once. Here: merge (delete + insert) on the primary key. *pipeline.py, tests/test_pipeline.py*
- **Schema drift / schema contract**: the source's columns or types change. dlt contract `columns: evolve, data_type: freeze` plus our `required_columns` check. *extract.py, sources.py*
- **Star schema**: facts (events with numbers: riders per day per service) point to dimensions (descriptions: date, service). Keeps queries simple and joins cheap. *dbt/models/marts/*
- **Grain**: what one row means, e.g. `fct_ridership_daily` = one day × one service. Tested with a unique test on that combination. *_marts.yml*
- **ASOF join**: join each day to the latest price on or before it. Fills weekly prices and weekday FX rates forward. *int_fuel__prices_daily.sql*
- **Unpivot**: turn one column per service into one row per service. *int_ridership__long.sql*
- **dbt tests vs unit tests**: data tests check the real data (unique, not_null, relationships); unit tests check SQL logic on fixed inputs. *_staging.yml, _intermediate.yml*
- **Source freshness**: fail or warn if the newest row is too old; thresholds follow each source's publishing lag. *_sources.yml*
- **Rate limiting + backoff**: space calls 15 s apart; on HTTP 429 wait `Retry-After` and retry. *http.py*
- **Lineage**: the graph of which model reads which. dbt docs draws it. *docs/lineage.jpg*
- **Static site + build-time data loaders**: data is queried when the site is built, not when someone visits, so no server or database is exposed. *dashboard/src/data/*

## 4. Interview questions and honest answers

1. **Why ELT and not ETL?** Raw data stays as the source sent it, so I can fix a model and rebuild without re-downloading. Transformations are SQL in dbt, which gives tests and lineage for free.
2. **How is the load incremental and idempotent?** dlt keeps the newest loaded date per table. Next run asks the API for rows since that date minus 35 days, then merges on the primary key. I ran the load twice in a row and row counts did not change; a test does the same with fake data.
3. **Why re-pull 35 days if you already have them?** Sources revise recent rows. The window picks that up. The trade-off is that a silent upstream break can overwrite good rows, which the incident drill showed, so the window is guarded.
4. **What happens if data.gov.my renames a column?** The load checks a list of columns the models need. If one is missing, it stops before writing and Telegram gets the error. If that check were off, dbt's not_null test would fail and the marts would keep yesterday's data. `uv run elt drill` shows both.
5. **How do you deal with the 4 requests/minute limit?** Daily runs make about 4 small calls, spaced 15 s apart, with backoff on 429. History comes from parquet bulk files instead of the API.
6. **Why MotherDuck and not BigQuery?** Same DuckDB engine as my laptop, so the same SQL runs locally and in the cloud, and the free tier needs no card. BigQuery sandbox tables expire after 60 days. Honestly, I have not yet measured MotherDuck compute use over a month.
7. **Why not Dagster or Airflow?** One daily job with three steps. A cron in GitHub Actions is enough and costs nothing; dbt docs give the lineage graph. If there were many dependent jobs or sensors, I would move to Dagster.
8. **What does the dashboard say, and do you trust it?** Weekly RON97 changes have |r| ≤ 0.10 with weekday rail ridership; transport CPI follows RON97 weakly since 2022; ridership on the 2019 lines is 115% of 2019. These are correlations on aggregated data, not causal effects. I split the CPI result by period because the full-period r of 0.96 was driven by 2018–2021.
9. **Why did you drop Evidence?** When I checked in Nov 2026, Evidence's static build was deprecated and the new CLI self-hosts as a server. GitHub Pages needs static files, so I switched to Observable Framework.
10. **How do you test a pipeline without hitting the APIs?** pytest fakes the network for dlt runs (backfill, increment, new column, renamed column, type change) and builds the whole dbt project on a tiny synthetic warehouse. CI runs those; a `live` marker runs the real-source check on demand.

## 5. What is weak, and how to say it

- **No causal model.** "I checked for an obvious weekly link and found none. Proving there is no effect would need controls for holidays, fares and new lines; that was out of scope."
- **The cloud path is the least proven part.** "Everything runs and is tested on local DuckDB; the MotherDuck target uses the same code, and I verified dlt restores its state from the warehouse. I'll know real compute usage after a month of runs."
- **Small data.** "About 11 MB. The project is about reliability: incremental loads, drift handling, tests, alerts. Those carry over to bigger data."
- **Hand-written service names.** "The source gives only column names, so names come from a 14-row seed, and a test fails if an unknown service appears."
- **The incident is simulated.** "I injected the rename with an environment variable and ran the real commands on a copy of the warehouse. It is a drill, and I say so in the doc."
- **Pre-1.0 and changing tools.** "Evidence changed under me mid-project; I checked current docs, explained the switch, and picked a tool with static output."

## 6. Resume bullets

- **[data]** Built a daily ELT pipeline (dlt, dbt, DuckDB/MotherDuck, GitHub Actions) loading 5 Malaysian open datasets (ridership, fuel prices, CPI, BNM FX) into a tested star schema with 50 dbt tests and source freshness checks, at RM 0 running cost.
- **[data]** Made loads incremental and idempotent (merge on keys, 35-day revision window, 4 req/min rate limiting); reruns add 0 rows and a fresh CI runner resumes from state stored in the warehouse.
- **[data/SWE]** Designed two-layer schema-drift protection and proved it with a reproducible incident drill: a renamed source column stops the load before any write; without the guard, a dbt test catches 6 nulled prices and the next run repairs them.
- **[data]** Published a static dashboard (Observable Framework, GitHub Pages) showing weekly RON97 changes have |r| ≤ 0.10 with Klang Valley rail ridership, and weekday ridership on 2019 lines at 115% of pre-COVID levels.
- **[cloud]** Automated a scheduled cloud pipeline with GitHub Actions, MotherDuck and GitHub Pages, with Telegram failure alerts that quote the failing error line and link to the run.
