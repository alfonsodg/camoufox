FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m camoufox fetch

COPY service/ ./service/

EXPOSE 8888

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8888"]
