FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends sumo sumo-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt -r backend/requirements.txt

COPY . .

ENV SUMO_HOME=/usr/share/sumo
ENV PORT=10000

EXPOSE 10000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
