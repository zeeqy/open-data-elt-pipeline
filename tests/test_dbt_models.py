"""Build the whole dbt project (seeds, models, data tests, unit tests) on a tiny
synthetic raw dataset, so CI checks the models without calling any API."""

import duckdb
import pytest

from open_data_elt import transform

RAW_SQL = """
create schema raw;
create table raw.ridership_headline as
select cast(d as date) as date,
       150000.0 + 1000 * i as rail_lrt_ampang, 200000.0 as rail_lrt_kj, 0.0 as rail_lrt_shah_alam,
       250000.0 as rail_mrt_kajang, 150000.0 as rail_mrt_pjy, 50000.0 as rail_monorail,
       20000.0 as rail_komuter, 18000.0 as rail_komuter_utara, 19000.0 as rail_ets,
       4000.0 as rail_intercity, 9000.0 as rail_tebrau, 250000.0 as bus_rkl,
       null::double as bus_rkn, 50000.0 as bus_rpn, 'parquet' as _origin
from generate_series(date '2026-11-02', date '2026-11-15', interval 1 day) with ordinality t(d, i);

create table raw.fuelprice as
select * from (values
  (date '2026-11-05', 'level', 4.27, 4.70, 5.12, 5.12, 1.99, 2.05, 2.15, 2.10, 'api'),
  (date '2026-11-12', 'level', 3.87, 4.20, 4.87, 4.87, 1.99, 2.05, 2.15, 2.10, 'api'),
  (date '2026-11-12', 'change_weekly', -0.4, -0.5, -0.25, -0.25, 0, 0, 0, 0, 'api')
) t(date, series_type, ron95, ron97, diesel, diesel_eastmsia, ron95_budi95, ron95_skps,
    diesel_skds, diesel_budi, _origin);

create table raw.mcoicop as
select * from (values
  (1, 'overall', '-', '-', '-', 'All items', 'Semua item'),
  (2, '07', '-', '-', '-', 'Transport', 'Pengangkutan'),
  (3, '07', '071', '-', '-', 'Purchase of vehicles', 'Pembelian kenderaan')
) t(digits, division, "group", "class", subclass, desc_en, desc_bm);

create table raw.cpi_headline as
select cast(m as date) as date, div as division, 120.0 + 0.1 * i as "index", 'parquet' as _origin
from generate_series(date '2025-01-01', date '2026-10-01', interval 1 month)
     with ordinality t(m, i),
     (values ('overall'), ('07')) v(div);

create table raw.bnm_exchange_rate as
select 'USD' as currency, cast(d as date) as date, 1.0 as unit, 4.06 as buying_rate,
       4.08 as selling_rate, 4.07 as middle_rate, '1200' as session, 'api' as _origin
from generate_series(date '2026-11-02', date '2026-11-14', interval 1 day) t(d)
where isodow(d) <= 5;
"""


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    path = tmp_path_factory.mktemp("wh") / "w.duckdb"
    with duckdb.connect(str(path)) as con:
        con.execute(RAW_SQL)
    assert transform.build(path, freshness=False), "dbt build failed, see output above"
    return path


def q(path, sql):
    # Same config as dbt's still-open in-process connection (DuckDB refuses a mix).
    with duckdb.connect(str(path)) as con:
        return con.sql(sql).fetchall()


def test_zero_and_null_ridership_are_dropped(warehouse):
    services = {
        r[0] for r in q(warehouse, "select distinct service_code from marts.fct_ridership_daily")
    }
    assert "rail_lrt_shah_alam" not in services  # all zeros
    assert "bus_rkn" not in services  # all null
    assert len(services) == 12


def test_change_rows_are_not_prices(warehouse):
    assert q(warehouse, "select count(*) from staging.stg_fuel__prices") == [(2,)]


def test_fx_carried_over_weekend(warehouse):
    assert q(
        warehouse,
        "select usd_myr, fixing_date::varchar from marts.fct_fx_daily "
        "where date_day = '2026-11-15'",
    ) == [(4.07, "2026-11-13")]  # Sun 15 Nov uses Fri 13 Nov


def test_cpi_yoy(warehouse):
    # index rises 0.1 per month, so Oct 2026 vs Oct 2025 = (122.2 / 121.0) - 1
    got = q(
        warehouse,
        "select yoy_pct from marts.fct_cpi_monthly "
        "where division_code = '07' and month_start = '2026-10-01'",
    )
    assert got == [(round(100 * (122.2 / 121.0 - 1), 2),)]


def test_weekly_mart_uses_weekdays_only(warehouse):
    rows = q(
        warehouse,
        "select weekdays_reported from marts.mart_transport_weekly where week_start = '2026-11-02'",
    )
    assert rows == [(5,)]
