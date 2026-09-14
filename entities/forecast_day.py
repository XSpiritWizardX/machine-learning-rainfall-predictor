from datetime import date, datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastDay:
    date: date
    temp_max: float
    temp_min: float
    precipitation_sum: float
    predicted_precipitation: float | None = None
    fetched_at: datetime | None = None
