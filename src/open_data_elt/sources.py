"""Registry of the open data sources this pipeline loads.

Checked by hand on 2026-11-23 (see SOURCES.md). The API is used for small
incremental pulls; the parquet bulk files are used for backfills, because the
data.gov.my API allows only 4 requests per minute.
"""

from dataclasses import dataclass

DATA_GOV_API = "https://api.data.gov.my/data-catalogue/"  # trailing slash matters (else 301)
BNM_API = "https://api.bnm.gov.my/public/exchange-rate"
BNM_ACCEPT = "application/vnd.BNM.API.v1+json"
DATA_GOV_REQUESTS_PER_MINUTE = 4


@dataclass(frozen=True)
class CatalogueSource:
    """One dataset from the data.gov.my data catalogue."""

    id: str
    parquet_url: str
    frequency: str  # as reported by the API's meta block
    primary_key: tuple[str, ...]
    date_column: str | None = "date"  # None for lookup tables
    # Columns the dbt models depend on. If one disappears (e.g. renamed upstream)
    # the load fails loudly. New extra columns are allowed and simply added.
    required_columns: tuple[str, ...] = ()
    # On incremental runs, re-pull this many days before the last loaded date so
    # late revisions are picked up. Merge on the primary key keeps it idempotent.
    lookback_days: int = 35


CATALOGUE_SOURCES: dict[str, CatalogueSource] = {
    "ridership_headline": CatalogueSource(
        id="ridership_headline",
        parquet_url="https://storage.data.gov.my/transportation/ridership_headline.parquet",
        frequency="DAILY",
        primary_key=("date",),
        required_columns=(
            "date",
            "rail_lrt_ampang",
            "rail_lrt_kj",
            "rail_mrt_kajang",
            "rail_mrt_pjy",
            "rail_monorail",
            "bus_rkl",
        ),
    ),
    "fuelprice": CatalogueSource(
        id="fuelprice",
        parquet_url="https://storage.data.gov.my/commodities/fuelprice.parquet",
        frequency="WEEKLY",
        primary_key=("date", "series_type"),
        required_columns=("date", "series_type", "ron95", "ron97", "diesel"),
    ),
    "cpi_headline": CatalogueSource(
        id="cpi_headline",
        parquet_url="https://storage.dosm.gov.my/cpi/cpi_2d.parquet",
        frequency="MONTHLY",
        primary_key=("date", "division"),
        required_columns=("date", "division", "index"),
        lookback_days=100,
    ),
    "mcoicop": CatalogueSource(
        id="mcoicop",
        parquet_url="https://storage.dosm.gov.my/dictionaries/mcoicop.parquet",
        frequency="AD_HOC",
        primary_key=("division", "group", "class", "subclass"),
        date_column=None,
        required_columns=("division", "group", "class", "subclass", "desc_en"),
    ),
}

# BNM: USD/MYR at the 12:00 session, one call per month.
BNM_CURRENCIES = ("USD",)
BNM_SESSION = "1200"
BNM_START = (2017, 1)  # fuel prices start 2017-03, so FX history from Jan 2017 covers it
