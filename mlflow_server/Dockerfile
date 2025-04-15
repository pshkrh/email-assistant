FROM python:3.11-slim

# Install MLflow with GCS support
RUN pip install mlflow==2.16.2 psycopg2-binary gunicorn google-cloud-storage gcsfs

# The environment variables will be set in Cloud Run configuration
ENV MLFLOW_PORT=5000

# Create directory for temp files
RUN mkdir -p /tmp/mlflow

# Set working directory
WORKDIR /app

EXPOSE $MLFLOW_PORT

# Use the environment variables from Cloud Run
CMD exec gunicorn --bind :$MLFLOW_PORT --workers 1 --threads 8 --timeout 0 \
    --env MLFLOW_BACKEND_STORE_URI=$MLFLOW_BACKEND_STORE_URI \
    --env MLFLOW_DEFAULT_ARTIFACT_ROOT=$MLFLOW_DEFAULT_ARTIFACT_ROOT \
    mlflow.server:app