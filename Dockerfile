FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir openenv-core fastapi uvicorn pydantic websockets openai

# Copy project files
COPY ai_readiness_auditor/ ai_readiness_auditor/
COPY server/ server/
COPY openenv.yaml .

EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
