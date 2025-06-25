# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MCP_SERVER_MODE=docker

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies using uv (include watchdog for hot reload)
RUN uv sync --frozen --no-dev && uv add watchdog

# Copy source code
COPY src/ ./src/

# Create logs directory
RUN mkdir -p /app/src/logs

# Expose the port
EXPOSE 8000

# Traefik will handle service discovery via other means

# Run the MCP server using uv with conditional hot reload
CMD ["sh", "-c", "if [ \"$MCP_HOT_RELOAD\" = \"true\" ]; then echo 'Starting with hot reload...'; uv run watchmedo auto-restart --directory=./src --pattern=*.py --recursive -- python src/server.py; else echo 'Starting in production mode...'; uv run python src/server.py; fi"]
