# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MCP_SERVER_MODE=docker
ENV PYTHONPATH=/app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./
COPY LICENSE ./

# Install Python dependencies using uv (include watchdog and reload tools for hot reload)
RUN uv sync --frozen --no-dev && uv add watchdog reloader

# Copy source code
COPY src/ ./src/
COPY contrib/ ./contrib/

# Create logs directory
RUN mkdir -p /app/src/logs

# Expose the port
EXPOSE 8000

# Run the MCP server using uv with enhanced hot reload support
CMD ["sh", "-c", "echo 'Starting modular MCP server (src/server.py)'; if [ \"$MCP_HOT_RELOAD\" = \"true\" ]; then echo 'Starting with enhanced hot reload...'; uv run watchmedo auto-restart --directory=./src --directory=./contrib --pattern=*.py --recursive --ignore-patterns='*/__pycache__/*;*.pyc;*.pyo;*/.pytest_cache/*' -- python -u src/server.py; else echo 'Starting in production mode...'; uv run python src/server.py; fi"]
