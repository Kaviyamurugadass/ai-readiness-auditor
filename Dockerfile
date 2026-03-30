FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir openenv-core fastapi uvicorn pydantic websockets openai

# Copy project files
COPY models.py client.py baseline.py __init__.py openenv.yaml ./
COPY server/ server/
COPY static/ static/
COPY data/ data/

EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
