FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev

COPY apps/api/app ./app

ENV ATTESTA_DB_PATH=/app/data/attesta.db
ENV ATTESTA_STORAGE_DIR=/app/data/evidence

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
