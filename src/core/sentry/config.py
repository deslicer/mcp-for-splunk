"""Sentry SDK configuration and initialization."""

import logging
import os
from contextvars import ContextVar

logger = logging.getLogger(__name__)

_sentry_sdk_available = False
try:
    import sentry_sdk

    _sentry_sdk_available = True
except ImportError:
    sentry_sdk = None  # type: ignore

_sentry_initialized = False

# Context variables for MCP request tracking
mcp_session_id: ContextVar[str | None] = ContextVar("mcp_session_id", default=None)
mcp_request_id: ContextVar[str | None] = ContextVar("mcp_request_id", default=None)
mcp_tool_name: ContextVar[str | None] = ContextVar("mcp_tool_name", default=None)


def is_sentry_enabled() -> bool:
    """Check if Sentry is enabled via environment configuration and SDK is available."""
    if not _sentry_sdk_available:
        return False
    dsn = os.getenv("SENTRY_DSN", "").strip()
    return bool(dsn)


def init_sentry() -> bool:
    """Initialize Sentry SDK. Returns True if initialized successfully."""
    global _sentry_initialized  # noqa: PLW0603 - exported for cross-module use

    if _sentry_initialized:
        return True

    if not _sentry_sdk_available:
        logger.info("sentry-sdk not installed")
        return False

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("SENTRY_DSN not set, Sentry disabled")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        try:
            from sentry_sdk.integrations.mcp import MCPIntegration

            _mcp_integration_available = True
        except ImportError:
            MCPIntegration = None  # type: ignore  # noqa: N806
            _mcp_integration_available = False

        environment = os.getenv("SENTRY_ENVIRONMENT", "development")
        release = os.getenv("SENTRY_RELEASE", "mcp-server-splunk@0.5.0")
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
        profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
        debug = os.getenv("SENTRY_DEBUG", "false").lower() == "true"
        enable_logs = os.getenv("SENTRY_ENABLE_LOGS", "true").lower() == "true"

        def traces_sampler(sampling_context: dict) -> float:
            """Custom sampler - always trace MCP/tool ops, lower rate for health checks."""
            ctx = sampling_context.get("transaction_context", {})
            name = ctx.get("name", "")
            op = ctx.get("op", "")

            if "mcp" in op.lower() or "mcp" in name.lower() or "tool" in op.lower():
                return 1.0
            if "/health" in name or "health" in op.lower():
                return 0.01
            return traces_sample_rate

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            debug=debug,
            traces_sampler=traces_sampler,
            profiles_sample_rate=profiles_sample_rate,
            enable_logs=enable_logs,
            auto_session_tracking=True,
            send_default_pii=os.getenv("SENTRY_SEND_PII", "true").lower() == "true",
            integrations=[
                *([MCPIntegration()] if _mcp_integration_available else []),
                AsyncioIntegration(),
                StarletteIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes={400, 401, 403, 404, 500, 502, 503},
                ),
                HttpxIntegration(),
                LoggingIntegration(
                    sentry_logs_level=logging.INFO,
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
            ],
            attach_stacktrace=True,
            max_breadcrumbs=100,
            before_send=_before_send_hook,
            before_send_transaction=_before_send_transaction_hook,
        )

        _sentry_initialized = True
        logger.info(
            "Sentry initialized (env=%s, release=%s, mcp=%s)",
            environment,
            release,
            "yes" if _mcp_integration_available else "no",
        )
        return True

    except ImportError as e:
        logger.warning("Sentry SDK import error: %s", e)
        return False
    except Exception as e:
        logger.error("Failed to initialize Sentry: %s", e)
        return False


def _before_send_hook(event: dict, hint: dict) -> dict | None:
    """Enrich error events with MCP context before sending to Sentry."""
    try:
        session_id = mcp_session_id.get()
        request_id = mcp_request_id.get()
        tool_name = mcp_tool_name.get()

        if "tags" not in event:
            event["tags"] = {}

        if session_id:
            event["tags"]["mcp.session.id"] = session_id
        if request_id:
            event["tags"]["mcp.request.id"] = request_id
        if tool_name:
            event["tags"]["mcp.tool.name"] = tool_name

        if "extra" not in event:
            event["extra"] = {}

        event["extra"]["mcp_context"] = {
            "session_id": session_id,
            "request_id": request_id,
            "tool_name": tool_name,
        }

    except Exception as e:
        logger.debug("Error enriching event: %s", e)

    return event


def _before_send_transaction_hook(event: dict, hint: dict) -> dict | None:
    """Enrich transaction events with MCP metadata."""
    try:
        session_id = mcp_session_id.get()
        if session_id:
            if "tags" not in event:
                event["tags"] = {}
            event["tags"]["mcp.session.id"] = session_id
    except Exception as e:
        logger.debug("Error enriching transaction: %s", e)

    return event

