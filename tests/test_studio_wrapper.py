"""Unit tests for Dashboard Studio wrapper helpers."""

import json

import pytest

from src.tools.dashboards.studio_wrapper import (
    DashboardDefinitionPreparer,
    StudioDashboardWrapper,
    StudioThemeResolver,
)


class TestStudioThemeResolver:
    def test_resolve_explicit_dark(self):
        assert StudioThemeResolver.resolve({}, "dark") == "dark"

    def test_resolve_auto_from_ui_settings(self):
        definition = {"uiSettings": {"theme": "light"}, "title": "T"}
        assert StudioThemeResolver.resolve(definition, "auto") == "light"

    def test_resolve_auto_from_top_level_theme(self):
        definition = {"theme": "dark", "title": "T"}
        assert StudioThemeResolver.resolve(definition, "auto") == "dark"

    def test_resolve_auto_fallback_dark(self):
        assert StudioThemeResolver.resolve({"title": "T"}, "auto") == "dark"

    def test_resolve_auto_from_prewrapped_xml(self):
        xml = '<dashboard version="2" theme="light"><definition><![CDATA[{}]]></definition></dashboard>'
        assert StudioThemeResolver.resolve(xml, "auto", prewrapped=True) == "light"


class TestStudioDashboardWrapper:
    def test_wrap_dict_includes_theme_and_label(self):
        wrapped = StudioDashboardWrapper.wrap(
            {"title": "Demo", "dataSources": {}},
            label="Demo Label",
            description=None,
            theme="dark",
        )
        assert '<dashboard version="2" theme="dark">' in wrapped
        assert "<label>Demo Label</label>" in wrapped
        assert "<definition><![CDATA[" in wrapped

    def test_prewrapped_pass_through(self):
        prewrapped = (
            '<dashboard version="2" theme="light">\n'
            '  <definition><![CDATA[{"title":"X"}]]></definition>\n'
            "</dashboard>"
        )
        assert StudioDashboardWrapper.wrap(prewrapped, label=None, description=None, theme="dark") == prewrapped


class TestDashboardDefinitionPreparer:
    def test_prepare_auto_detects_json_string(self):
        prepared = DashboardDefinitionPreparer.prepare(
            json.dumps({"title": "Auto", "dataSources": {}, "visualizations": {}}),
            dashboard_type="auto",
            label=None,
            description=None,
            theme="auto",
        )
        assert not isinstance(prepared, str)
        assert prepared.resolved_type == "studio"
        assert prepared.resolved_theme == "dark"

    def test_prepare_classic_xml(self):
        prepared = DashboardDefinitionPreparer.prepare(
            "<dashboard><label>Classic</label></dashboard>",
            dashboard_type="auto",
            label=None,
            description=None,
            theme="auto",
        )
        assert not isinstance(prepared, str)
        assert prepared.resolved_type == "classic"
        assert prepared.resolved_theme is None

    def test_prepare_invalid_theme(self):
        result = DashboardDefinitionPreparer.prepare(
            {"title": "X"},
            dashboard_type="studio",
            label=None,
            description=None,
            theme="sepia",  # type: ignore[arg-type]
        )
        assert isinstance(result, str)
        assert "theme" in result.lower()
