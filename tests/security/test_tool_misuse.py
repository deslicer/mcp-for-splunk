"""
Security tests for tool misuse prevention.

Tests that dangerous SPL commands are blocked while normal operations work.
Index access and subsearches are delegated to Splunk RBAC.
"""

import pytest

from src.core.security import (
    QuerySecurityError,
    SPLQueryValidator,
    sanitize_search_query,
    validate_search_query,
)


class TestSearchToolSecurity:
    """Tests for search tool security."""

    def test_normal_search_allowed(self):
        """Normal searches should work."""
        queries = [
            "index=main error",
            "index=* | stats count by sourcetype",
            "search index=web status>=400 | timechart count",
        ]
        for query in queries:
            result = sanitize_search_query(query)
            assert result  # Should return sanitized query

    def test_complex_search_allowed(self):
        """Complex but safe searches should work."""
        query = r"""
        index=main sourcetype=access_combined
        | rex field=_raw "user=(?<username>\w+)"
        | stats count by username, status
        | where count > 100
        | sort -count
        | head 20
        """
        result = sanitize_search_query(query.strip())
        assert "search" in result.lower()

    def test_data_modification_blocked(self):
        """Data modification commands should be blocked."""
        dangerous = [
            "index=main | collect index=exfil",
            "index=main | outputlookup stolen.csv",
            "index=main | delete",
        ]
        for query in dangerous:
            with pytest.raises(QuerySecurityError):
                sanitize_search_query(query)


class TestSubsearchesAllowed:
    """Tests confirming subsearches are allowed (Splunk RBAC handles access)."""

    def test_basic_subsearch(self):
        """Basic subsearches should work."""
        query = "index=main [ search index=users | return email ]"
        valid, _ = validate_search_query(query, strict=False)
        assert valid

    def test_join_with_subsearch(self):
        """Joins with subsearches should work."""
        query = "index=main | join user [ search index=hr | fields user, department ]"
        valid, _ = validate_search_query(query, strict=False)
        assert valid

    def test_append_with_subsearch(self):
        """Append with subsearches should work."""
        query = "index=web | append [ search index=app | stats count ]"
        valid, _ = validate_search_query(query, strict=False)
        assert valid


class TestInternalIndexesAllowed:
    """Tests confirming internal indexes are allowed (Splunk RBAC handles access)."""

    def test_audit_index(self):
        """_audit index should be accessible if user has permissions."""
        query = "index=_audit action=search | stats count by user"
        valid, _ = validate_search_query(query, strict=False)
        assert valid

    def test_internal_index(self):
        """_internal index should be accessible if user has permissions."""
        query = "index=_internal sourcetype=splunkd | stats count"
        valid, _ = validate_search_query(query, strict=False)
        assert valid


class TestValidatorConfiguration:
    """Tests for validator configuration."""

    def test_strict_mode(self):
        """Strict mode should raise exceptions."""
        with pytest.raises(QuerySecurityError):
            validate_search_query("index=main | collect index=x", strict=True)

    def test_non_strict_mode(self):
        """Non-strict mode should return violations list."""
        valid, violations = validate_search_query("index=main | collect index=x", strict=False)
        assert not valid
        assert len(violations) > 0

    def test_custom_forbidden_commands(self):
        """Custom forbidden commands should be enforced."""
        validator = SPLQueryValidator(additional_forbidden_commands={"eventstats"})
        with pytest.raises(QuerySecurityError):
            validator.validate_query("index=main | eventstats count")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
