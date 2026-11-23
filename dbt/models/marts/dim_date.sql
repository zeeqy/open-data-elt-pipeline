select
    date_day,
    cast(date_trunc('month', date_day) as date) as month_start,
    cast(date_trunc('week', date_day) as date) as week_start,  -- ISO week, Monday
    year(date_day) as year,
    month(date_day) as month,
    isodow(date_day) as iso_day_of_week,  -- 1 = Monday
    dayname(date_day) as day_name,
    isodow(date_day) >= 6 as is_weekend
from {{ ref('int_date_spine') }}
