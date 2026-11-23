"""End-to-end dlt runs into a temp DuckDB, with the network replaced by fakes."""

import datetime as dt

import dlt
import duckdb
import pytest

from open_data_elt import extract, pipeline
from open_data_elt.extract import SchemaDriftError, normalize_row
from open_data_elt.sources import CATALOGUE_SOURCES

FUEL = CATALOGUE_SOURCES["fuelprice"]


def fuel(date, ron95, origin="parquet", **extra):
    row = {"date": date, "series_type": "level", "ron95": ron95, "ron97": 4.0, "diesel": 4.7}
    return normalize_row(row | extra, FUEL, origin)


@pytest.fixture
def env(tmp_path, monkeypatch):
    calls = {"api_since": []}
    parquet_rows = [fuel("2026-11-05", 4.27), fuel("2026-11-12", 3.87)]
    api_rows = []

    def fake_parquet(src, raw_dir=None):
        if src.id == "mcoicop":
            return [
                {
                    "division": "07",
                    "group": "-",
                    "class": "-",
                    "subclass": "-",
                    "desc_en": "Transport",
                }
            ]
        return parquet_rows

    def fake_api(src, since):
        calls["api_since"].append(since)
        extract.check_columns(set().union(*(r.keys() for r in api_rows)) - {"_origin"}, src)
        return api_rows, {"data_as_of": "2026-11-19"}

    monkeypatch.setattr(extract, "fetch_parquet", fake_parquet)
    monkeypatch.setattr(extract, "fetch_api", fake_api)
    db = tmp_path / "w.duckdb"

    def run(**kw):
        return pipeline.run(
            only=["fuelprice", "mcoicop"],
            destination=dlt.destinations.duckdb(str(db)),
            pipelines_dir=tmp_path / "dlt",
            **kw,
        )

    def query(sql):
        with duckdb.connect(str(db), read_only=True) as con:
            return con.sql(sql).fetchall()

    return run, query, api_rows, calls


def test_first_run_backfills_then_increments_without_duplicates(env):
    run, query, api_rows, calls = env
    run()
    assert query("select count(*) from raw.fuelprice") == [(2,)]
    assert calls["api_since"] == []  # first run used the bulk file

    # The API re-sends 12 Nov (revised price) and adds 19 Nov.
    api_rows += [fuel("2026-11-12", 3.85, "api"), fuel("2026-11-19", 3.72, "api")]
    run()
    run()  # running again changes nothing
    assert calls["api_since"][0] == dt.date(2026, 11, 12) - dt.timedelta(days=FUEL.lookback_days)
    assert query("select date::varchar, ron95 from raw.fuelprice order by date") == [
        ("2026-11-05", 4.27),
        ("2026-11-12", 3.85),
        ("2026-11-19", 3.72),
    ]


def test_new_column_is_added(env):
    run, query, api_rows, _ = env
    run()
    api_rows.append(fuel("2026-11-19", 3.72, "api", ron95_new_subsidy=1.89))
    run()
    assert query("select ron95_new_subsidy from raw.fuelprice where date = '2026-11-19'") == [
        (1.89,)
    ]


def test_renamed_column_stops_the_load(env):
    run, query, api_rows, _ = env
    run()
    row = fuel("2026-11-19", 3.72, "api")
    row["ron97_price"] = row.pop("ron97")
    api_rows.append(row)
    with pytest.raises(Exception) as info:
        run()
    assert isinstance(_root(info.value), SchemaDriftError)
    assert query("select count(*) from raw.fuelprice") == [(2,)]  # nothing half-loaded


def test_changed_type_stops_the_load(env):
    run, query, api_rows, _ = env
    run()
    api_rows.append(fuel("2026-11-19", "3.72 RM", "api"))
    with pytest.raises(Exception, match="(?i)contract|data type"):
        run()
    assert query("select count(*) from raw.fuelprice") == [(2,)]


def _root(err):
    while err.__cause__ or err.__context__:
        err = err.__cause__ or err.__context__
    return err
