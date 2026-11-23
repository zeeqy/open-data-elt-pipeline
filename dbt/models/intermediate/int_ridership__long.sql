-- Wide -> long: one row per day per service.
-- Nulls (service not running / not reported) are dropped by UNPIVOT.
-- Zeros are dropped too. Checked 2026-11-23: they only occur as unbroken runs
-- where a service was not running or not reporting, never as single days:
--   bus_rkn            0 every day from 2025-12-15 (stopped reporting)
--   rail_lrt_shah_alam 0 from 2026-04-01 until first riders on 2026-06-29 (not yet open)
with long as (
    unpivot {{ ref('stg_ridership__daily') }}
    on columns(* exclude (date_day))
    into name service_code value riders
)
select date_day, service_code, riders
from long
where riders > 0
