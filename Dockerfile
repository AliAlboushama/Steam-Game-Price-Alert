FROM python:3.12-slim

# Unbuffered output so `docker logs` shows each check straight away; data lives in the /data volume
ENV PYTHONUNBUFFERED=1 \
    STEAM_ALERT_DATA_DIR=/data

WORKDIR /app
COPY Steam-Game-Price-Alert/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Steam-Game-Price-Alert/ .
RUN useradd --system --uid 1000 bot && mkdir /data && chown bot /data
USER bot
VOLUME /data

CMD ["python", "main.py", "--daemon"]
