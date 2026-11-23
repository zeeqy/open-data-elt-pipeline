-- The price in force on each day = the latest weekly price on or before it.
select
    s.date_day,
    p.effective_date,
    s.date_day = p.effective_date as is_price_update_day,
    p.ron95_market_price,
    p.ron95_citizen_price,
    p.ron97_price,
    p.diesel_price,
    p.is_budi95_period
from {{ ref('int_date_spine') }} as s
asof join {{ ref('stg_fuel__prices') }} as p
    on s.date_day >= p.effective_date
