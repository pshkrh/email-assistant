FROM python:3.11-slim

WORKDIR /model_pipeline

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN mkdir -p /model_pipeline/credentials

# Install a compatible protobuf version first
RUN pip install --upgrade pip && \
    pip install --no-cache-dir protobuf==4.23.4

# Install compatible versions of core dependencies
RUN pip install --no-cache-dir \
    opentelemetry-proto==1.26.0 \
    google-cloud-core==2.4.1 \
    google-cloud-audit-log==0.2.5 \
    grpcio-status==1.54.0 \
    googleapis-common-protos==1.60.0 \
    google-cloud-resource-manager==1.10.0 \
    google-cloud-logging==3.10.0 \
    google-cloud-secret-manager==2.20.0

# Install PyTorch separately
RUN pip install --no-cache-dir torch==2.6.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu

# Install spaCy dependencies with compatible versions
RUN pip install --no-cache-dir blis==1.0.0 thinc==8.3.2

# Create filtered requirements file
RUN grep -v "protobuf\|opentelemetry-proto\|google-cloud-resource-manager\|googleapis-common-protos\|grpcio-status\|google-cloud-core\|google-cloud-audit-log\|google-cloud-logging\|google-cloud-secret-manager\|torch\|blis\|thinc\|bert-score" requirements.txt > requirements_filtered.txt

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements_filtered.txt

# Install bert-score separately
RUN pip install --no-cache-dir bert-score

# Download spacy model
RUN python -m spacy download en_core_web_sm

COPY . .

ENV BLIS_ARCH=generic
ENV FLASK_ENV=production
ENV PORT=8000

CMD ["python", "scripts/fetch_gmail_threads.py"]