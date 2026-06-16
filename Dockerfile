FROM python:3.11-slim AS backend-builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    poppler-utils \
    libkrb5-dev \
    comerr-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY utils/ ./utils/

RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM nginx:alpine AS frontend-server

WORKDIR /usr/share/nginx/html

RUN rm -rf ./*

COPY index.html .

EXPOSE 80