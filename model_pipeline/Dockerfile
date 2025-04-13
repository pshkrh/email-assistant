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

# Install dependencies in steps to avoid conflicts
RUN pip install --upgrade pip && \
    # Remove bert-score from requirements to install it separately later
    grep -v bert-score requirements.txt > requirements_filtered.txt && \
    # Install problematic packages with exact versions first
    pip install --no-cache-dir protobuf==3.19.6 && \
    pip install --no-cache-dir opentelemetry-proto==1.26.0 && \
    pip install --no-cache-dir google-cloud-audit-log==0.2.5 && \
    pip install --no-cache-dir google-cloud-core==2.4.1 && \
    # Install PyTorch CPU version
    pip install --no-cache-dir torch==2.6.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu && \
    # Install spaCy dependencies with versions known to work together
    pip install --no-cache-dir blis==0.7.11 && \
    pip install --no-cache-dir thinc==8.3.2 && \
    # Then install Google Cloud dependencies
    pip install --no-cache-dir google-cloud-secret-manager==2.20.0 && \
    pip install --no-cache-dir google-cloud-logging==3.10.0 && \
    # Now install remaining requirements
    pip install --no-cache-dir -r requirements_filtered.txt && \
    # Install bert-score last
    pip install --no-cache-dir bert-score && \
    # Download spaCy model
    python -m spacy download en_core_web_sm

COPY . .

ENV BLIS_ARCH=generic
ENV FLASK_ENV=production
ENV PORT=8000

CMD ["python", "scripts/fetch_gmail_threads.py"]