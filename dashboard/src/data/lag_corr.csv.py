# Correlation of weekly % change in weekday rail riders with the % change in
# RON97 k weeks earlier (k = 0..4), full weeks since 2023 (after the COVID
# recovery, so the trend does not dominate).
from open_data_elt.export import emit_csv

emit_csv("""
with w as (
    select *, row_number() over (order by week_start) as n
    from marts.mart_transport_weekly
    where week_start >= date '2023-01-02'
),
lags as (select range as k from range(0, 5))
select lags.k as lag_weeks,
       corr(a.riders_wow_pct, b.ron97_wow_pct) as r,
       count(*) as weeks
from lags, w as a
join w as b on a.n = b.n + lags.k
where a.weekdays_reported = 5 and b.ron97_wow_pct is not null
group by lags.k
order by lags.k
""")
