-- Catch unit or parsing errors (e.g. sen instead of RM, or a shifted column).
-- Bounds are wide on purpose: the real range 2017-2026 is RM 1.25 to RM 6.72
-- (diesel peaked at RM 6.72 on 2026-04-09). A first version capped at RM 6
-- and failed on those genuine April 2026 prices, so the cap is now RM 10.
select *
from {{ ref('stg_fuel__prices') }}
where least(ron95_market_price, ron95_citizen_price, ron97_price, diesel_price) < 1
   or greatest(ron95_market_price, ron95_citizen_price, ron97_price, diesel_price) > 10
