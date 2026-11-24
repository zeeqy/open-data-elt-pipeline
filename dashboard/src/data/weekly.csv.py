# Weekly Rapid KL rail weekday riders and fuel prices (full weeks only).
from open_data_elt.export import emit_csv

emit_csv("""
select week_start, avg_weekday_rail_riders, weekdays_reported, ron97_price,
       ron95_citizen_price, diesel_price, usd_myr, riders_wow_pct, ron97_wow_pct
from marts.mart_transport_weekly
where week_start >= date '2019-01-07'
order by week_start
""")
