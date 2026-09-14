# tests/test_geo.py

from unittest.mock import patch, MagicMock
from hamcrest import assert_that, is_
from geo import is_valid_us_zip, geocode_zip

from tests.conftest import BEVERLY_HILLS_LOCATION, BEVERLY_HILLS_JSON
import db

class IsValidUsZipTests:
    @staticmethod
    def test_zip_not_digits():
        assert_that(is_valid_us_zip("abcde"), is_(False))
        assert_that(is_valid_us_zip("123a5"), is_(False))

    @staticmethod
    def test_zip_has_spaces():
        assert_that(is_valid_us_zip("90 210"), is_(False))

    @staticmethod
    def test_zip_is_empty_string():
        assert_that(is_valid_us_zip(""), is_(False))

    @staticmethod
    def test_zip_too_short():
        assert_that(is_valid_us_zip("123"), is_(False))

    @staticmethod
    def test_zip_too_long():
        assert_that(is_valid_us_zip("123456"), is_(False))

    @staticmethod
    def test_zip_plus_4_not_supported():
        assert_that(is_valid_us_zip("20500+1600"), is_(False))
        assert_that(is_valid_us_zip("20500-1600"), is_(False))

    @staticmethod
    def test_zip_just_right():
        assert_that(is_valid_us_zip("12345"), is_(True))
        assert_that(is_valid_us_zip("90210"), is_(True))
        assert_that(is_valid_us_zip("00000"), is_(True))


class GecodeZipTests:
    @staticmethod
    def test_geocode_zip_invalid_zip():
        assert_that(geocode_zip("abcde"), is_(None))

    @staticmethod
    @patch("geo.requests.get")
    def test_geocode_zip_no_cache_happy_path(mock_get: MagicMock, clean_db):
        # Arrange – fake response from Zippopotam.us
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = BEVERLY_HILLS_JSON
        mock_get.return_value = mock_response

        # Act
        data = BEVERLY_HILLS_LOCATION
        assert_that(geocode_zip("90210"), is_(data))

        mock_get.assert_called_once_with(
            "https://api.zippopotam.us/us/90210",
            timeout=5
        )

    @staticmethod
    @patch("geo.requests.get")
    def test_geocode_zip_cache_hit_happy_path(mock_get: MagicMock, clean_db):
        # Arrange – put the data in the cache first
        db.save_location(BEVERLY_HILLS_LOCATION)

        # Act
        result = geocode_zip("90210")

        # Assert
        assert_that(result, is_(BEVERLY_HILLS_LOCATION))

        # Most important: we should NOT have called the external API
        mock_get.assert_not_called()
