# Sources

All checked by hand on 2026-11-23. Cost: RM 0, no API key needed.

| Dataset | Publisher | How we read it | Grain | History | Updates |
|---|---|---|---|---|---|
| `ridership_headline` | Prasarana / KTMB via data.gov.my | API (incremental) + parquet (backfill) | 1 row per day, 1 column per rail line / bus network | 2019-01-01 → 2026-10-31 | Daily, ~3 weeks lag |
| `fuelprice` | Ministry of Finance via data.gov.my | API + parquet | 2 rows per week: `series_type` = `level` and `change_weekly` | 2017-03-30 → 2026-11-19 | Weekly (Wednesday night) |
| `cpi_headline` | DOSM | API + parquet (`cpi_2d.parquet`) | 1 row per month per MCOICOP division (`overall`, `01`–`13`) | 1980-01 → 2026-10 | Monthly (API meta gives `next_update`) |
| `mcoicop` | DOSM | API + parquet | Lookup: division/group/class codes → English + Malay names | n/a | Rarely |
| USD/MYR exchange rate | Bank Negara Malaysia Open API | `GET /public/exchange-rate/USD/year/{y}/month/{m}?session=1200` | 1 row per business day (buying, selling, middle) | Same API used in project 03 | Daily |

## Endpoints

- data.gov.my: `https://api.data.gov.my/data-catalogue/?id=<id>`. The trailing slash matters: without it the server returns `301` with an empty body.
  - Incremental: `&date_start=YYYY-MM-DD@date`. Metadata: `&meta=true` returns `data_as_of`, `last_updated`, `next_update` (used for freshness checks).
  - Docs: https://developer.data.gov.my/request-query
- Bulk parquet files (for backfill, no rate limit stated):
  - https://storage.data.gov.my/transportation/ridership_headline.parquet
  - https://storage.data.gov.my/commodities/fuelprice.parquet
  - https://storage.dosm.gov.my/cpi/cpi_2d.parquet (the `cpi_headline` file name returns 404; `cpi_2d` is the same table)
  - https://storage.dosm.gov.my/dictionaries/mcoicop.parquet
- BNM: `https://api.bnm.gov.my/public/exchange-rate/...` with header `Accept: application/vnd.BNM.API.v1+json`.

## Things that differ from what you might expect

- **Rate limit: 4 requests per minute** per API (https://developer.data.gov.my/rate-limit). We saw `429` on the 4th quick call. So each scheduled run makes only 4 small API calls, retries `429` with backoff, and backfills come from the parquet files.
- `fuelprice` mixes price levels and week-on-week changes in one table. Staging must filter `series_type = 'level'`.
- Subsidised RON95 (`ron95_budi95`, `ron95_skps`) and diesel (`diesel_budi`, `diesel_skds`) columns only appear in later years (null before). This is real schema drift inside the source.
- Ridership columns for some lines are null in early years (lines that had not opened or were not reported yet). Some bus columns are `0.0` instead of null.
- The CPI parquet stores `date` as a timestamp (`1980-01-01 00:00:00`), the others as a date. Staging casts all to `date`.
- Probe on 2026-11-23 (`uv run elt probe`): ridership 2,861 rows (no missing days), fuel 975, CPI 7,868 (562 months × 14 divisions), mcoicop 343. All primary keys unique.
- CPI division codes follow MCOICOP (13 divisions, `07` = Transport). Names come from the `mcoicop` lookup, not typed by hand.

## License

data.gov.my and OpenDOSM: Creative Commons Attribution 4.0 (CC BY 4.0). BNM Open API: public, free to use. Attribution goes in the README and the dashboard footer.
