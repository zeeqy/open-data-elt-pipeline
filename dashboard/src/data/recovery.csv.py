# Average weekday riders per year on the Rapid KL rail lines that already ran
# in January 2019 (like-for-like: newer lines would flatter the recovery).
from open_data_elt.export import emit_csv

emit_csv("""
with lines_2019 as (
    select service_code
    from marts.fct_ridership_daily
    join marts.dim_service using (service_code)
    where is_rapid_kl_rail and date_day < date '2019-02-01'
    group by service_code
),
daily as (
    select r.date_day, sum(r.riders) as riders
    from marts.fct_ridership_daily as r
    join lines_2019 using (service_code)
    join marts.dim_date as d using (date_day)
    where not d.is_weekend
    group by r.date_day
),
yearly as (
    select year(date_day) as year, avg(riders) as avg_weekday_riders, count(*) as weekdays
    from daily group by 1
)
select year, avg_weekday_riders, weekdays,
       100 * avg_weekday_riders / (select avg_weekday_riders from yearly where year = 2019)
           as pct_of_2019,
       (select string_agg(service_code, ' ' order by service_code) from lines_2019) as lines
from yearly
order by year
""")
