from datetime import date

from hamcrest import assert_that, is_, close_to, none

from entities import HistoricalDay, ForecastDay
from predict import predict_forecast
from tests.conftest import FORECAST_DAY_FOR_UNIT_TESTS, HISTORICAL_DAY_FOR_UNIT_TESTS


def assert_forecast_day_equal(actual, expected, tolerance=0.0001):
    assert_that(actual.date, is_(expected.date))
    assert_that(actual.temp_max, is_(expected.temp_max))
    assert_that(actual.temp_min, is_(expected.temp_min))
    assert_that(actual.precipitation_sum, is_(expected.precipitation_sum))
    assert_that(actual.fetched_at, is_(expected.fetched_at))

    if expected.predicted_precipitation is None:
        assert_that(actual.predicted_precipitation, is_(none()))
    else:
        assert_that(
            actual.predicted_precipitation,
            is_(close_to(expected.predicted_precipitation, tolerance)),
        )


class PredictTests:
    @staticmethod
    def test_empty_historical_list():
        result = predict_forecast([], [FORECAST_DAY_FOR_UNIT_TESTS])
        assert_that(result, is_([FORECAST_DAY_FOR_UNIT_TESTS]))


    @staticmethod
    def test_empty_forecast_list():
        result = predict_forecast([HISTORICAL_DAY_FOR_UNIT_TESTS], [])
        assert_that(result, is_([]))

    @staticmethod
    def test_predicts_from_temperature_pattern():
        historical = [
            HistoricalDay(date(2024, 1, 1), temp_max=10, temp_min=0, precipitation=1.0),
            HistoricalDay(date(2024, 1, 2), temp_max=20, temp_min=10, precipitation=2.0),
            HistoricalDay(date(2024, 1, 3), temp_max=30, temp_min=20, precipitation=3.0),
        ]

        forecast = [
            ForecastDay(
                date=date(2024, 1, 4),
                temp_max=40,
                temp_min=30,
                precipitation_sum=0.0,
            )
        ]

        result = predict_forecast(historical, forecast)

        expected = ForecastDay(
            date=date(2024, 1, 4),
            temp_max=40,
            temp_min=30,
            precipitation_sum=0.0,
            predicted_precipitation=4.0,
        )

        assert_forecast_day_equal(result[0], expected)
