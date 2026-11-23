from pathlib import Path

import duckdb
import pytest

from open_data_elt.probe import profile_parquet
from open_data_elt.sources import CATALOGUE_SOURCES, DATA_GOV_API, CatalogueSource


def test_registry_is_consistent():
    assert DATA_GOV_API.endswith("/"), "API returns 301 + empty body without the trailing slash"
    for key, src in CATALOGUE_SOURCES.items():
        assert key == src.id
        assert src.parquet_url.endswith(".parquet")
        assert src.primary_key
        if src.date_column:
            assert src.date_column in src.primary_key


def _write_parquet(tmp_path: Path, sql: str) -> Path:
    path = tmp_path / "t.parquet"
    duckdb.sql(f"copy ({sql}) to '{path.as_posix()}' (format parquet)")
    return path


FUEL = CatalogueSource("fuelprice", "x.parquet", "WEEKLY", ("date", "series_type"))


def test_profile_detects_unique_key(tmp_path):
    path = _write_parquet(
        tmp_path,
        "select * from (values (date '2026-11-12', 'level', 3.87), "
        "(date '2026-11-12', 'change_weekly', -0.4), (date '2026-11-19', 'level', 3.72)) "
        "t(date, series_type, ron95)",
    )
    r = profile_parquet(path, FUEL)
    assert (r.rows, r.min_date, r.max_date, r.pk_unique) == (3, "2026-11-12", "2026-11-19", True)


def test_profile_detects_duplicate_key(tmp_path):
    path = _write_parquet(
        tmp_path,
        "select * from (values (date '2026-11-12', 'level', 3.87), "
        "(date '2026-11-12', 'level', 3.90)) t(date, series_type, ron95)",
    )
    assert profile_parquet(path, FUEL).pk_unique is False


@pytest.mark.live
def test_live_probe():
    from open_data_elt.probe import run

    assert all(r.pk_unique for r in run())
