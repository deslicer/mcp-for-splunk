"""
Phoenix OpenTelemetry instrumentation for MCP Server.

This module initializes Phoenix tracing for the MCP server, capturing:
- MCP tool calls and responses
- Splunk API interactions
- LLM calls (if using OpenAI/other providers)
- Custom application spans
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global flag to track if Phoenix is initialized
_phoenix_initialized = False


def initialize_phoenix_tracing() -> bool:
    """
    Initialize Phoenix OpenTelemetry tracing for the MCP server.
    
    Configuration via environment variables:
    - PHOENIX_COLLECTOR_ENDPOINT: Phoenix OTLP endpoint (e.g., http://localhost:6006/v1/traces)
    - PHOENIX_PROJECT_NAME: Phoenix project name (default: mcp-server-for-splunk)
    - PHOENIX_ENABLED: Enable/disable Phoenix tracing (default: true)
    - MCP_SERVICE_NAME: Service name for traces (default: mcp-server-for-splunk)
    
    Returns:
        bool: True if Phoenix was successfully initialized, False otherwise
    """
    global _phoenix_initialized
    
    if _phoenix_initialized:
        logger.debug("Phoenix tracing already initialized")
        return True
    
    # Check if Phoenix is enabled
    phoenix_enabled = os.getenv("PHOENIX_ENABLED", "true").lower() == "true"
    if not phoenix_enabled:
        logger.info("Phoenix tracing disabled via PHOENIX_ENABLED=false")
        return False
    
    phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    if not phoenix_endpoint:
        logger.info("Phoenix tracing not configured - PHOENIX_COLLECTOR_ENDPOINT not set")
        return False
    
    try:
        from phoenix.otel import register
        from openinference.instrumentation.mcp import MCPInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.semconv.resource import ResourceAttributes
        
        # Configuration
        project_name = os.getenv("PHOENIX_PROJECT_NAME", "mcp-server-for-splunk")
        service_name = os.getenv("MCP_SERVICE_NAME", "mcp-server-for-splunk")
        service_version = os.getenv("MCP_SERVICE_VERSION", "0.4.0")
        
        logger.info(f"Initializing Phoenix tracing: {service_name} -> {phoenix_endpoint}")
        
        # Create resource with service information
        resource = Resource(attributes={
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: service_version,
            "phoenix.project.name": project_name,
        })
        
        # Create OTLP exporter pointing to Phoenix
        otlp_exporter = OTLPSpanExporter(
            endpoint=phoenix_endpoint,
            headers=None,  # Add auth headers here if needed
        )
        
        # Create tracer provider with the resource
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # Register Phoenix OTEL (this sets the global tracer provider)
        register(
            project_name=project_name,
            tracer_provider=tracer_provider,
        )
        
        # Instrument MCP SDK
        # This will automatically trace all MCP tool calls, resource requests, etc.
        MCPInstrumentor().instrument()
        
        _phoenix_initialized = True
        logger.info(f"✅ Phoenix tracing initialized for project: {project_name}")
        logger.info(f"   Endpoint: {phoenix_endpoint}")
        logger.info(f"   Service: {service_name} v{service_version}")
        logger.info("   MCP instrumentation: enabled")
        
        return True
        
    except ImportError as e:
        logger.warning(f"Phoenix tracing dependencies not installed: {e}")
        logger.warning("Install with: uv add arize-phoenix-otel openinference-instrumentation-mcp")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Phoenix tracing: {e}", exc_info=True)
        return False


def is_phoenix_enabled() -> bool:
    """Check if Phoenix tracing is currently enabled."""
    return _phoenix_initialized


def add_trace_attributes(**attributes) -> None:
    """
    Add custom attributes to the current active span.
    
    Args:
        **attributes: Key-value pairs to add as span attributes
        
    Example:
        add_trace_attributes(
            user_id="user123",
            session_id="session456",
            splunk_instance="production"
        )
    """
    if not _phoenix_initialized:
        return
    
    try:
        from opentelemetry import trace
        
        span = trace.get_current_span()
        if span and span.is_recording():
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, str(value))
    except Exception as e:
        logger.debug(f"Failed to add trace attributes: {e}")


def trace_operation(name: str, **attributes):
    """
    Context manager for tracing a custom operation.
    
    Args:
        name: Name of the operation (e.g., "splunk.search", "cache.lookup")
        **attributes: Additional span attributes
        
    Example:
        with trace_operation("splunk.search", query="index=main", user="admin"):
            results = run_search(query)
    """
    if not _phoenix_initialized:
        # Return a no-op context manager
        from contextlib import nullcontext
        return nullcontext()
    
    try:
        from opentelemetry import trace
        
        tracer = trace.get_tracer(__name__)
        return tracer.start_as_current_span(name, attributes=attributes)
    except Exception as e:
        logger.debug(f"Failed to create trace span: {e}")
        from contextlib import nullcontext
        return nullcontext()


