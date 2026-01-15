# TMDB Backend Docker Image
# Supports pipeline CLI, API server, and tests

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (mysql-client for database backup/restore)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY tmdb_pipeline/ ./tmdb_pipeline/
COPY api/ ./api/
COPY tests/ ./tests/
COPY scripts/ ./scripts/

# Create logs and data directories
RUN mkdir -p tmdb_pipeline/logs data

# Environment
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Create entrypoint script
RUN echo '#!/bin/bash\n\
if [ "$1" = "api" ]; then\n\
    shift\n\
    exec uvicorn api.main:app --host 0.0.0.0 --port 8000 "$@"\n\
elif [ "$1" = "test" ]; then\n\
    shift\n\
    exec pytest "$@"\n\
elif [ "$1" = "seed" ]; then\n\
    shift\n\
    exec python scripts/seed_from_remote.py "$@"\n\
else\n\
    exec python -m tmdb_pipeline "$@"\n\
fi' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["--help"]
