FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    mlflow==2.16.2 \
    psycopg2-binary==2.9.9 \
    google-cloud-storage==2.18.2 \
    gcsfs==2024.9.0.post1 \
    google-cloud-logging==3.11.2

# Environment variables
ENV MLFLOW_PORT=5000 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create directories
RUN mkdir -p /tmp/mlflow /app

# Set working directory
WORKDIR /app

# Expose port
EXPOSE $MLFLOW_PORT

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:$MLFLOW_PORT/health || exit 1

# Start MLflow server
CMD exec mlflow server \
    --backend-store-uri "${MLFLOW_BACKEND_STORE_URI}" \
    --default-artifact-root "${MLFLOW_DEFAULT_ARTIFACT_ROOT}" \
    --host 0.0.0.0 \
    --port "${MLFLOW_PORT}" \
    --workers 2 \
    --gunicorn-opts "--log-level debug --timeout 600"