FROM python:3.13.5-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /Score_predictor

# tzdata: correct timezone names for APScheduler / zoneinfo (compose sets TZ).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY DataManager/ ./DataManager/
COPY ludobot/ ./ludobot/
COPY Utils/ ./Utils/
COPY src/ ./src/

# `ludobot/bot.py` imports `ThresholdRFClassifier` from this folder at startup.
COPY ["ML Core/", "./ML Core/"]

# Flask / scripts; keeps layout consistent with local repo.
COPY ["API core/", "./API core/"]

# Joblib artifacts + CSV used by `background_score_predictor` / API (paths from `.env` / defaults).
# Build context must contain these dirs (can be empty if you mount models at runtime instead).
COPY ["Trained models/", "./Trained models/"]
COPY Datasets/ ./Datasets/

CMD ["python", "ludobot/bot.py"]
