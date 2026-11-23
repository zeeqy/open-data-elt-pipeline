-- Names and modes from the hand-written seed (the source only gives column names).
select
    service_code,
    service_name,
    mode,
    operator,
    region,
    is_rapid_kl_rail
from {{ ref('ridership_services') }}
