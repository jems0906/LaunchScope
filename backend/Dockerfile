FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/vendor \
    LAUNCHSCOPE_SCENARIO_CONFIG=/app/configs/scenarios/game_discovery.json

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/vendor ./vendor
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY configs ./configs

EXPOSE 8000
CMD ["sh", "-c", "until python -c 'import socket; socket.create_connection((\"db\", 5432), timeout=2).close()'; do sleep 2; done; alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]