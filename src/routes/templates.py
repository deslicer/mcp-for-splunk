"""
Template handling utilities for the health routes.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_template(template_name: str) -> str:
    """Load a template file from the templates directory"""
    template_path = Path(__file__).parent / "templates" / template_name
    try:
        with open(template_path, encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Template file not found: {template_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading template {template_name}: {e}")
        raise

def load_css(css_name: str) -> str:
    """Load a CSS file from the static directory"""
    css_path = Path(__file__).parent / "static" / css_name
    try:
        with open(css_path, encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"CSS file not found: {css_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading CSS {css_name}: {e}")
        raise

def render_template(template_content: str, **kwargs) -> str:
    """Render a template with the given variables"""
    try:
        return template_content.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing template variable: {e}")
        raise
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        raise
