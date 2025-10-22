"""
Tests for Dashboard Studio prompts.
"""

from pathlib import Path


class TestDashboardStudioPrompts:
    """Test Dashboard Studio prompt files."""

    def test_builder_prompt_exists(self):
        """Test builder prompt file exists."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        assert prompt_path.exists(), f"Builder prompt not found at {prompt_path}"

    def test_builder_prompt_loads(self):
        """Test builder prompt content loads successfully."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        content = prompt_path.read_text(encoding="utf-8")

        assert content is not None
        assert len(content) > 0

    def test_builder_prompt_has_key_sections(self):
        """Test builder prompt contains essential sections."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        content = prompt_path.read_text(encoding="utf-8")

        # Check for key instructional sections
        required_sections = [
            "Dashboard Studio Builder",
            "Steps",
            "definition",
            "JSON",
            "create_dashboard",
        ]

        for section in required_sections:
            assert section in content, f"Missing key section: {section}"

    def test_builder_prompt_has_authoring_guidance(self):
        """Test builder prompt includes authoring guidance."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        content = prompt_path.read_text(encoding="utf-8")

        # Check for authoring concepts
        authoring_keywords = [
            "dataSources" or "data source",
            "visualizations" or "visualization",
            "layout",
            "version",
            "SPL" or "query",
        ]

        matches = sum(1 for keyword in authoring_keywords if keyword in content)
        assert matches >= 3, "Builder prompt missing core authoring guidance"

    def test_builder_prompt_has_output_contract(self):
        """Test builder prompt specifies output contract."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        content = prompt_path.read_text(encoding="utf-8")

        # Check for output format guidance
        assert "output" in content.lower() or "Output" in content
        assert "JSON" in content or "json" in content
        assert '"version"' in content or "version" in content

    def test_builder_prompt_has_examples(self):
        """Test builder prompt includes examples."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        content = prompt_path.read_text(encoding="utf-8")

        # Check for code examples
        assert "```" in content or "example" in content.lower()

    def test_builder_prompt_references_resources(self):
        """Test builder prompt references Dashboard Studio resources."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        content = prompt_path.read_text(encoding="utf-8")

        # Check for resource references
        resource_refs = ["dashboard-studio://cheatsheet", "dashboard-studio://links", "cheatsheet"]

        matches = sum(1 for ref in resource_refs if ref in content)
        assert matches >= 1, "Builder prompt should reference Dashboard Studio resources"

    def test_builder_prompt_has_constraints(self):
        """Test builder prompt specifies REST creation constraints."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        content = prompt_path.read_text(encoding="utf-8")

        # Check for constraint guidance
        constraint_keywords = [
            "REST",
            "valid",
            "minimal" or "Minimal",
            "documented" or "documentation",
        ]

        matches = sum(1 for keyword in constraint_keywords if keyword in content)
        assert matches >= 2, "Builder prompt should specify creation constraints"

    def test_builder_prompt_has_validation_checks(self):
        """Test builder prompt includes validation checks."""
        prompt_path = Path("src/prompts/dashboard_studio_builder.md")
        content = prompt_path.read_text(encoding="utf-8")

        # Check for validation guidance
        validation_keywords = [
            "validate" or "Validate",
            "check" or "Check",
            "verify" or "Verify",
            "required",
        ]

        matches = sum(1 for keyword in validation_keywords if keyword in content)
        assert matches >= 2, "Builder prompt should include validation checks"
