#!/bin/bash

export PORT=${PORT:-8080}

# Start the Celery worker in the background
echo "Starting Celery Background Worker..."
celery -A src.worker.celery_app worker --loglevel=info &

# Start the FastAPI Web Service in the foreground
echo "Starting FastAPI Web Service..."
uvicorn src.api.app:app --host 0.0.0.0 --port $PORT
