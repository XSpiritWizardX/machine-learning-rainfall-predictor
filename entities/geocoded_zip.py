from dataclasses import dataclass


@dataclass(frozen = True)
class GeocodedZip:
    zip: str
    latitude: float
    longitude: float
    city: str
    state_abbr: str

    @property
    def state(self) -> str:
        """Alias for state_abbr"""
        return self.state_abbr
