#!/bin/bash

# BUDDY Cloud Deployment Startup Script
# This script is used by Render.com to start the BUDDY backend

echo "🤖 Starting BUDDY AI Assistant - Cloud Backend"
echo "================================================"

# Set environment variables
export PORT=${PORT:-8081}
export HOST=${HOST:-0.0.0.0}

# Print configuration
echo "Configuration:"
echo "- Port: $PORT"
echo "- Host: $HOST"
echo "- Python: $(python --version)"

# Check if we're in production
if [ "$RENDER" = "true" ]; then
    echo "- Environment: Production (Render)"
else
    echo "- Environment: Development"
fi

echo ""
echo "Starting BUDDY backend server..."

# Start the server using gunicorn for production
if [ "$RENDER" = "true" ]; then
    echo "Using Gunicorn for production..."
    exec gunicorn cloud_backend:app \
        --bind 0.0.0.0:$PORT \
        --workers 2 \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --access-logfile - \
        --error-logfile -
else
    echo "Using Uvicorn for development..."
    exec python cloud_backend.py
fi
