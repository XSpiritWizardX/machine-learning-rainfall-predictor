from datetime import date, timedelta
from hamcrest import assert_that, is_, has_length, empty, not_none
from db import (save_location, get_cached_location, save_historical_data, get_historical_data,
                _expected_day_count, get_missing_historical_ranges, _get_weather_rows, save_forecasts, get_forecasts)
from entities import GeocodedZip, HistoricalDay, ForecastDay
import pytest


class GetCachedLocationTests:

    @staticmethod
    def test_returns_none_when_not_found(clean_db):
        result = get_cached_location("90210 ")
        assert result is None

    @staticmethod
    def test_returns_location_when_found(clean_db):
        # Arrange – use the real save function
        original = GeocodedZip(
            zip="90210",
            latitude=34.0901,
            longitude=-118.4065,
            city="Beverly Hills",
            state_abbr="CA"
        )
        save_location(original)

        # Act
        result = get_cached_location("90210")

        # Assert
        assert_that(result, is_(original))


SAMPLE_DAYS = [
    HistoricalDay(
        date=date(2024, 1, 1),
        temp_max=18.5,
        temp_min=8.2,
        precipitation=0.0,
    ),
    HistoricalDay(
        date=date(2024, 1, 2),
        temp_max=20.1,
        temp_min=9.0,
        precipitation=2.3,
    ),
    HistoricalDay(
        date=date(2024, 1, 3),
        temp_max=17.0,
        temp_min=7.5,
        precipitation=1.1,
    ),
]

class GetHistoricalDataTests:

    @staticmethod
    def test_returns_empty_list_when_not_found(clean_db):
        result = get_historical_data("90210")
        assert_that(result, has_length(0))

    @staticmethod
    def test_returns_saved_days(clean_db):
        save_historical_data("90210", SAMPLE_DAYS)

        result = get_historical_data("90210")

        assert_that(result, is_(SAMPLE_DAYS))

    @staticmethod
    def test_filters_by_date_range(clean_db):
        save_historical_data("90210", SAMPLE_DAYS)

        result = get_historical_data(
            "90210",
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
        )

        assert_that(result, has_length(1))
        assert_that(result[0], is_(SAMPLE_DAYS[1]))

    @staticmethod
    def test_does_not_return_other_zip_codes(clean_db):
        save_historical_data("90210", SAMPLE_DAYS)

        result = get_historical_data("20500")

        assert_that(result, is_(empty()))


class SaveHistoricalDataTests:

    @staticmethod
    def test_overwrites_existing_day(clean_db):
        save_historical_data("90210", SAMPLE_DAYS)

        updated_day = HistoricalDay(
            date=date(2024, 1, 2),
            temp_max=99.9,
            temp_min=1.1,
            precipitation=5.5,
        )
        save_historical_data("90210", [updated_day])

        result = get_historical_data("90210", start_date=date(2024, 1, 2), end_date=date(2024, 1, 2))

        assert_that(result, has_length(1))
        assert_that(result[0], is_(updated_day))


class ExpectedDateCountTests:
    @staticmethod
    def test_expected_date_count():
        daysAgo = 5
        delta = timedelta(days = daysAgo)
        fiveDaysAgo = date.today() - delta
        assert_that(_expected_day_count(fiveDaysAgo, date.today()), is_(daysAgo + 1))


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


JAN_1 = date(2024, 1, 1)
JAN_2 = date(2024, 1, 2)
JAN_3 = date(2024, 1, 3)
JAN_5 = date(2024, 1, 5)
JAN_8 = date(2024, 1, 8)
JAN_10 = date(2024, 1, 10)


class GetMissingHistoricalRangesTests:
    @staticmethod
    def test_no_cached_data(clean_db):
        daysAgo = 5
        delta = timedelta(days = daysAgo)
        fiveDaysAgo = date.today() - delta
        expectedResult = [(fiveDaysAgo, date.today())]
        assert_that(get_missing_historical_ranges("90210", fiveDaysAgo, date.today()),
                    is_(expectedResult))

    @pytest.mark.parametrize(
        "start_date, end_date, cached_start, cached_end, expected",
        [
            # no cached data
            (JAN_1, JAN_10, None, None, [(JAN_1, JAN_10)]),

            # full range is present
            (JAN_1, JAN_10, JAN_1, JAN_10, []),

            # missing the beginning
            (JAN_1, JAN_10, JAN_3, JAN_10, [(JAN_1, date(2024, 1, 2))]),

            # missing the end
            (JAN_1, JAN_10, JAN_1, JAN_8, [(date(2024, 1, 9), JAN_10)]),

            # missing both beginning and end
            (JAN_1, JAN_10, JAN_3, JAN_8, [
                (JAN_1, date(2024, 1, 2)),
                (date(2024, 1, 9), JAN_10),
            ]),

            # single day present
            (JAN_5, JAN_5, JAN_5, JAN_5, []),

            # single day missing
            (JAN_5, JAN_5, None, None, [(JAN_5, JAN_5)]),
        ],
        ids=[
            "no_cached_data",
            "full_range_present",
            "missing_beginning",
            "missing_end",
            "missing_both_ends",
            "single_day_present",
            "single_day_missing",
        ],
    )
    def test_missing_ranges(
            self,
            clean_db,
            start_date,
            end_date,
            cached_start,
            cached_end,
            expected,
    ):
        if cached_start is not None and cached_end is not None:
            save_historical_data("90210", _days(cached_start, cached_end))

        result = get_missing_historical_ranges("90210", start_date, end_date)
        assert_that(result, is_(expected))


