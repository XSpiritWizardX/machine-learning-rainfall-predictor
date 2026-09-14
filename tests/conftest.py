from datetime import date

import pytest
import db
from entities import ForecastDay, HistoricalDay
from entities.geocoded_zip import GeocodedZip


# Shared test data
BEVERLY_HILLS_JSON = {
    "post code": "90210",
    "places": [{
        "place name": "Beverly Hills",
        "longitude": "-118.4065",
        "latitude": "34.0901",
        "state abbreviation": "CA"
    }]
}

BEVERLY_HILLS_LOCATION = GeocodedZip(
    zip="90210",
    latitude=34.0901,
    longitude=-118.4065,
    city="Beverly Hills",
    state_abbr="CA"
)

HISTORICAL_DAY_FOR_UNIT_TESTS = HistoricalDay(
    date=date(2024, 1, 2),
    temp_max=99.9,
    temp_min=1.1,
    precipitation=5.5,
)

FORECAST_DAY_FOR_UNIT_TESTS = ForecastDay(
    date=date(2024, 1, 2),
    temp_max=20.1,
    temp_min=9.0,
    precipitation_sum=2.3,
)


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Create a temporary database for each test."""
    db_file = tmp_path / "test_cache.db"
    monkeypatch.setattr("db.CACHE_DB_PATH", str(db_file))

    db.init_db()
    yield
    # tmp_path is automatically cleaned up
