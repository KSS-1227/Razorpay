FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install system dependencies needed by Pillow and optional image/PDF tooling.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       git \
       wget \
       curl \
       gcc \
       libglib2.0-0 \
       libsm6 \
       libxrender1 \
       libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HuggingFace Spaces requires a non-root user
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data/working /app/data/output /app/data/cache /app/data/uploads \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 7860

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
