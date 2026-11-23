-- One row per ISO week: Rapid KL rail ridership next to fuel prices and USD/MYR.
-- Used for "do fuel price changes move ridership?". Weekday riders only, so
-- holidays-on-weekends and weekend leisure trips do not blur commuting.
with rail as (
    select
        d.week_start,
        r.date_day,
        sum(r.riders) as riders
    from {{ ref('fct_ridership_daily') }} as r
    join {{ ref('dim_service') }} as s using (service_code)
    join {{ ref('dim_date') }} as d using (date_day)
    where s.is_rapid_kl_rail and not d.is_weekend
    group by 1, 2
),

rail_weekly as (
    select week_start, avg(riders) as avg_weekday_rail_riders, count(*) as weekdays_reported
    from rail
    group by 1
),

prices_weekly as (
    select
        d.week_start,
        avg(f.ron97_price) as ron97_price,
        avg(f.ron95_citizen_price) as ron95_citizen_price,
        avg(f.diesel_price) as diesel_price,
        avg(x.usd_myr) as usd_myr
    from {{ ref('dim_date') }} as d
    join {{ ref('fct_fuel_price_daily') }} as f using (date_day)
    join {{ ref('fct_fx_daily') }} as x using (date_day)
    group by 1
)

select
    p.week_start,
    r.avg_weekday_rail_riders,
    r.weekdays_reported,
    p.ron97_price,
    p.ron95_citizen_price,
    p.diesel_price,
    p.usd_myr,
    r.avg_weekday_rail_riders / lag(r.avg_weekday_rail_riders) over w - 1 as riders_wow_pct,
    p.ron97_price / lag(p.ron97_price) over w - 1 as ron97_wow_pct
from prices_weekly as p
left join rail_weekly as r using (week_start)
window w as (order by p.week_start)
