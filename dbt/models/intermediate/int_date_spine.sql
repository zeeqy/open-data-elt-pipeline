-- Every calendar day from 2017-01-01 to the newest date in any daily/weekly source.
with bounds as (
    select greatest(
        (select max(effective_date) from {{ ref('stg_fuel__prices') }}),
        (select max(rate_date) from {{ ref('stg_bnm__usd_myr') }}),
        (select max(date_day) from {{ ref('stg_ridership__daily') }})
    ) as last_day
)
select cast(d as date) as date_day
from bounds, generate_series(date '2017-01-01', bounds.last_day, interval 1 day) as t(d)
