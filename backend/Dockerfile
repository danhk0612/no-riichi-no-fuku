FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

COPY app /app/app
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

CMD ["sh", "-c", "alembic upgrade head && python -m app.bootstrap && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
