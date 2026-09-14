# Rainfall Predictor

Flask app that takes a US ZIP code, trains a small linear model on local history, and compares that model’s rain guess to Open-Meteo’s 14-day forecast.

## What it does

1. Validates a 5-digit US ZIP and geocodes it with Zippopotam.us (cached forever).
2. Loads or fetches about two years of daily history from Open-Meteo (`temp_max`, `temp_min`, `precipitation`).
3. Loads or fetches a 14-day forecast (cached 12 hours).
4. Fits `LinearRegression` on that ZIP’s history: temps → precipitation. Negative predictions are clipped to 0.
5. Returns JSON with location, timing, Open-Meteo rain, and model rain. The page fills a table from that payload.

The model is trained per request from cached history. It is not the old Centreville pickle/CSV pipeline.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env_example .env   # optional; cache path defaults are fine
```

Then open `http://127.0.0.1:5500/` if you set that host/port in `app.py`. Prefer `127.0.0.1` over `localhost`.

## API

`GET /api/predict/<zip_code>`

Example: `GET /api/predict/90210`

Success:

```json
{
  "elapsed_ms": 42,
  "location": {
    "zip": "90210",
    "city": "Beverly Hills",
    "state": "CA",
    "latitude": 34.09,
    "longitude": -118.41
  },
  "historical_days": 731,
  "forecast": [
    {
      "date": "2026-09-02",
      "temp_max": 28.1,
      "temp_min": 16.4,
      "forecast_precipitation": 0.0,
      "predicted_precipitation": 0.12
    }
  ],
  "diagnostics": {
    "user_likes_cheese": true
  }
}
```

Invalid or unknown ZIP:

```json
{ "error": "Invalid or unknown ZIP code" }
```

Status `400`.

`diagnostics.user_likes_cheese` is random. It is not a model feature.

## Frontend

Flask serves `index.html`, `style.css`, and `scripts/script.js`. Enter a ZIP. The script calls `/api/predict/<zip>`, fills the table, and shows city, state, historical day count, and `elapsed_ms`. Submit is disabled while a request is in flight.

## Project layout

| Path | Role |
| --- | --- |
| `app.py` | Flask app and `/api/predict/<zip>` |
| `geo.py` | ZIP check and geocoding |
| `weather.py` | Open-Meteo fetch + cache helpers |
| `predict.py` | Per-ZIP linear regression |
| `db.py` | SQLite cache |
| `entities/` | Frozen dataclasses |
| `index.html`, `style.css`, `scripts/script.js` | UI |
| `tests/` | Hamcrest tests, `clean_db` fixture |

## Tests

```bash
pytest
```

## Cache

- `locations` — ZIP → lat/lon/city/state, kept indefinitely
- `historical` — daily history; missing start/end ranges are fetched
- `forecasts` — 14-day forecast, refreshed after 12 hours via `fetched_at`

Do not delete the DB on every request.

## Limits

- US 5-digit ZIP only (no ZIP+4, no other countries, no raw lat/lon)
- Predicted rain is not written back to `forecasts`
- Predictions are not scored against later observations
- Not a production WSGI deploy

## Docker

```bash
docker build -t rainfall-predictor .
docker run --rm -p 5500:5500 \
  -v "$(pwd)/weather_cache.db:/app/weather_cache.db" \
  rainfall-predictor
```
