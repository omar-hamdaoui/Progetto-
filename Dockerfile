# Development-friendly Dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system deps needed to build dlib/face_recognition and runtime (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git wget curl ca-certificates \
    libjpeg-dev libpng-dev libopenblas-dev liblapack-dev pkg-config \
    python3-dev zlib1g-dev libx11-dev libgtk-3-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install first to leverage cache
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r /app/requirements.txt

# Create non-root user to avoid root-owned files on host mounts
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser \
 && mkdir -p /app/data && chown -R appuser:appgroup /app

# Copy app and set ownership
COPY --chown=appuser:appgroup . /app

USER appuser

EXPOSE 5000

# Dev entry (for production use gunicorn instead)
CMD ["python", "app.py"]