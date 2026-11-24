# DEMO: 60–90 second video script

**Hook (0:00–0:07).** "Malaysia publishes ridership, fuel prices and inflation as open data. I built a pipeline that loads all of it every morning, tests it, and costs zero ringgit."

| # | Time | On screen | Say |
|---|---|---|---|
| 1 | 0:07–0:20 | Dashboard top: 4 cards (1,098,426 weekday riders, 115% of 2019, RON97 RM 4.00, transport CPI +4.2%) | "This dashboard rebuilds itself daily from five sources: rail and bus ridership, weekly fuel prices, CPI and Bank Negara's exchange rate." |
| 2 | 0:20–0:35 | Scroll to question 1: the scatter plot and lag bars | "Do fuel price changes move ridership? Since 2023, the correlation is never above 0.1, even a month later. Most drivers pay subsidised RON95, which barely changed." |
| 3 | 0:35–0:47 | Terminal: `uv run elt load` showing `incremental via API since ...` and row counts; then run it again, same counts | "dlt loads only what's new, within the API's 4-requests-a-minute limit, and merges on keys, so running it twice adds zero rows." |
| 4 | 0:47–1:00 | dbt docs lineage graph (`docs/lineage.jpg`), then `elt transform` ending with `PASS=69` | "dbt turns it into a star schema. Sixty-nine checks, 50 of them tests, plus freshness, run every morning." |
| 5 | 1:00–1:15 | Terminal: `uv run elt drill` output, the SchemaDriftError line, then the FAIL 6 not_null line | "What if the source renames a column? The load stops before writing. Even with that check off, dbt catches the six prices that would have been wiped, and the next run repairs them." |
| 6 | 1:15–1:25 | GitHub Actions run page (green), the Telegram alert text from INCIDENT.md | "It runs on a GitHub Actions cron, publishes to GitHub Pages, and pings Telegram if anything fails." |

**Closing (1:25–1:30).** "Incremental, tested, alerting, and free to run. The code and the incident write-up are on my GitHub."
