FROM python:3.12-slim AS test

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py geo.py weather.py predict.py pytest.ini ./
COPY entities ./entities
COPY tests ./tests

RUN pytest

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5500

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pytest pyhamcrest \
    && rm -rf /root/.cache/pip

COPY app.py db.py geo.py weather.py predict.py ./
COPY entities ./entities
COPY index.html style.css ./
COPY scripts ./scripts

EXPOSE 5500

CMD ["python", "app.py"]
