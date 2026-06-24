#!/bin/bash
echo "🚀 Starting lore stack..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d --build
else
    docker compose up -d --build
fi
echo "✅ Stack is running at http://localhost:5000"
echo "📦 Store: local SQLite (+WAL) under ~/.lore — no postgres/redis"
