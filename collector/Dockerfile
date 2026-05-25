FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

RUN apt update && apt install -y --no-install-recommends \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY collector.py .

CMD ["python", "collector.py"]
