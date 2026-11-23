select division_code, division_name, division_name_bm
from {{ ref('stg_dosm__mcoicop_divisions') }}
