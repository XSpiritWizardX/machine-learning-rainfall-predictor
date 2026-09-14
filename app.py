import time
import random

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory

import db
import os

from geo import geocode_zip
from predict import predict_forecast
from weather import get_or_fetch_historical_weather, get_or_fetch_forecast

DEBUG = True

load_dotenv()
app = Flask(__name__)
db.init_db()


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/style.css")
def stylesheet():
    return send_from_directory(".", "style.css")


@app.route("/scripts/<path:filename>")
def scripts(filename):
    return send_from_directory("scripts", filename)


@app.route("/api/predict/<zip_code>")
def api_predict(zip_code: str):
    started = time.perf_counter()

    location = geocode_zip(zip_code)
    if location is None:
        return jsonify({"error": "Invalid or unknown ZIP code"}), 400

    try:
        historical = get_or_fetch_historical_weather(location)
        forecast = get_or_fetch_forecast(location)
        predicted = predict_forecast(historical, forecast)
        user_likes_cheese = random.randint(1, 100) % 2 == 1
        user_thinking_about_hats = random.randint(1, 100) % 2 == 1
    except Exception as e:
        return jsonify({"error": f"Failed to generate prediction: {str(e)}"}), 500

    elapsed_ms = round((time.perf_counter() - started) * 1000)

    return jsonify({
        "elapsed_ms": elapsed_ms,
        "location": {
            "zip": location.zip,
            "city": location.city,
            "state": location.state_abbr,
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        "historical_days": len(historical),
        "forecast": [
            {
                "date": d.date.isoformat(),
                "temp_max": d.temp_max,
                "temp_min": d.temp_min,
                "forecast_precipitation": d.precipitation_sum,
                "predicted_precipitation": d.predicted_precipitation,
            }
            for d in predicted
        ],
        "diagnostics": {
            "user_likes_cheese": user_likes_cheese,
            "user_thinking_about_hats": user_thinking_about_hats
        }
    })

def print_db_variables_debug():
    print("\n")
    print(f"CACHE_DB_NAME from env: {os.getenv("CACHE_DB_NAME")}")
    print(f"CACHE_DB_DIR from env: {os.getenv("CACHE_DB_DIR")}")

    print("\n")
    print(f"db.CACHE_DB_DIR: {db.CACHE_DB_DIR}")
    print(f"db.CACHE_DB_NAME: {db.CACHE_DB_NAME}")
    print(f"db.CACHE_DB_PATH: {db.CACHE_DB_PATH}")


if __name__ == "__main__":

    if DEBUG:
        print_db_variables_debug()

    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5500"))
    app.run(host=host, port=port, debug=DEBUG, use_reloader=False)
