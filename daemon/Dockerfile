# Claude Daemon - 24/7 Async Operation
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | sh || true

# Copy daemon files
COPY queue.py memory.py runner.py submit.py approvals.py ./
COPY coherence.py registry.py github_webhook.py ./
COPY modules/ ./modules/

# Install Python dependencies
RUN pip install --no-cache-dir \
    openmemory-py \
    requests \
    pyyaml

# Create data directories
RUN mkdir -p /data /logs

# Environment
ENV PYTHONUNBUFFERED=1
ENV CLAUDE_DAEMON_DATA=/data
ENV CLAUDE_DAEMON_LOGS=/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/data/tasks.db').execute('SELECT 1')" || exit 1

# Default: run daemon
CMD ["python", "runner.py", "--continuous"]
