FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY pyproject.toml README.md ./
COPY ai_history ./ai_history/
COPY ai_history_web_new.py ./

# Install dependencies
RUN pip install --no-cache-dir . flask markdown psycopg2-binary redis gunicorn

# Expose port
EXPOSE 5000

# Environment variables
ENV FLASK_APP=ai_history_web_new.py
ENV FLASK_HOST=0.0.0.0

CMD ["gunicorn", "--workers", "1", "--threads", "8", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "ai_history_web_new:app"]
