FROM python:3.11-slim

RUN pip install mlflow==2.16.2 psycopg2-binary gunicorn

ENV BACKEND_STORE_URI=postgresql+psycopg2://postgres:postgres@/mlflow?host=/cloudsql/email-assistant-449706:us-central1:mlflow-db
ENV DEFAULT_ARTIFACT_ROOT=gs://mail_mate_mlflow_logs/mlflow-artifacts
ENV MLFLOW_PORT=5000

EXPOSE $MLFLOW_PORT

CMD exec gunicorn --bind :$MLFLOW_PORT --workers 1 --threads 8 --timeout 0 mlflow.server:app