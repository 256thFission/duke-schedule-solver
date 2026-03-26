# Duke Schedule Solver — Backend API
# Multi-stage build to keep image small

FROM python:3.10-slim AS base

WORKDIR /app

# Install system dependencies needed by ortools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY scripts/ scripts/
COPY backend/ backend/
COPY config/ config/

# Copy data: processed_courses.json for the solver, historical_catalog.json for transcript matching
COPY data/processed/processed_courses.json data/processed/processed_courses.json
COPY data/historical_catalog.json data/historical_catalog.json

# Python path: backend/ for local imports (schemas, utils), /app for scripts/
ENV PYTHONPATH="/app/backend:/app"

# ALLOWED_ORIGINS must be set at runtime to your frontend domain (e.g. https://yourapp.com)
# Defaults to http://localhost:5173 if unset — do NOT use "*" in production
ENV UVICORN_WORKERS=2

EXPOSE 8000

# Run with multiple workers for production concurrency
CMD uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${UVICORN_WORKERS}
