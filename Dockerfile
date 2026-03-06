FROM python:3.13.5-slim

WORKDIR /Score_predictor

RUN apt-get update && apt-get install -y build-essential libssl-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY DataManager .

COPY ludobot .

COPY Utils .

CMD ["python", "ludobot/bot.py"]