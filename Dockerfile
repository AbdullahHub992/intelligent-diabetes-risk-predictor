FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

# App code, dataset, trained models, and static plots (offline-safe cold start).
COPY . .

RUN mkdir -p instance data saved_models app/static/plots

ENV PORT=10000
EXPOSE 10000

CMD gunicorn run:app --bind 0.0.0.0:${PORT} --workers 1 --threads 2 --timeout 120
