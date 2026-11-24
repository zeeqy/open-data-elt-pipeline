# Monthly ridership, fuel, transport CPI and USD/MYR, plus fuel year-on-year %.
from open_data_elt.export import emit_csv

emit_csv("""
select *,
    100 * (ron97_price / lag(ron97_price, 12) over w - 1) as ron97_yoy_pct,
    100 * (ron95_citizen_price / lag(ron95_citizen_price, 12) over w - 1) as ron95_citizen_yoy_pct
from marts.mart_transport_monthly
window w as (order by month_start)
order by month_start
""")
