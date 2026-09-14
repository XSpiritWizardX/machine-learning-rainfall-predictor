from dataclasses import replace
from typing import List

from sklearn.linear_model import LinearRegression

from entities import HistoricalDay, ForecastDay


def predict_forecast(
        historical: List[HistoricalDay],
        forecast: List[ForecastDay],
) -> List[ForecastDay]:
    """
    Train a linear model on historical temps → precipitation,
    then predict precipitation for each forecast day.
    """
    if not historical or not forecast:
        return forecast

    X = [[day.temp_max, day.temp_min] for day in historical]
    y = [day.precipitation for day in historical]

    model = LinearRegression()
    model.fit(X, y)

    predicted_days: List[ForecastDay] = []
    for day in forecast:
        predicted = model.predict([[day.temp_max, day.temp_min]])[0]
        predicted = max(0.0, float(predicted))  # rain can't be negative
        predicted_days.append(
            replace(day, predicted_precipitation=predicted)
        )

    return predicted_days
