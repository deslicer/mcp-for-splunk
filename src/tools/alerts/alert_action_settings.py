"""Map structured alert-action payloads to Splunk saved-search fields."""

from __future__ import annotations

import json
from typing import Any

FLAT_BUILTIN_ACTIONS = frozenset(
    {
        "email",
        "rss",
        "script",
        "populate_lookup",
        "summary_index",
    }
)


class AlertActionSettings:
    """Convert MCP action lists into Splunk `action.*` saved-search fields."""

    def parse_actions(self, raw: Any) -> list[dict[str, Any]]:
        payload = self._load_payload(raw)
        parsed: list[dict[str, Any]] = []
        for index, item in enumerate(payload):
            parsed.append(self._parse_action_item(item, index))
        return parsed

    def splunk_fields(
        self,
        actions: list[dict[str, Any]],
        *,
        include_actions_csv: bool = True,
    ) -> dict[str, str]:
        fields: dict[str, str] = {}
        enabled_names: list[str] = []
        for item in actions:
            name = item["name"]
            enabled = bool(item.get("enabled", True))
            fields[f"action.{name}"] = "1" if enabled else "0"
            if enabled:
                enabled_names.append(name)
            fields.update(self._param_fields(name, item.get("params") or {}))
        if include_actions_csv:
            fields["actions"] = ",".join(enabled_names)
        return fields

    def enabled_names_from_content(self, content: dict[str, Any] | None) -> list[str]:
        source = content or {}
        names: list[str] = []
        seen: set[str] = set()
        csv_value = source.get("actions") or ""
        if isinstance(csv_value, str):
            for name in csv_value.split(","):
                cleaned = name.strip()
                if cleaned and cleaned not in seen:
                    names.append(cleaned)
                    seen.add(cleaned)
        for key, value in source.items():
            if not self._is_action_toggle_key(key) or not self._is_true(value):
                continue
            name = key.split(".", 1)[1]
            if name not in seen:
                names.append(name)
                seen.add(name)
        return names

    def patch_fields(
        self,
        current_content: dict[str, Any] | None,
        actions: list[dict[str, Any]],
    ) -> dict[str, str]:
        enabled = list(self.enabled_names_from_content(current_content))
        fields: dict[str, str] = {}
        for item in actions:
            name = item["name"]
            is_enabled = bool(item.get("enabled", True))
            fields[f"action.{name}"] = "1" if is_enabled else "0"
            enabled = self._adjust_enabled_names(enabled, name, is_enabled)
            fields.update(self._param_fields(name, item.get("params") or {}))
        fields["actions"] = ",".join(enabled)
        return fields

    def override_fields(
        self,
        current_content: dict[str, Any] | None,
        actions: list[dict[str, Any]],
    ) -> dict[str, str]:
        fields = self.splunk_fields(actions, include_actions_csv=True)
        new_enabled = {item["name"] for item in actions if item.get("enabled", True)}
        for name in self.enabled_names_from_content(current_content):
            if name not in new_enabled:
                fields[f"action.{name}"] = "0"
        return fields

    def param_field_name(self, action_name: str, key: str) -> str:
        if "." in key:
            return f"action.{action_name}.{key}"
        if action_name in FLAT_BUILTIN_ACTIONS:
            return f"action.{action_name}.{key}"
        return f"action.{action_name}.param.{key}"

    def _load_payload(self, raw: Any) -> list[Any]:
        if raw is None:
            return []
        if isinstance(raw, str):
            raw = json.loads(raw) if raw.strip() else []
        if not isinstance(raw, list):
            raise ValueError("actions must be a list of {name, params, enabled}")
        return raw

    def _parse_action_item(self, item: Any, index: int) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError(f"actions[{index}] must be an object with a name")
        name = str(item.get("name") or "").strip()
        if not name:
            raise ValueError(f"actions[{index}].name is required")
        params = item.get("params") or {}
        if isinstance(params, str):
            params = json.loads(params) if params.strip() else {}
        if not isinstance(params, dict):
            raise ValueError(f"actions[{index}].params must be an object")
        return {
            "name": name,
            "params": dict(params),
            "enabled": bool(item.get("enabled", True)),
        }

    def _param_fields(self, action_name: str, params: dict[str, Any]) -> dict[str, str]:
        return {
            self.param_field_name(action_name, str(key)): "" if value is None else str(value)
            for key, value in params.items()
        }

    def _adjust_enabled_names(
        self, enabled: list[str], name: str, is_enabled: bool
    ) -> list[str]:
        if is_enabled:
            if name not in enabled:
                enabled.append(name)
            return enabled
        return [existing for existing in enabled if existing != name]

    def _is_action_toggle_key(self, key: str) -> bool:
        return key.startswith("action.") and key.count(".") == 1

    def _is_true(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        if isinstance(value, int | float):
            return bool(value)
        return False
