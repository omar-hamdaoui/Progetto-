FROM python:3.10-slim

# install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git wget ca-certificates \
    libjpeg-dev libpng-dev libopenblas-dev libblas-dev liblapack-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
COPY . /app

RUN pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt --no-cache-dir

EXPOSE 5000
CMD ["python", "app.py"]
