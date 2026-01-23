#!/bin/bash
# Start Claude Daemon Stack

set -e

# Check for required env vars
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Warning: ANTHROPIC_API_KEY not set"
    echo "Set it in .env or export before running"
fi

# Build and start
echo "Starting Claude Daemon Stack..."
docker-compose up -d --build

# Show status
echo ""
echo "Services started:"
docker-compose ps

echo ""
echo "Logs: docker-compose logs -f"
echo "Stop: docker-compose down"
echo ""
echo "Submit tasks: python daemon/submit.py 'Your task here'"
echo "GitHub webhook: http://localhost:8080/webhook"
