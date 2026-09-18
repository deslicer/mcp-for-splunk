"""Splunk authentication completeness checks for local CLI setup."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SplunkAuthConfiguration:
    """Represent the Splunk settings required to skip interactive setup."""

    host: str = ""
    username: str = ""
    password: str = ""
    bearer_credential: str = ""

    @classmethod
    def from_env_values(cls, env_values: dict[str, str]) -> SplunkAuthConfiguration:
        return cls(
            host=env_values.get("SPLUNK_HOST", "").strip(),
            username=env_values.get("SPLUNK_USERNAME", "").strip(),
            password=env_values.get("SPLUNK_PASSWORD", "").strip(),
            bearer_credential=env_values.get("SPLUNK_TOKEN", "").strip(),
        )

    def is_complete(self) -> bool:
        has_basic_auth = bool(self.username and self.password)
        return bool(self.host and (has_basic_auth or self.bearer_credential))
