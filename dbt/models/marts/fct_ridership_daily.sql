select
    date_day,
    service_code,
    riders
from {{ ref('int_ridership__long') }}
