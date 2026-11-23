select
    month_start,
    division_code,
    cpi_index,
    round(100 * (cpi_index / lag(cpi_index, 12) over w - 1), 2) as yoy_pct
from {{ ref('stg_cpi__division') }}
window w as (partition by division_code order by month_start)
