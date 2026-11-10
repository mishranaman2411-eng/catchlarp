# Production Dockerfile for Render free tier (FastAPI + yt-dlp + ffmpeg + Groq + Gemini)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

WORKDIR /app

# Install Debian system dependencies first (ffmpeg includes ffprobe; curl for diagnostics/healthcheck)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies before copying app code to maximize layer caching
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create a non-root user and ensure /app is writable for SQLite reel_cache.db
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-10000}/" >/dev/null || exit 1

# Bind to 0.0.0.0:$PORT with a single worker to fit Render free tier (512 MB RAM) and avoid SQLite lock contention
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
