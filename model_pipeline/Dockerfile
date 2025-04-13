FROM python:3.11-slim

WORKDIR /model_pipeline

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Create credentials directory
RUN mkdir -p /model_pipeline/credentials

# Install dependencies in one step, allow caching
RUN pip install --upgrade pip && \
    grep -v bert-score requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir torch==2.6.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install blis==1.0.0 thinc==8.3.2 bert-score google-cloud-secret-manager google-cloud-logging==3.10.0 -r requirements_filtered.txt && \
    python -m spacy download en_core_web_sm

COPY . .

ENV BLIS_ARCH=generic
ENV FLASK_ENV=production
ENV PORT=8000

CMD ["python", "scripts/fetch_gmail_threads.py"]