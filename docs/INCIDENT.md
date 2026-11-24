# Incident drill: the source renames a column

**Date:** 2026-11-24 · **Type:** simulated (drill) · **Reproduce:** `uv run elt drill` · **Raw output:** [incident_drill_output.txt](incident_drill_output.txt)

## Scenario

data.gov.my renames the `ron97` column of the `fuelprice` dataset to `ron97_price`. Nothing else changes: same rows, same values. This is the most common kind of upstream break: no error from the API, just a different column name.

The drill runs the real `elt load` and `elt transform` commands as separate processes on a copy of the warehouse (`data/drill/`), with an environment variable that renames the column in the rows the API returns. The real warehouse is not touched.

## What happened

### 1. Normal pipeline (load-time guard on): stopped before writing

```
$ ELT_DRILL_RENAME=fuelprice:ron97=ron97_price elt load --only fuelprice   -> exit 1
   [load] fuelprice: incremental via API since 2026-10-15 (last loaded 2026-11-19)
   LOAD FAILED: SchemaDriftError: fuelprice: required column(s) ['ron97'] missing from source.
   Columns received: [..., 'ron97_price', 'series_type']. Did the source rename a column?
```

- `raw.fuelprice` unchanged: 975 rows, latest RON97 still RM 4.00 / 4.20 / 4.70.
- The dlt state did not move, so the next run retries the same window.
- In GitHub Actions the failed step triggers the Telegram alert. Its text (built by `elt alert` from the step log):

```
[FAILED] open-data-elt pipeline, step: load

LOAD FAILED: SchemaDriftError: fuelprice: required column(s) ['ron97'] missing from source. Columns received: [...'ron97_price', 'series_type']. Did the source rename a column?

https://github.com/<owner>/open-data-elt-pipeline/actions/runs/<id>
```

**Time to detect:** the same run (minutes after the source changed). **Bad data written:** none.

### 2. Counterfactual (guard off): what a pipeline without the check does

```
$ ELT_DRILL_RENAME=... ELT_DRILL_SKIP_GUARD=1 elt load --only fuelprice   -> exit 0
   [after load] level rows with NULL ron97 since 2018 = 6, column ron97_price exists = True
   [after load] latest (date, ron97, ron97_price):
                ('2026-11-19', None, 4.0), ('2026-11-12', None, 4.2), ('2026-11-05', None, 4.7)
$ elt transform --skip-freshness   -> exit 1
   FAIL 6 not_null_stg_fuel__prices_ron97_price
   Done. PASS=39 WARN=0 ERROR=1 SKIP=29 TOTAL=69
```

The load "succeeds": dlt's schema evolution adds `ron97_price` as a new column. But the **35-day revision window** re-pulls the last 6 weeks and the merge overwrites them, so 6 real RON97 prices become NULL. A design choice that protects against late revisions makes this failure worse.

The second line of defence catches it: dbt's `not_null` test on `stg_fuel__prices.ron97_price` fails with 6 rows, and `dbt build` skips the 29 models and tests downstream. The marts are tables, so they keep yesterday's correct data: the dashboard goes stale, not wrong.

### 3. Recovery

When the source is fixed (or the pipeline is changed to map the new name), the next normal run repairs the data with no manual SQL:

```
$ elt load --only fuelprice   -> exit 0
   [after load] level rows with NULL ron97 since 2018 = 0
   latest (date, ron97, ron97_price): ('2026-11-19', 4.0, None), ...
$ elt transform --skip-freshness   -> exit 0
   Done. PASS=69 WARN=0 ERROR=0 SKIP=0 TOTAL=69
```

The merge on `(date, series_type)` rewrites the same 6 rows with the right values. Left behind: an empty `ron97_price` column in `raw.fuelprice`, because dlt never drops columns. It is harmless (staging selects columns by name) and can be dropped by hand.

## Why it was caught

| Layer | Check | Where | Result in the drill |
|---|---|---|---|
| Load | `required_columns` per source; missing one raises `SchemaDriftError` before dlt writes | `src/open_data_elt/extract.py`, `sources.py` | Caught, nothing written |
| Load | dlt schema contract `data_type: freeze` (a type change, e.g. `"4.00 RM"`, also stops the load) | `pipeline.py` | Not triggered (values still numbers) |
| Transform | dbt `not_null` on the columns the marts use | `dbt/models/staging/_staging.yml` | Caught (when the load guard is off) |
| Serve | Marts are tables; a failed build leaves the last good version | `dbt_project.yml` | Dashboard stale, not wrong |
| Alert | Any failed step sends Telegram with the error lines and run link | `.github/workflows/pipeline.yml`, `alert.py` | Message shown above |

## What we would do in a real incident

1. Read the alert; open the run link; confirm the new column name on https://data.gov.my/data-catalogue/fuelprice.
2. If the rename is permanent: rename it back in extract (one line, like the drill hook) or update `required_columns` + the staging model, add a test, push. The next scheduled run catches up thanks to the revision window.
3. Optionally drop the empty leftover column.

## Lessons

- Schema evolution alone is not safety: "column added" hides "column removed". Name the columns you depend on.
- Overlapping incremental windows amplify silent upstream breaks. Keep them, but guard them.
- Two independent layers (load guard + dbt tests) meant either one alone would have caught this.
