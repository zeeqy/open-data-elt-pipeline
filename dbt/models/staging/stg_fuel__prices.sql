-- Price levels only (the source also holds week-on-week changes).
-- From 2025-09-30, `ron95` is the unsubsidised price and eligible citizens pay
-- the BUDI95 price, so ron95_citizen_price picks whichever one applied.
select
    cast(date as date) as effective_date,
    ron95 as ron95_market_price,
    coalesce(ron95_budi95, ron95) as ron95_citizen_price,
    ron97 as ron97_price,
    diesel as diesel_price,
    diesel_eastmsia as diesel_east_my_price,
    ron95_budi95 is not null as is_budi95_period
from {{ source('raw', 'fuelprice') }}
where series_type = 'level'
