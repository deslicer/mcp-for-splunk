"""Structured ITSI object schemas and payload validation.

This package serves machine-usable schemas (parsed from the ITSI 4.21 REST API
schema docs) and validates payloads against them so agents can perform CRUD on
deeply nested ITOA objects reliably.

Public surface:

* :class:`~mcp_itsi.knowledge.schema.models.ObjectSchema`
* :data:`~mcp_itsi.knowledge.schema.registry.registry` (shared instance)
* :class:`~mcp_itsi.knowledge.schema.validator.PayloadValidator`
"""

from __future__ import annotations

from mcp_itsi.knowledge.schema.models import AttributeSpec, ObjectSchema
from mcp_itsi.knowledge.schema.registry import SchemaRegistry, registry
from mcp_itsi.knowledge.schema.validator import (
    PayloadValidator,
    ValidationIssue,
    ValidationResult,
)

__all__ = [
    "AttributeSpec",
    "ObjectSchema",
    "SchemaRegistry",
    "registry",
    "PayloadValidator",
    "ValidationIssue",
    "ValidationResult",
]
