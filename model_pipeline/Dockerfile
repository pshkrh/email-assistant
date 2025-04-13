FROM python:3.11-slim

WORKDIR /model_pipeline

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN mkdir -p /model_pipeline/credentials

RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch==2.6.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install blis==1.0.0 thinc==8.3.2 bert-score google-cloud-secret-manager google-cloud-logging==3.10.0 -r requirements.txt && \
    python -m spacy download en_core_web_sm

COPY . .

ENV BLIS_ARCH=generic
ENV FLASK_ENV=production
ENV PORT=8000

CMD ["python", "scripts/fetch_gmail_threads.py"]