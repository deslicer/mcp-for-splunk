# Use Python 3.12 slim image for better wheel availability
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MCP_SERVER_MODE=docker
ENV PYTHONPATH=/app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gcc \
    libc-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
ENV UV_INSTALL_DIR=/usr/local/bin
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure uv is on PATH
ENV PATH="${PATH}:/root/.cargo/bin"

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./
COPY LICENSE ./

# Install Python dependencies
RUN uv sync --frozen --no-dev && uv add watchdog "sentry-sdk[mcp,starlette,httpx,asyncio]"

# Copy source code
COPY src/ ./src/
COPY contrib/ ./contrib/
COPY docs/ ./docs/

# Create logs directory
RUN mkdir -p /app/src/logs

# Expose the internal HTTP port the server binds to
EXPOSE 8001

# Run the MCP server using uv with enhanced hot reload support
CMD ["sh", "-c", "echo 'Starting modular MCP server (src/server.py)'; if [ \"$MCP_HOT_RELOAD\" = \"true\" ]; then echo 'Starting with enhanced hot reload...'; uv run watchmedo auto-restart --directory=./src --directory=./contrib --pattern=*.py --recursive --ignore-patterns='*/__pycache__/*;*.pyc;*.pyo;*/.pytest_cache/*' -- python -u src/server.py; else echo 'Starting in production mode...'; uv run python src/server.py; fi"]
