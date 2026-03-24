FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

WORKDIR /app

# Копируем установленные пакеты из builder-слоя
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ ./src/

ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_WORKERS=4 \
    MAX_CONTENT_BYTES=10485760 \
    LOG_LEVEL=info \
    LOG_FORMAT=json

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.main:app --host $APP_HOST --port $APP_PORT --workers $APP_WORKERS"]
