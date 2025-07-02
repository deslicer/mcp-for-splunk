"""
Content processors for converting documentation formats.
"""

try:
    from .html_processor import SplunkDocsProcessor

    __all__ = ["SplunkDocsProcessor"]
except ImportError:
    # Handle missing dependencies gracefully
    __all__ = []
