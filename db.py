import sqlite3
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import shutil
from typing import Optional, List

from entities import GeocodedZip, HistoricalDay, ForecastDay
from datetime import date

# --- Configuration (runs when the module is imported) ---
CACHE_DB_NAME = os.getenv("CACHE_DB_NAME", "weather_cache.db")
CACHE_DB_DIR  = os.getenv("CACHE_DB_DIR", "")

if CACHE_DB_DIR:
    CACHE_DB_PATH = str(Path(CACHE_DB_DIR) / CACHE_DB_NAME)
else:
    CACHE_DB_PATH = CACHE_DB_NAME


def get_connection():
    """Return a connection to the SQLite database.
    Creates the database file if it does not exist yet.
    """
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name (row["zip"])
    return conn


def backup_db():
    """Create a timestamped backup of the database."""
    if not os.path.exists(CACHE_DB_PATH):
        print("No database file found to back up.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"weather_cache_backup_{timestamp}.db"
    shutil.copy2(CACHE_DB_PATH, backup_name)
    print(f"Backup created: {backup_name}")


def init_db():
    """Create the tables if they do not already exist.
    Safe to call multiple times — it will never destroy existing data.
    """
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS locations (
                zip TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                city TEXT,
                state TEXT,
                last_updated TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS historical (
                zip TEXT NOT NULL,
                date TEXT NOT NULL,
                temp_max REAL,
                temp_min REAL,
                precipitation REAL,
                PRIMARY KEY (zip, date),
                FOREIGN KEY (zip) REFERENCES locations(zip)
            );

            CREATE TABLE IF NOT EXISTS forecasts (
                zip TEXT NOT NULL,
                date TEXT NOT NULL,
                temp_max REAL,
                temp_min REAL,
                precipitation_sum REAL,
                predicted_precipitation REAL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (zip, date),
                FOREIGN KEY (zip) REFERENCES locations(zip)
            );
        """)
    print("Database ready.")


def get_db_status() -> str:
    """Return a human-readable status of the database."""
    try:
        with get_connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()

            if not tables:
                return "Database connected, but no tables found."

            table_names = [row["name"] for row in tables]
            return f"Database connection successful. Tables: {', '.join(table_names)}"
    except Exception as e:
        return f"Database error: {e}"


def get_cached_location(zip_code: str) -> Optional[GeocodedZip]:
    """
    Look up a ZIP code in the locations table.
    Returns a GeocodedZip if found, otherwise None.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT zip, latitude, longitude, city, state
            FROM locations
            WHERE zip = ?
            """,
            (zip_code,)
        ).fetchone()

    if row is None:
        return None

    return GeocodedZip(
        zip=row["zip"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        city=row["city"],
        state_abbr=row["state"],
    )


def save_location(location: GeocodedZip) -> None:
    """
    Insert or update a GeocodedZip in the locations table.
    """
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO locations (zip, latitude, longitude, city, state, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(zip) DO UPDATE SET
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                city = excluded.city,
                state = excluded.state,
                last_updated = excluded.last_updated
            """,
            (
                location.zip,
                location.latitude,
                location.longitude,
                location.city,
                location.state_abbr,
                now,
            )
        )
        conn.commit()


def save_historical_data(zip_code: str, days: list[HistoricalDay]) -> None:
    """
    Save a list of HistoricalDay records for a ZIP code.
    Uses INSERT OR REPLACE so re-fetching the same days is safe.
    """
    with get_connection() as conn:
        for day in days:
            conn.execute(
                """
                INSERT INTO historical (zip, date, temp_max, temp_min, precipitation)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(zip, date) DO UPDATE SET
                    temp_max = excluded.temp_max,
                    temp_min = excluded.temp_min,
                    precipitation = excluded.precipitation
                """,
                (
                    zip_code,
                    day.date.isoformat(),   # convert date → string for SQLite
                    day.temp_max,
                    day.temp_min,
                    day.precipitation,
                )
            )
        conn.commit()


def _get_weather_rows(
        table: str,
        columns: str,
        zip_code: str,
        start_date: date | None = None,
        end_date: date | None = None,
):
    query = f"""
        SELECT {columns}
        FROM {table}
        WHERE zip = ?
    """
    params: list = [zip_code]

    if start_date is not None:
        query += " AND date >= ?"
        params.append(start_date.isoformat())

    if end_date is not None:
        query += " AND date <= ?"
        params.append(end_date.isoformat())

    query += " ORDER BY date"

    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def get_historical_data(
        zip_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
) -> List[HistoricalDay]:
    """
    Retrieve historical weather data for a ZIP code.

    Optionally filter by start_date and/or end_date (inclusive).
    Returns a list of HistoricalDay objects ordered by date.
    """
    query = """
        SELECT date, temp_max, temp_min, precipitation
        FROM historical
        WHERE zip = ?
    """

    rows = _get_weather_rows(
        "historical",
        "date, temp_max, temp_min, precipitation",
        zip_code,
        start_date,
        end_date,
    )

    return [
        HistoricalDay(
            date=date.fromisoformat(row["date"]),
            temp_max=row["temp_max"],
            temp_min=row["temp_min"],
            precipitation=row["precipitation"],
        )
        for row in rows
    ]


def _expected_day_count(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1


def get_missing_historical_ranges(
        zip_code: str,
        start_date: date,
        end_date: date,
) -> list[tuple[date, date]]:
    """
    Return contiguous date ranges that are missing from the cache.

    This simple version only looks for missing days at the beginning
    and/or the end of the requested window.
    """
    cached = get_historical_data(zip_code, start_date, end_date)

    if not cached:
        return [(start_date, end_date)]

    expected = _expected_day_count(start_date, end_date)
    min_date = cached[0].date
    max_date = cached[-1].date

    if (
            len(cached) == expected
            and min_date == start_date
            and max_date == end_date
    ):
        return []

    missing: list[tuple[date, date]] = []

    # Missing the oldest days
    if min_date > start_date:
        missing.append((start_date, min_date - timedelta(days=1)))

    # Missing the newest days
    if max_date < end_date:
        missing.append((max_date + timedelta(days=1), end_date))

    return missing


def save_forecasts(zip_code: str, days: list[ForecastDay]):
    """
    Save a list of ForecastDay records for a ZIP code.
    Uses INSERT OR REPLACE so re-fetching the same days is safe.
    """

    with get_connection() as conn:
        now = datetime.now(timezone.utc).isoformat()

        for day in days:
            conn.execute(
                """
                INSERT INTO forecasts (zip, date, temp_max, temp_min, precipitation_sum, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(zip, date) DO UPDATE SET
                    temp_max = excluded.temp_max,
                    temp_min = excluded.temp_min,
                    precipitation_sum = excluded.precipitation_sum,
                    fetched_at = excluded.fetched_at
                """,
                (
                    zip_code,
                    day.date.isoformat(),   # convert date → string for SQLite
                    day.temp_max,
                    day.temp_min,
                    day.precipitation_sum,
                    now
                )
            )
        conn.commit()


def get_forecasts(
        zip_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
) -> List[ForecastDay]:
    """
    Retrieve forecast rows for a ZIP code.

    Optionally filter by start_date and/or end_date (inclusive).
    Returns a list of ForecastDay objects ordered by date.
    """
    query = """
        SELECT date, temp_max, temp_min, precipitation_sum,
               predicted_precipitation, fetched_at
        FROM forecasts
        WHERE zip = ?
    """

    rows = _get_weather_rows(
        "forecasts",
        "date, temp_max, temp_min, precipitation_sum, predicted_precipitation, fetched_at",
        zip_code,
        start_date,
        end_date,
    )

    return [
        ForecastDay(
            date=date.fromisoformat(row["date"]),
            temp_max=row["temp_max"],
            temp_min=row["temp_min"],
            precipitation_sum=row["precipitation_sum"],
            predicted_precipitation=row["predicted_precipitation"],
            fetched_at=datetime.fromisoformat(row["fetched_at"])
            if row["fetched_at"] is not None
            else None,
        )
        for row in rows
    ]


if __name__ == "__main__":
    init_db()
    print(get_db_status())
    # backup_db()   # uncomment if you want to test backup
