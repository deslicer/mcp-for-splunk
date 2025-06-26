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
COPY contrib/ ./contrib/

# Create logs directory
RUN mkdir -p /app/src/logs

# Expose the port
EXPOSE 8000

# Support for choosing between old and new server
# Default to new modular server, but allow override via environment variable
ENV MCP_SERVER_VERSION=new

# Run the MCP server using uv with conditional hot reload and server selection
CMD ["sh", "-c", "SERVER_FILE=$([ \"$MCP_SERVER_VERSION\" = \"old\" ] && echo \"src/server.py\" || echo \"src/server_new.py\"); echo \"Starting $SERVER_FILE with MCP_SERVER_VERSION=$MCP_SERVER_VERSION\"; if [ \"$MCP_HOT_RELOAD\" = \"true\" ]; then echo 'Starting with hot reload...'; uv run watchmedo auto-restart --directory=./src --directory=./contrib --pattern=*.py --recursive -- python \"$SERVER_FILE\"; else echo 'Starting in production mode...'; uv run python \"$SERVER_FILE\"; fi"]
