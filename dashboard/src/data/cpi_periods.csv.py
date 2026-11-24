# Correlation of transport CPI year-on-year % with RON97 and citizen RON95
# year-on-year %, split at 2022 (RON95 swung widely before, barely after).
from open_data_elt.export import emit_csv

emit_csv("""
with m as (
    select month_start, cpi_transport_yoy_pct as cpi,
        100 * (ron97_price / lag(ron97_price, 12) over w - 1) as r97,
        100 * (ron95_citizen_price / lag(ron95_citizen_price, 12) over w - 1) as r95
    from marts.mart_transport_monthly
    window w as (order by month_start)
),
p as (
    select *, case when month_start < date '2022-01-01' then '2018-2021' else '2022-now' end
        as period
    from m
    where month_start >= date '2018-04-01' and cpi is not null and r97 is not null
)
select period, corr(cpi, r97) as r_ron97, corr(cpi, r95) as r_ron95_citizen,
       stddev(r95) as ron95_yoy_sd, regr_slope(cpi, r97) as cpi_pts_per_ron97_pt,
       count(*) as months, min(month_start) as first_month, max(month_start) as last_month
from p
group by period
order by period
""")
