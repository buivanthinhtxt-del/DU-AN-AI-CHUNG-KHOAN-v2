# ==============================================================================
# STAGE 1: Build React Frontend Workstation (Vite)
# ==============================================================================
FROM node:20-alpine AS web-builder
WORKDIR /app/web

# Install web dependencies with reproducible npm ci
COPY web/package*.json ./
RUN npm ci

# Copy frontend source code and compile production bundles
COPY web/ ./
RUN npm run build

# ==============================================================================
# STAGE 2: Python 3.11-slim All-in-One Runtime (Render & Hugging Face Spaces)
# ==============================================================================
FROM python:3.11-slim

# Create dedicated non-root user with UID 1000 (standard for Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Configure environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=7860

WORKDIR /app

# Install essential system dependencies (SSL certs, curl for healthchecks, tzdata)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend source code, demo page, and pre-compiled React frontend
COPY --chown=user:user backend/ ./backend/
COPY --chown=user:user fiintrade_demo.html ./fiintrade_demo.html
COPY --chown=user:user --from=web-builder /app/web/dist ./web/dist

# Ensure proper write permissions for cache, data directory, and home directory
RUN mkdir -p /app/backend/cache/forecast_audit \
             /app/backend/data/ohlcv \
             /home/user/.cache \
             /tmp && \
    chown -R 1000:1000 /app /home/user && \
    chmod -R 775 /app/backend && \
    chmod -R 777 /tmp

# Switch to non-root UID 1000 user
USER user

# Expose default port (7860 for Hugging Face Spaces)
EXPOSE 7860

# Dynamic PORT binding: Render provides $PORT dynamically; defaults to 7860
CMD ["sh", "-c", "uvicorn api:app --app-dir backend --host 0.0.0.0 --port ${PORT:-7860}"]
