FROM python:3.11-slim
WORKDIR /model_pipeline
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
ENV BLIS_ARCH=generic

# Create credentials directory
RUN mkdir -p /model_pipeline/credentials

RUN pip install --upgrade pip && \
    grep -v bert-score requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir blis==0.7.11 && \ 
    pip install --no-cache-dir thinc==8.3.2 && \
    pip install torch==2.6.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    pip install bert-score && \
    pip install google-cloud-secret-manager && \
    python -m spacy download en_core_web_sm

COPY . .

# Make sure the Flask app listens on all interfaces
ENV FLASK_ENV=production
ENV PORT=8000

CMD ["python", "scripts/fetch_gmail_threads.py"]