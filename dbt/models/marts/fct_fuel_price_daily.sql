select
    date_day,
    effective_date,
    is_price_update_day,
    ron95_market_price,
    ron95_citizen_price,
    ron97_price,
    diesel_price,
    is_budi95_period
from {{ ref('int_fuel__prices_daily') }}
