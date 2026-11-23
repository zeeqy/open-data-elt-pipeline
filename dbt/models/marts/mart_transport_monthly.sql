-- One row per month: ridership, fuel, transport CPI and USD/MYR side by side.
with ridership as (
    select
        d.month_start,
        sum(r.riders) filter (where s.is_rapid_kl_rail) as rapid_kl_rail_riders,
        sum(r.riders) filter (where s.mode = 'bus') as bus_riders
    from {{ ref('fct_ridership_daily') }} as r
    join {{ ref('dim_service') }} as s using (service_code)
    join {{ ref('dim_date') }} as d using (date_day)
    group by 1
),

rail_days as (
    select
        d.month_start,
        avg(day_total) filter (where not d.is_weekend) as avg_weekday_rail_riders,
        avg(day_total) filter (where d.is_weekend) as avg_weekend_rail_riders,
        count(*) as days_reported
    from (
        select r.date_day, sum(r.riders) as day_total
        from {{ ref('fct_ridership_daily') }} as r
        join {{ ref('dim_service') }} as s using (service_code)
        where s.is_rapid_kl_rail
        group by 1
    ) as t
    join {{ ref('dim_date') }} as d using (date_day)
    group by 1
),

prices as (
    select
        d.month_start,
        avg(f.ron97_price) as ron97_price,
        avg(f.ron95_citizen_price) as ron95_citizen_price,
        avg(f.diesel_price) as diesel_price,
        avg(x.usd_myr) as usd_myr
    from {{ ref('dim_date') }} as d
    left join {{ ref('fct_fuel_price_daily') }} as f using (date_day)
    left join {{ ref('fct_fx_daily') }} as x using (date_day)
    group by 1
),

cpi as (
    select
        month_start,
        max(cpi_index) filter (where division_code = '07') as cpi_transport,
        max(yoy_pct) filter (where division_code = '07') as cpi_transport_yoy_pct,
        max(yoy_pct) filter (where division_code = 'overall') as cpi_overall_yoy_pct
    from {{ ref('fct_cpi_monthly') }}
    group by 1
)

select
    p.month_start,
    rd.avg_weekday_rail_riders,
    rd.avg_weekend_rail_riders,
    rd.days_reported,
    r.rapid_kl_rail_riders,
    r.bus_riders,
    p.ron97_price,
    p.ron95_citizen_price,
    p.diesel_price,
    p.usd_myr,
    c.cpi_transport,
    c.cpi_transport_yoy_pct,
    c.cpi_overall_yoy_pct
from prices as p
left join ridership as r using (month_start)
left join rail_days as rd using (month_start)
left join cpi as c using (month_start)
