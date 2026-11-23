select date_day, fixing_date, usd_myr
from {{ ref('int_fx__usd_myr_daily') }}
