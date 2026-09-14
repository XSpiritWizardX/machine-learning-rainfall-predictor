from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import requests
from dateutil.relativedelta import relativedelta
from hamcrest import assert_that, is_, has_length, none, raises, calling

from db import save_historical_data, get_historical_data
from weather import fetch_historical_weather, get_or_fetch_historical_weather, fetch_forecast
from entities import HistoricalDay, GeocodedZip, ForecastDay
from tests.conftest import BEVERLY_HILLS_LOCATION


# Minimal fake Open-Meteo response
FAKE_OPEN_METEO_RESPONSE = {
    "daily": {
        "time": ["2024-01-01", "2024-01-02"],
        "temperature_2m_max": [18.5, 20.1],
        "temperature_2m_min": [8.2, 9.0],
        "precipitation_sum": [0.0, 2.3],
    }
}


class FetchHistoricalWeatherTests:

    @patch("weather.requests.get")
    def test_fetch_historical_weather_happy_path(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = FAKE_OPEN_METEO_RESPONSE
        mock_get.return_value = mock_response

        # Act
        result = fetch_historical_weather(BEVERLY_HILLS_LOCATION)

        # Assert
        assert_that(result, has_length(2))

        expected = [
            HistoricalDay(
                date=date(2024, 1, 1),
                temp_max=18.5,
                temp_min=8.2,
                precipitation=0.0
            ),
            HistoricalDay(
                date=date(2024, 1, 2),
                temp_max=20.1,
                temp_min=9.0,
                precipitation=2.3
            ),
        ]
        assert_that(result, is_(expected))

        # verify the call
        mock_get.assert_called_once()

        args, kwargs = mock_get.call_args
        params = kwargs["params"]

        today = date.today()
        expected_start = today - relativedelta(years=2)

        assert_that(params["start_date"], is_(expected_start.isoformat()))
        assert_that(params["end_date"], is_(today.isoformat()))


LOCATION = GeocodedZip(
    zip="90210",
    latitude=34.0901,
    longitude=-118.4065,
    city="Beverly Hills",
    state_abbr="CA",
)

START = date(2024, 1, 1)
END = date(2024, 1, 10)


def _days(start: date, end: date) -> list[HistoricalDay]:
    days = []
    current = start
    while current <= end:
        days.append(
            HistoricalDay(
                date=current,
                temp_max=20.0,
                temp_min=10.0,
                precipitation=0.0,
            )
        )
        current += timedelta(days=1)
    return days


class GetOrFetchHistoricalWeatherTests:

    @patch("weather.fetch_historical_weather")
    def test_uses_cache_when_complete(self, mock_fetch, clean_db):
        save_historical_data("90210", _days(START, END))

        result = get_or_fetch_historical_weather(LOCATION, START, END)

        mock_fetch.assert_not_called()
        assert_that(result, is_(_days(START, END)))

    @patch("weather.fetch_historical_weather")
    def test_fetches_full_range_when_cache_empty(self, mock_fetch, clean_db):
        mock_fetch.return_value = _days(START, END)

        result = get_or_fetch_historical_weather(LOCATION, START, END)

        mock_fetch.assert_called_once_with(
            LOCATION,
            start_date=START,
            end_date=END,
        )
        assert_that(result, is_(_days(START, END)))
        assert_that(get_historical_data("90210", START, END), has_length(10))

    @patch("weather.fetch_historical_weather")
    def test_fetches_only_missing_end(self, mock_fetch, clean_db):
        save_historical_data("90210", _days(START, date(2024, 1, 8)))
        missing_start = date(2024, 1, 9)
        mock_fetch.return_value = _days(missing_start, END)

        result = get_or_fetch_historical_weather(LOCATION, START, END)

        mock_fetch.assert_called_once_with(
            LOCATION,
            start_date=missing_start,
            end_date=END,
        )
        assert_that(result, has_length(10))
        assert_that(result[0].date, is_(START))
        assert_that(result[-1].date, is_(END))


FAKE_FORECAST_RESPONSE = {
    "daily": {
        "time": ["2024-01-01", "2024-01-02"],
        "temperature_2m_max": [18.5, 20.1],
        "temperature_2m_min": [8.2, 9.0],
        "precipitation_sum": [0.0, 2.3],
    }
}


class FetchForecastTests:

    @patch("weather.requests.get")
    def test_fetch_forecast_happy_path(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = FAKE_FORECAST_RESPONSE
        mock_get.return_value = mock_response

        result = fetch_forecast(LOCATION)

        expected = [
            ForecastDay(
                date=date(2024, 1, 1),
                temp_max=18.5,
                temp_min=8.2,
                precipitation_sum=0.0,
            ),
            ForecastDay(
                date=date(2024, 1, 2),
                temp_max=20.1,
                temp_min=9.0,
                precipitation_sum=2.3,
            ),
        ]

        assert_that(result, is_(expected))
        assert_that(result[0].predicted_precipitation, is_(none()))
        assert_that(result[0].fetched_at, is_(none()))

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert_that(kwargs["params"]["forecast_days"], is_(14))
        assert_that(kwargs["params"]["latitude"], is_(LOCATION.latitude))
        assert_that(kwargs["params"]["longitude"], is_(LOCATION.longitude))

    @patch("weather.requests.get")
    def test_fetch_forecast_respects_days_parameter(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "daily": {
                "time": [],
                "temperature_2m_max": [],
                "temperature_2m_min": [],
                "precipitation_sum": [],
            }
        }
        mock_get.return_value = mock_response

        fetch_forecast(LOCATION, days=7)

        args, kwargs = mock_get.call_args
        assert_that(kwargs["params"]["forecast_days"], is_(7))

    @patch("weather.requests.get")
    def test_fetch_forecast_returns_empty_list_when_no_days(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "daily": {
                "time": [],
                "temperature_2m_max": [],
                "temperature_2m_min": [],
                "precipitation_sum": [],
            }
        }
        mock_get.return_value = mock_response

        result = fetch_forecast(LOCATION)
        assert_that(result, is_([]))

    @patch("weather.requests.get")
    def test_fetch_forecast_raises_on_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("boom")
        mock_get.return_value = mock_response
        assert_that(calling(fetch_forecast).with_args(LOCATION), raises(requests.HTTPError))
