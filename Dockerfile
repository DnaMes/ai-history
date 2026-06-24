FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create the non-root user. Its home is made traversable (0711) so the
# container can also run as the host user via compose's `user:` override —
# the process must be able to *enter* /home/ai to reach the bind-mounted
# /home/ai/.lore data volume. 0711 allows traversal without listing.
RUN useradd -m -u 10001 ai && chmod 0711 /home/ai

# Copy package files
COPY pyproject.toml README.md ./
COPY lore ./lore/
# Top-level CLI entry modules referenced by [project.scripts] / py-modules.
COPY lore_cli.py lore_session_cli.py ./

# Install dependencies (no postgres or redis — this app uses JSON + SQLite)
RUN pip install --no-cache-dir . gunicorn

# Switch to non-root user
USER ai
ENV HOME=/home/ai

# Set TRUSTED_PROXY=1 when a reverse proxy (nginx, Caddy, Traefik…) sits in
# front of this container. Without it, X-Forwarded-For is ignored so clients
# cannot spoof their IP address. Leave unset for direct exposure.
# ENV TRUSTED_PROXY=1

# Expose port
EXPOSE 5000

CMD ["gunicorn", "--workers", "1", "--threads", "8", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "lore.interfaces.web:app"]
