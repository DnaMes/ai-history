FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 10001 ai

# Copy package files
COPY pyproject.toml README.md ./
COPY ai_history ./ai_history/
# cli entry-points are now inside the ai_history package (no extra root copies needed)

# Install dependencies (no postgres or redis — this app uses JSON + SQLite)
RUN pip install --no-cache-dir . gunicorn

# Switch to non-root user
USER ai
ENV HOME=/home/ai

# Expose port
EXPOSE 5000

CMD ["gunicorn", "--workers", "1", "--threads", "8", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "ai_history.interfaces.web:app"]
