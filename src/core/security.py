"""
Security utilities for MCP Server for Splunk.

Provides SPL query validation for dangerous commands and complexity limits.
Access control is handled by Splunk RBAC via user credentials.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SecurityViolationType(Enum):
    """Types of security violations that can be detected."""

    FORBIDDEN_COMMAND = "forbidden_command"
    EXCESSIVE_COMPLEXITY = "excessive_complexity"


@dataclass
class SecurityViolation:
    """Represents a security violation detected in a query."""

    violation_type: SecurityViolationType
    message: str
    query_snippet: str
    severity: str
    remediation: str


class QuerySecurityError(Exception):
    """Exception raised when a security violation is detected in a query."""

    def __init__(self, violation: SecurityViolation):
        self.violation = violation
        super().__init__(violation.message)


class SPLQueryValidator:
    """
    Validates Splunk SPL queries for dangerous commands and complexity.

    Note: Index access and subsearch permissions are handled by Splunk RBAC.
    """

    FORBIDDEN_COMMANDS = {
        # Data modification - dangerous regardless of RBAC
        "collect", "outputlookup", "outputcsv", "delete", "sendemail",
        # External execution
        "script", "run",
    }

    def __init__(
        self,
        additional_forbidden_commands: set[str] | None = None,
        max_query_length: int = 50000,
        max_pipe_depth: int = 50,
    ):
        self.max_query_length = max_query_length
        self.max_pipe_depth = max_pipe_depth

        self.forbidden_commands = self.FORBIDDEN_COMMANDS.copy()
        if additional_forbidden_commands:
            self.forbidden_commands.update(additional_forbidden_commands)

    def validate_query(self, query: str, strict: bool = True) -> tuple[bool, list[SecurityViolation]]:
        """
        Validate an SPL query for security issues.

        Args:
            query: The SPL query to validate
            strict: If True, raise exception on violation

        Returns:
            Tuple of (is_valid, violations_list)
        """
        violations: list[SecurityViolation] = []
        query = query.strip()

        # Check query length (DoS protection)
        if len(query) > self.max_query_length:
            violation = SecurityViolation(
                violation_type=SecurityViolationType.EXCESSIVE_COMPLEXITY,
                message=f"Query exceeds maximum length of {self.max_query_length}",
                query_snippet=query[:100] + "...",
                severity="medium",
                remediation=f"Reduce query length to under {self.max_query_length} characters",
            )
            violations.append(violation)
            if strict:
                raise QuerySecurityError(violation)

        # Check forbidden commands
        cmd_violations = self._check_forbidden_commands(query)
        violations.extend(cmd_violations)
        if strict and cmd_violations:
            raise QuerySecurityError(cmd_violations[0])

        # Check pipeline complexity (DoS protection)
        complexity_violations = self._check_pipeline_complexity(query)
        violations.extend(complexity_violations)
        if strict and complexity_violations:
            raise QuerySecurityError(complexity_violations[0])

        return len(violations) == 0, violations

    def _check_forbidden_commands(self, query: str) -> list[SecurityViolation]:
        """Check for forbidden SPL commands that could cause damage."""
        violations = []
        query_lower = query.lower()
        for cmd in self.forbidden_commands:
            if re.search(r"\b" + re.escape(cmd) + r"\b", query_lower):
                violations.append(SecurityViolation(
                    violation_type=SecurityViolationType.FORBIDDEN_COMMAND,
                    message=f"Forbidden command '{cmd}' detected",
                    query_snippet=self._extract_context(query, cmd),
                    severity="high",
                    remediation=f"Remove '{cmd}' command",
                ))
                logger.warning(f"Forbidden command blocked: {cmd}")
        return violations

    def _check_pipeline_complexity(self, query: str) -> list[SecurityViolation]:
        """Check for excessive pipeline depth (DoS protection)."""
        pipe_count = query.count("|")
        if pipe_count > self.max_pipe_depth:
            return [SecurityViolation(
                violation_type=SecurityViolationType.EXCESSIVE_COMPLEXITY,
                message=f"Pipeline depth {pipe_count} exceeds limit {self.max_pipe_depth}",
                query_snippet=query[:100] + "...",
                severity="medium",
                remediation="Simplify query",
            )]
        return []

    def _extract_context(self, text: str, keyword: str, chars: int = 50) -> str:
        pos = text.lower().find(keyword.lower())
        if pos == -1:
            return text[:100]
        start, end = max(0, pos - chars), min(len(text), pos + len(keyword) + chars)
        snippet = text[start:end]
        return ("..." if start > 0 else "") + snippet + ("..." if end < len(text) else "")

    def sanitize_query(self, query: str) -> str:
        """Prepare query by adding search command if needed."""
        query = query.strip()
        if not query.lower().startswith(("search ", "| ")):
            query = f"search {query}"
        return query


_default_validator = SPLQueryValidator()


def validate_search_query(query: str, strict: bool = True) -> tuple[bool, list[SecurityViolation]]:
    """Validate an SPL query for security issues."""
    return _default_validator.validate_query(query, strict=strict)


def sanitize_search_query(query: str) -> str:
    """Sanitize and validate a Splunk search query."""
    _default_validator.validate_query(query, strict=True)
    return _default_validator.sanitize_query(query)


def get_security_config() -> dict[str, Any]:
    """Get current security configuration."""
    return {
        "max_query_length": _default_validator.max_query_length,
        "max_pipe_depth": _default_validator.max_pipe_depth,
        "forbidden_commands": list(_default_validator.forbidden_commands),
        "note": "Index access controlled by Splunk RBAC",
    }
