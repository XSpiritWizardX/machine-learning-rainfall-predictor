# geo.py


import requests
from typing import Optional

from entities.geocoded_zip import GeocodedZip
import db

def is_valid_us_zip(zip_code: str) -> bool:
    """Return True if the input is a valid 5-digit US ZIP code."""
    return isinstance(zip_code, str) and zip_code.isdigit() and len(zip_code) == 5


def geocode_zip(zip_code: str) -> Optional[GeocodedZip]:
    """
    Look up a US ZIP code and return location data.

    Returns a GeocodedZip object which contains:
        - latitude
        - longitude
        - city
        - state
        - zip

    Returns None if the ZIP is invalid or the lookup fails.

    Uses database cache when possible.
    """
    if not is_valid_us_zip(zip_code):
        return None

    # Try the cache first
    cached = db.get_cached_location(zip_code)
    if cached is not None:
        return cached

    url = f"https://api.zippopotam.us/us/{zip_code}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()          # raises an error for 4xx/5xx
        data = response.json()

        # Zippopotam.us returns a list of places; we take the first one
        place = data["places"][0]

        location =  GeocodedZip (
            zip = data["post code"],
            latitude = float(place["latitude"]),
            longitude = float(place["longitude"]),
            city = place["place name"],
            state_abbr = place["state abbreviation"],
        )

        db.save_location(location)
        return location

    except (requests.RequestException, KeyError, IndexError, ValueError):
        # Network error, unexpected JSON structure, etc.
        return None
