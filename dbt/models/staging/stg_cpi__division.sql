select
    cast(date as date) as month_start,
    division as division_code,
    "index" as cpi_index
from {{ source('raw', 'cpi_headline') }}
