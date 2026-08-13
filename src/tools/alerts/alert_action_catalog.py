"""Discover installed Splunk alert actions via REST."""

from __future__ import annotations

import json
from typing import Any

SKIP_CONTENT_KEYS = frozenset(
    {
        "eai:acl",
        "eai:appName",
        "eai:userName",
        "disabled",
        "label",
        "description",
        "is_custom",
        "icon_path",
        "payload_format",
        "command",
        "python.version",
        "filename",
        "track_alert",
        "ttl",
        "maxtime",
        "maxresults",
    }
)


class AlertActionCatalog:
    """List alert actions installed on a connected Splunk instance."""

    def list_actions(self, service: Any) -> list[dict[str, Any]]:
        response = service.get("alerts/alert_actions", output_mode="json", count=0)
        payload = json.loads(response.body.read())
        actions: list[dict[str, Any]] = []
        for entry in payload.get("entry", []):
            content = entry.get("content") or {}
            acl = entry.get("acl") or {}
            actions.append(
                {
                    "name": entry.get("name", ""),
                    "label": content.get("label") or entry.get("name", ""),
                    "description": content.get("description", ""),
                    "is_custom": self._is_true(content.get("is_custom")),
                    "app": acl.get("app", ""),
                    "param_keys": self._param_keys(content),
                }
            )
        return actions

    def names(self, service: Any) -> set[str]:
        return {action["name"] for action in self.list_actions(service) if action.get("name")}

    def unknown_actions(self, service: Any, requested: list[str]) -> list[str]:
        available = self.names(service)
        return [name for name in requested if name not in available]

    def _param_keys(self, content: dict[str, Any]) -> list[str]:
        keys: list[str] = []
        for key in content:
            if key in SKIP_CONTENT_KEYS:
                continue
            if key.startswith("param.") or key.startswith("action."):
                keys.append(key)
        return sorted(keys)

    def _is_true(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        return False
