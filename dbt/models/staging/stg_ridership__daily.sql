-- One row per day, one column per service. Cast counts back to integers
-- (the loader stores every measure as double so API and parquet rows match).
select
    cast(date as date) as date_day,
    {% for col in ['rail_lrt_ampang', 'rail_lrt_kj', 'rail_lrt_shah_alam', 'rail_mrt_kajang',
                   'rail_mrt_pjy', 'rail_monorail', 'rail_komuter', 'rail_komuter_utara',
                   'rail_ets', 'rail_intercity', 'rail_tebrau', 'bus_rkl', 'bus_rkn', 'bus_rpn'] %}
    cast({{ col }} as bigint) as {{ col }}{{ ',' if not loop.last }}
    {% endfor %}
from {{ source('raw', 'ridership_headline') }}
