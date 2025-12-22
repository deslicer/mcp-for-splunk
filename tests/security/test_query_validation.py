"""
Security tests for SPL query validation.

Tests forbidden command blocking and complexity limits.
Index access and subsearches are handled by Splunk RBAC.
"""

import pytest

from src.core.security import (
    QuerySecurityError,
    SecurityViolationType,
    SPLQueryValidator,
    get_security_config,
    sanitize_search_query,
    validate_search_query,
)


class TestForbiddenCommands:
    """Tests for forbidden command blocking."""

    @pytest.mark.parametrize("cmd", [
        "collect", "outputlookup", "outputcsv", "delete", "sendemail", "script", "run"
    ])
    def test_forbidden_command_blocked(self, cmd):
        """Test that data-modifying commands are blocked."""
        query = f"index=main | {cmd} test"
        with pytest.raises(QuerySecurityError) as exc:
            sanitize_search_query(query)
        assert exc.value.violation.violation_type == SecurityViolationType.FORBIDDEN_COMMAND

    def test_safe_commands_allowed(self):
        """Test that normal SPL commands work."""
        queries = [
            "index=main error | stats count",
            "index=web | timechart span=1h count",
            "index=app | top 10 host",
            "search index=main | where status>=400",
            "| inputlookup users.csv | search active=true",
        ]
        for query in queries:
            valid, violations = validate_search_query(query, strict=False)
            assert valid, f"Query should be valid: {query}"


class TestComplexityLimits:
    """Tests for query complexity limits."""

    def test_query_length_limit(self):
        """Test that very long queries are blocked."""
        validator = SPLQueryValidator(max_query_length=100)
        long_query = "index=main " + "| eval x=1 " * 50

        with pytest.raises(QuerySecurityError) as exc:
            validator.validate_query(long_query)
        assert exc.value.violation.violation_type == SecurityViolationType.EXCESSIVE_COMPLEXITY

    def test_pipeline_depth_limit(self):
        """Test that deeply nested pipelines are blocked."""
        validator = SPLQueryValidator(max_pipe_depth=5)
        deep_query = "index=main" + " | stats count" * 10

        with pytest.raises(QuerySecurityError) as exc:
            validator.validate_query(deep_query)
        assert exc.value.violation.violation_type == SecurityViolationType.EXCESSIVE_COMPLEXITY

    def test_normal_complexity_allowed(self):
        """Test that reasonable queries pass."""
        query = "index=main | stats count by host | sort -count | head 10"
        valid, _ = validate_search_query(query, strict=False)
        assert valid


class TestSplunkRBACDelegation:
    """Tests confirming Splunk RBAC handles access control."""

    def test_subsearches_allowed(self):
        """Subsearches are allowed - Splunk RBAC handles access."""
        queries = [
            "index=main [ search index=summary | return host ]",
            "index=web | append [ search index=app ]",
            "index=main | join user [ search index=users ]",
        ]
        for query in queries:
            valid, _ = validate_search_query(query, strict=False)
            assert valid, f"Subsearch should be allowed: {query}"

    def test_internal_indexes_allowed(self):
        """Internal indexes allowed - Splunk RBAC handles access."""
        queries = [
            "index=_internal | stats count",
            "index=_audit action=search | table user",
            "index=_introspection | timechart count",
        ]
        for query in queries:
            valid, _ = validate_search_query(query, strict=False)
            assert valid, f"Internal index should be allowed: {query}"


class TestQuerySanitization:
    """Tests for query sanitization."""

    def test_adds_search_command(self):
        """Test that search command is added when missing."""
        result = sanitize_search_query("index=main error")
        assert result.startswith("search ")

    def test_preserves_existing_search(self):
        """Test that existing search command is preserved."""
        result = sanitize_search_query("search index=main")
        assert result == "search index=main"

    def test_preserves_pipe_start(self):
        """Test that pipe-starting queries are preserved."""
        result = sanitize_search_query("| inputlookup test.csv")
        assert result == "| inputlookup test.csv"


class TestSecurityConfig:
    """Tests for security configuration."""

    def test_config_structure(self):
        """Test that config returns expected structure."""
        config = get_security_config()
        assert "max_query_length" in config
        assert "max_pipe_depth" in config
        assert "forbidden_commands" in config
        assert isinstance(config["forbidden_commands"], list)


class TestCustomValidator:
    """Tests for custom validator configuration."""

    def test_additional_forbidden_commands(self):
        """Test adding custom forbidden commands."""
        validator = SPLQueryValidator(additional_forbidden_commands={"custom_cmd"})

        with pytest.raises(QuerySecurityError):
            validator.validate_query("index=main | custom_cmd")

    def test_custom_limits(self):
        """Test custom complexity limits."""
        validator = SPLQueryValidator(max_query_length=50, max_pipe_depth=2)

        # Should fail length
        with pytest.raises(QuerySecurityError):
            validator.validate_query("x" * 100)

        # Should fail depth
        with pytest.raises(QuerySecurityError):
            validator.validate_query("a | b | c | d")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
