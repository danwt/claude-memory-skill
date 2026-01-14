FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

RUN mkdir -p /app/data /app/models

ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
