FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_ITSI_SERVER_PORT=8001 \
    MCP_ITSI_TRANSPORT=http

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 mcp \
    && useradd --system --uid 1001 --gid mcp --home-dir /app --shell /usr/sbin/nologin mcp

ADD https://astral.sh/uv/install.sh /uv-installer.sh
ENV UV_INSTALL_DIR=/usr/local/bin
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="${PATH}:/root/.cargo/bin"

COPY pyproject.toml uv.lock README.md LICENSE ./
# The parent pyproject.toml declares packaging/mcp-itsi-server as a uv
# workspace member (and redirects mcp-itsi-server -> {workspace = true}).
# Without the member directory present, `uv sync --frozen` fails with:
#   "mcp-itsi-server references a workspace ... but is not a workspace member"
COPY packaging/ ./packaging/
COPY mcp_itsi/ ./mcp_itsi/

RUN uv sync --frozen --no-dev \
    && chown -R mcp:mcp /app

USER mcp

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl --fail --silent --show-error http://127.0.0.1:8001/mcp/ -H 'Accept: application/json' >/dev/null || exit 1

CMD ["uv", "run", "mcp-itsi-server", "--host", "0.0.0.0", "--port", "8001"]
