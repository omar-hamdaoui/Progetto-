FROM python:3.10-slim

# Evita file .pyc e buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# install build deps + runtime tools (curl per healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git wget curl ca-certificates \
    libjpeg-dev libpng-dev libopenblas-dev libblas-dev liblapack-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installa dipendenze prima di copiare tutto per sfruttare la cache
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt --no-cache-dir

# Copia il resto del codice
COPY . /app

EXPOSE 5000
CMD ["python", "app.py"]
