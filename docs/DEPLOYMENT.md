# Deployment Guide

## Docker Deployment

### Prerequisites

- Docker and Docker Compose installed
- Access to the project directory

### Building and Deploying

```bash
# Build the Docker image (recommended before deploying)
docker compose build --no-cache

# Deploy/start the stack
docker compose up -d

# Watch logs
docker compose logs -f app

# Check status
docker compose ps
```

### Important Notes

1. **The container name is `ai-history-app`** (defined in docker-compose.yml)
2. **The image tag is `ai-history-app:latest`**
3. **Container is healthy** if `docker compose ps` shows `(healthy)` status

### Version Mismatch Warning

The local codebase and container may occasionally get out of sync:

If you see unexpected behavior after pulling updates:

1. Rebuild: `docker compose build --no-cache`
2. Restart: `docker compose restart app`
3. Check container logs: `docker compose logs app`

### Environment Variables

See README.md "Production Ops" section for rate limiting and logging configuration.

### Accessing the Application

- **Local**: http://localhost:5000
- **Deployed (via Traefik or reverse proxy)**: https://your-domain.example.com/

### Clearing Container State

```bash
# Restart fresh (keeps volumes)
docker compose restart app

# Full rebuild (no cache)
docker compose build --no-cache && docker compose up -d

# Stop everything
docker compose down
```

### Database and Redis

- **db container**: PostgreSQL 15 Alpine (persistent via `db_data` volume)
- **redis container**: Redis Alpine (persistent via `redis_data` volume)

To reset data:

```bash
docker compose down -v  # WARNING: Deletes all data volumes
docker compose up -d
```
