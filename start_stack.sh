#!/bin/bash
echo "🚀 Starting ai-history stack..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d --build
else
    docker compose up -d --build
fi
echo "✅ Stack is running at http://localhost:5000"
echo "📊 Database: postgres://ai_history:password@localhost:5432/ai_history"
echo "📦 Redis: redis://localhost:6379"
