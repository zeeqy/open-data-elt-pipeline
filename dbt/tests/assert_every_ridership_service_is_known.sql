-- A new column in the source (a new line opening) must be added to the seed,
-- or it would silently vanish from the marts after the inner join.
select distinct r.service_code
from {{ ref('int_ridership__long') }} as r
left join {{ ref('ridership_services') }} as s using (service_code)
where s.service_code is null