class GetWeatherRowsTests:

    @staticmethod
    def test_returns_empty_when_not_found(clean_db):
        rows = _get_weather_rows(
            "historical",
            "date, temp_max, temp_min, precipitation",
            "90210",
        )
        assert_that(rows, has_length(0))

    @staticmethod
    def test_returns_all_rows_for_zip(clean_db):
        save_historical_data("90210", _days(JAN_1, JAN_3))

        rows = _get_weather_rows(
            "historical",
            "date, temp_max, temp_min, precipitation",
            "90210",
        )

        assert_that(rows, has_length(3))
        assert_that(rows[0]["date"], is_("2024-01-01"))
        assert_that(rows[-1]["date"], is_("2024-01-03"))

    @staticmethod
    def test_filters_by_date_range(clean_db):
        save_historical_data("90210", _days(JAN_1, JAN_3))

        rows = _get_weather_rows(
            "historical",
            "date, temp_max, temp_min, precipitation",
            "90210",
            start_date=JAN_2,
            end_date=JAN_2,
        )

        assert_that(rows, has_length(1))
        assert_that(rows[0]["date"], is_("2024-01-02"))

    @staticmethod
    def test_does_not_return_other_zip(clean_db):
        save_historical_data("90210", _days(JAN_1, JAN_3))

        rows = _get_weather_rows(
            "historical",
            "date, temp_max, temp_min, precipitation",
            "20500",
        )

        assert_that(rows, has_length(0))


def _forecast_days(start: date, end: date) -> list[ForecastDay]:
    days = []
    current = start
    while current <= end:
        days.append(
            ForecastDay(
                date=current,
                temp_max=21.0,
                temp_min=11.0,
                precipitation_sum=0.4,
            )
        )
        current += timedelta(days=1)
    return days


class GetForecastsTests:

    @staticmethod
    def test_returns_empty_list_when_not_found(clean_db):
        result = get_forecasts("90210")
        assert_that(len(result), is_(0))

    @staticmethod
    def test_returns_saved_days(clean_db):
        original = _forecast_days(JAN_1, JAN_3)
        save_forecasts("90210", original)

        result = get_forecasts("90210")

        assert_that(result, has_length(3))
        assert_that(result[0].date, is_(JAN_1))
        assert_that(result[-1].date, is_(JAN_3))
        assert_that(result[0].temp_max, is_(21.0))
        assert_that(result[0].precipitation_sum, is_(0.4))
        assert_that(result[0].predicted_precipitation, is_(None))
        assert_that(result[0].fetched_at, is_(not_none()))

    @staticmethod
    def test_filters_by_date_range(clean_db):
        save_forecasts("90210", _forecast_days(JAN_1, JAN_3))

        result = get_forecasts("90210", start_date=JAN_2, end_date=JAN_2)

        assert_that(result, has_length(1))
        assert_that(result[0].date, is_(JAN_2))

    @staticmethod
    def test_does_not_return_other_zip(clean_db):
        save_forecasts("90210", _forecast_days(JAN_1, JAN_3))

        result = get_forecasts("20500")
        assert_that(len(result), is_(0))


class SaveForecastsTests:

    @staticmethod
    def test_overwrites_existing_day(clean_db):
        save_forecasts("90210", _forecast_days(JAN_1, JAN_3))

        updated = ForecastDay(
            date=JAN_2,
            temp_max=99.9,
            temp_min=1.1,
            precipitation_sum=5.5,
        )
        save_forecasts("90210", [updated])

        result = get_forecasts("90210", start_date=JAN_2, end_date=JAN_2)

        assert_that(result, has_length(1))
        assert_that(result[0].temp_max, is_(99.9))
        assert_that(result[0].precipitation_sum, is_(5.5))
