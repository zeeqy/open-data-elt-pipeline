import datetime as dt
import math

import duckdb
import pytest

from open_data_elt import http
from open_data_elt.extract import (
    SchemaDriftError,
    check_columns,
    months,
    normalize_row,
    read_parquet_rows,
)
from open_data_elt.sources import CATALOGUE_SOURCES

FUEL = CATALOGUE_SOURCES["fuelprice"]
CPI = CATALOGUE_SOURCES["cpi_headline"]
RIDERSHIP = CATALOGUE_SOURCES["ridership_headline"]


def test_normalize_makes_api_and_parquet_rows_identical():
    api = {"date": "2026-10-01", "division": "07", "index": 126}
    parquet = {"date": dt.datetime(2026, 10, 1), "division": "07", "index": 126.0}
    a, p = normalize_row(api, CPI, "api"), normalize_row(parquet, CPI, "parquet")
    assert a.pop("_origin") == "api" and p.pop("_origin") == "parquet"
    assert a == p == {"date": dt.date(2026, 10, 1), "division": "07", "index": 126.0}


def test_normalize_nan_to_none_and_ints_to_float():
    row = normalize_row(
        {"date": "2026-10-31", "rail_lrt_kj": 177109, "bus_rkn": math.nan}, RIDERSHIP, "api"
    )
    assert row["rail_lrt_kj"] == 177109.0 and isinstance(row["rail_lrt_kj"], float)
    assert row["bus_rkn"] is None


def test_check_columns_allows_new_and_rejects_missing():
    cols = {"date", "series_type", "ron95", "ron97", "diesel"}
    assert check_columns(cols | {"ron95_new_subsidy"}, FUEL) == {"ron95_new_subsidy"}
    with pytest.raises(SchemaDriftError, match=r"\['ron97'\]"):
        check_columns((cols - {"ron97"}) | {"ron97_price"}, FUEL)


def test_renamed_column_in_parquet_is_caught(tmp_path):
    path = tmp_path / "fuel.parquet"
    duckdb.sql(
        "copy (select date '2026-11-19' as date, 'level' as series_type, 3.72 as ron95, "
        f"4.0 as ron97_price, 4.72 as diesel) to '{path.as_posix()}' (format parquet)"
    )
    with pytest.raises(SchemaDriftError, match="rename a column"):
        read_parquet_rows(path, FUEL)


def test_months_crosses_year_end():
    assert list(months((2025, 11), dt.date(2026, 2, 3))) == [
        (2025, 11),
        (2025, 12),
        (2026, 1),
        (2026, 2),
    ]


class FakeResponse:
    def __init__(self, status, headers=None):
        self.status_code, self.headers = status, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self, statuses):
        self.statuses, self.calls = list(statuses), 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return self.statuses.pop(0)


def test_http_retries_429_using_retry_after():
    waits = []
    session = FakeSession([FakeResponse(429, {"Retry-After": "7"}), FakeResponse(200)])
    resp = http.get("https://example.test/x", session=session, sleep=waits.append)
    assert resp.status_code == 200 and session.calls == 2 and 7.0 in waits


def test_http_gives_up_after_max_tries():
    session = FakeSession([FakeResponse(503)] * 3)
    with pytest.raises(http.FetchError):
        http.get("https://example.test/y", session=session, sleep=lambda s: None, max_tries=3)


def test_http_spaces_calls_to_data_gov(monkeypatch):
    waits = []
    http._last_call.clear()
    session = FakeSession([FakeResponse(200), FakeResponse(200)])
    for _ in range(2):
        http.get("https://api.data.gov.my/data-catalogue/", session=session, sleep=waits.append)
    assert len(waits) == 1 and 14.0 < waits[0] <= 15.0


def test_drill_rename_hook_is_off_by_default_and_caught_when_on(monkeypatch, tmp_path):
    from open_data_elt.extract import _rows_checked, drill_renames

    row = {
        "date": "2026-11-19",
        "series_type": "level",
        "ron95": 3.72,
        "ron97": 4.0,
        "diesel": 4.72,
    }
    monkeypatch.delenv("ELT_DRILL_RENAME", raising=False)
    assert drill_renames(FUEL) == {}
    assert _rows_checked([row], FUEL, "api")[0]["ron97"] == 4.0

    monkeypatch.setenv("ELT_DRILL_RENAME", "fuelprice:ron97=ron97_price,cpi_headline:index=idx")
    assert drill_renames(FUEL) == {"ron97": "ron97_price"}
    with pytest.raises(SchemaDriftError):
        _rows_checked([row], FUEL, "api")

    monkeypatch.setenv("ELT_DRILL_SKIP_GUARD", "1")
    loaded = _rows_checked([row], FUEL, "api")[0]
    assert "ron97" not in loaded and loaded["ron97_price"] == 4.0
