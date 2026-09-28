FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY alembic.ini docker-entrypoint.sh ./
COPY app/ ./app
COPY migrations/ ./migrations

ENTRYPOINT [ "sh", "/app/docker-entrypoint.sh" ]

CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" ]