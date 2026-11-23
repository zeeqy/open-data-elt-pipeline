-- Division level only (2-digit codes) plus the 'overall' row.
select
    division as division_code,
    desc_en as division_name,
    desc_bm as division_name_bm
from {{ source('raw', 'mcoicop') }}
where "group" = '-' and "class" = '-' and subclass = '-'
