FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /Score_predictor

# Only runtime OS packages. (No build-essential: deps use manylinux wheels.)
# Retries help flaky Docker network / mirror timeouts (apt exit 100).
RUN apt-get -o Acquire::Retries=5 update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY DataManager/ ./DataManager/
COPY ludobot/ ./ludobot/
COPY Utils/ ./Utils/
COPY src/ ./src/

# `ludobot/bot.py` imports `ThresholdRFClassifier` from this folder at startup.
COPY ["ML Core/", "./ML Core/"]

COPY ["API core/", "./API core/"]

# Joblib artifacts + CSV used by `background_score_predictor` / API (paths from `.env` / defaults).
# Build context must contain these dirs (can be empty if you mount models at runtime instead).

CMD ["python", "ludobot/bot.py"]
