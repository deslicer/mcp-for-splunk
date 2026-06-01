"""Dashboard Studio XML wrapping and theme resolution for create_dashboard."""

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

ThemeParam = Literal["light", "dark", "auto"]
ResolvedTheme = Literal["light", "dark"]
DashboardType = Literal["studio", "classic"]


def _xml_escape(value: str) -> str:
    """Escape text for XML element content without using the stdlib xml package."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@dataclass(frozen=True)
class PreparedDashboard:
    """Normalized dashboard payload ready for Splunk REST create/update."""

    eai_data: str
    resolved_type: DashboardType
    resolved_theme: ResolvedTheme | None
    definition_size_bytes: int


class StudioThemeResolver:
    """Resolve Dashboard Studio light/dark theme from params or definition content."""

    _THEME_PATTERN = re.compile(r'<dashboard[^>]*\stheme="(light|dark)"', re.IGNORECASE)

    @classmethod
    def resolve(
        cls,
        definition: Any,
        theme_param: ThemeParam,
        *,
        prewrapped: bool = False,
    ) -> ResolvedTheme:
        if theme_param in ("light", "dark"):
            return theme_param

        detected = cls._from_definition(definition, prewrapped=prewrapped)
        return detected or "dark"

    @classmethod
    def from_eai_data(cls, eai_data: str) -> ResolvedTheme | None:
        if "<dashboard" in eai_data:
            return cls._from_xml(eai_data)
        return None

    @classmethod
    def _from_definition(cls, definition: Any, *, prewrapped: bool) -> ResolvedTheme | None:
        if prewrapped and isinstance(definition, str):
            return cls._from_xml(definition)

        data = cls._as_dict(definition)
        if data is not None:
            return cls._from_dict(data)

        if isinstance(definition, str) and "<dashboard" in definition:
            return cls._from_xml(definition)
        return None

    @staticmethod
    def _as_dict(definition: Any) -> dict | None:
        if isinstance(definition, dict):
            return definition
        if isinstance(definition, str):
            try:
                parsed = json.loads(definition)
            except json.JSONDecodeError:
                return None
            return parsed if isinstance(parsed, dict) else None
        return None

    @staticmethod
    def _from_dict(data: dict) -> ResolvedTheme | None:
        ui_settings = data.get("uiSettings")
        if isinstance(ui_settings, dict):
            theme = ui_settings.get("theme")
            if theme in ("light", "dark"):
                return theme

        theme = data.get("theme")
        if theme in ("light", "dark"):
            return theme

        options = data.get("options")
        if isinstance(options, dict):
            option_theme = options.get("theme")
            if option_theme in ("light", "dark"):
                return option_theme
        return None

    @classmethod
    def _from_xml(cls, xml: str) -> ResolvedTheme | None:
        match = cls._THEME_PATTERN.search(xml)
        if match:
            return match.group(1).lower()  # type: ignore[return-value]
        return None


class StudioDashboardWrapper:
    """Wrap Dashboard Studio JSON in Splunk's required XML + CDATA structure."""

    @staticmethod
    def is_prewrapped(definition: str) -> bool:
        return "<definition>" in definition or "<dashboard" in definition

    @classmethod
    def wrap(
        cls,
        definition: Any,
        *,
        label: str | None,
        description: str | None,
        theme: ResolvedTheme,
    ) -> str:
        if isinstance(definition, str) and cls.is_prewrapped(definition):
            return definition

        studio_json_str = cls._normalize_json(definition)
        cdata_safe_json = studio_json_str.replace("]]>", "]]]]><![CDATA[>")

        xml_parts: list[str] = [f'<dashboard version="2" theme="{theme}">']
        if label:
            xml_parts.append(f"  <label>{_xml_escape(label)}</label>")
        if description:
            xml_parts.append(f"  <description>{_xml_escape(description)}</description>")
        xml_parts.extend(
            [
                "  <definition><![CDATA[",
                cdata_safe_json,
                "  ]]></definition>",
                "</dashboard>",
            ]
        )
        return "\n".join(xml_parts)

    @staticmethod
    def _normalize_json(definition: Any) -> str:
        if isinstance(definition, dict):
            return json.dumps(definition, separators=(",", ":"))
        if isinstance(definition, str):
            try:
                parsed = json.loads(definition)
                return json.dumps(parsed, separators=(",", ":"))
            except json.JSONDecodeError:
                return definition.strip()
        raise TypeError("Studio definition must be dict or str")


class DashboardDefinitionPreparer:
    """Detect dashboard type and build eai:data for Splunk REST create/update."""

    @classmethod
    def prepare(
        cls,
        definition: Any,
        *,
        dashboard_type: str,
        label: str | None,
        description: str | None,
        theme: ThemeParam,
    ) -> PreparedDashboard | str:
        resolved_type_input = dashboard_type if dashboard_type in ("studio", "classic", "auto") else "auto"

        if theme not in ("light", "dark", "auto"):
            return "Invalid 'theme'. Use 'light', 'dark', or 'auto' (Dashboard Studio wrapper only)."

        if resolved_type_input == "classic":
            return cls._prepare_classic(definition)

        if resolved_type_input == "studio":
            return cls._prepare_studio(definition, label=label, description=description, theme=theme)

        return cls._prepare_auto(definition, label=label, description=description, theme=theme)

    @classmethod
    def _prepare_classic(cls, definition: Any) -> PreparedDashboard | str:
        if not isinstance(definition, str):
            return "Classic dashboards require XML string definition"
        return PreparedDashboard(
            eai_data=definition,
            resolved_type="classic",
            resolved_theme=None,
            definition_size_bytes=len(definition.encode("utf-8")),
        )

    @classmethod
    def _prepare_studio(
        cls,
        definition: Any,
        *,
        label: str | None,
        description: str | None,
        theme: ThemeParam,
    ) -> PreparedDashboard | str:
        if not isinstance(definition, (dict, str)):
            return "Studio dashboards require JSON (dict) or JSON string"

        prewrapped = isinstance(definition, str) and StudioDashboardWrapper.is_prewrapped(definition)
        resolved_theme = StudioThemeResolver.resolve(definition, theme, prewrapped=prewrapped)

        try:
            eai_data = StudioDashboardWrapper.wrap(
                definition,
                label=label,
                description=description,
                theme=resolved_theme,
            )
        except Exception as wrap_err:  # pylint: disable=broad-except
            return f"Invalid Studio definition: {wrap_err}"

        if prewrapped:
            extracted = StudioThemeResolver.from_eai_data(eai_data)
            if extracted:
                resolved_theme = extracted

        return PreparedDashboard(
            eai_data=eai_data,
            resolved_type="studio",
            resolved_theme=resolved_theme,
            definition_size_bytes=len(eai_data.encode("utf-8")),
        )

    @classmethod
    def _prepare_auto(
        cls,
        definition: Any,
        *,
        label: str | None,
        description: str | None,
        theme: ThemeParam,
    ) -> PreparedDashboard | str:
        if isinstance(definition, dict):
            return cls._prepare_studio(definition, label=label, description=description, theme=theme)

        if isinstance(definition, str):
            if "<definition>" in definition:
                return cls._prepare_studio(definition, label=label, description=description, theme=theme)

            try:
                json.loads(definition)
            except (json.JSONDecodeError, TypeError):
                return cls._prepare_classic(definition)

            return cls._prepare_studio(definition, label=label, description=description, theme=theme)

        return "Invalid 'definition' type. Expect dict or str"
