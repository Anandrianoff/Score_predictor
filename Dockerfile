FROM python:3.13-slim

# ENV DEBIAN_FRONTEND=noninteractive \
#     PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1 \
#     PIP_DEFAULT_TIMEOUT=120 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1

# If PyPI is slow or blocked, build with e.g.:
#   docker build --build-arg PIP_INDEX_URL=https://pypi.org/simple .
# Or a mirror: https://mirrors.aliyun.com/pypi/simple/ (also add that host to --trusted-host).
# ARG PIP_INDEX_URL=https://pypi.org/simple
# ENV PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /Score_predictor

RUN apt-get update && apt-get install -y build-essential libssl-dev && rm -rf /var/lib/apt/lists/*
# RUN apt-get -o Acquire::Retries=5 update \
#     && apt-get install -y --no-install-recommends \
#         ca-certificates \
#         tzdata \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY DataManager/ ./DataManager/
COPY ludobot/ ./ludobot/
COPY Utils/ ./Utils/
COPY src/ ./src/

COPY ["ML Core/", "./ML Core/"]
COPY ["API core/", "./API core/"]

# Joblib artifacts + CSV used by `background_score_predictor` / API (paths from `.env` / defaults).
# Build context must contain these dirs (can be empty if you mount models at runtime instead).

CMD ["python", "ludobot/bot.py"]
