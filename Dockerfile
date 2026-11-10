FROM python:3.11-slim

# OpenCV, used by the OCR library, needs these system libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-secret settings, so the image builds and runs without a .env file.
# API keys are never baked in: they come from .env at run time (see docker-compose.yml).
ENV EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
    PINNED_RULE_GROUPS=H1,H2,H3,H11 \
    RETRIEVED_RULE_GROUPS=4 \
    KNOWLEDGE_DIR=data/knowledge_base \
    EVIDENCE_DIR=data/evidence \
    INDEX_DIR=index \
    MODEL_CACHE_DIR=.model_cache \
    PYTHONUNBUFFERED=1

COPY server ./server
COPY data ./data

# Download the embedding model and build the index now, so the container starts ready.
RUN python -m server.cli index

EXPOSE 8000
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
