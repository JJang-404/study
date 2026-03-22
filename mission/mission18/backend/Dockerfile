FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY movie_backend.py .
COPY koelectra_onnx/ ./koelectra_onnx/

EXPOSE 8000

CMD ["uvicorn", "movie_backend:app", "--host", "0.0.0.0", "--port", "8000"]