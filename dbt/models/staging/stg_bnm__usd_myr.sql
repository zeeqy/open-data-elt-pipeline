-- Middle rate per 1 unit of currency. Falls back to the buying/selling midpoint
-- if BNM leaves middle_rate empty.
select
    cast(date as date) as rate_date,
    currency,
    coalesce(middle_rate, (buying_rate + selling_rate) / 2) / unit as myr_per_unit
from {{ source('raw', 'bnm_exchange_rate') }}
where currency = 'USD'
