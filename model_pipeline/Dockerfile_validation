FROM python:3.11-slim
WORKDIR /model_pipeline
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip
ENV BLIS_ARCH=generic
RUN pip install --no-cache-dir blis==0.7.11
RUN pip install --no-cache-dir thinc==8.3.2
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
COPY . .
CMD ["python", "scripts/main.py"]