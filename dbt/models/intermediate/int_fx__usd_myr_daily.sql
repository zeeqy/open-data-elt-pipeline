-- Carry the last BNM fixing over weekends and public holidays.
select
    s.date_day,
    f.rate_date as fixing_date,
    f.myr_per_unit as usd_myr
from {{ ref('int_date_spine') }} as s
asof join {{ ref('stg_bnm__usd_myr') }} as f
    on s.date_day >= f.rate_date
