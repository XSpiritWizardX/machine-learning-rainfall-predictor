from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class HistoricalDay:
    date: date
    temp_max: float
    temp_min: float
    precipitation: float
