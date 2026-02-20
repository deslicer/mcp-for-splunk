"""
Utilities for normalizing Splunk search job messages.

Splunk can return job.content["messages"] in multiple formats (dicts, strings, or mixed).
This module provides a small, reusable parser so tools can consistently extract errors
and present messages in a stable shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedJobMessages:
    """Normalized messages and extracted error texts."""

    messages: list[dict[str, str]]
    error_texts: list[str]


class JobMessageParser:
    """Normalize Splunk job messages and extract error texts."""

    @staticmethod
    def parse(messages: Any) -> ParsedJobMessages:
        normalized: list[dict[str, str]] = []
        errors: list[str] = []

        if not messages:
            return ParsedJobMessages(messages=[], error_texts=[])

        # Splunk commonly returns a list of dicts or strings; be tolerant of other shapes.
        if isinstance(messages, list):
            for item in messages:
                normalized_item = JobMessageParser._normalize_single_message(item)
                if normalized_item is None:
                    continue
                normalized.append(normalized_item)

                if normalized_item.get("type") == "ERROR":
                    text = normalized_item.get("text", "")
                    if text:
                        errors.append(text)
        else:
            normalized_item = JobMessageParser._normalize_single_message(messages)
            if normalized_item is not None:
                normalized.append(normalized_item)
                if normalized_item.get("type") == "ERROR":
                    text = normalized_item.get("text", "")
                    if text:
                        errors.append(text)

        return ParsedJobMessages(messages=normalized, error_texts=errors)

    @staticmethod
    def _normalize_single_message(item: Any) -> dict[str, str] | None:
        if item is None:
            return None

        # Dict format: {"type": "ERROR", "text": "..."} (or similar)
        if isinstance(item, dict):
            msg_type = str(item.get("type", "INFO")).upper()
            text_value = item.get("text")
            text = str(text_value) if text_value is not None else str(item)
            return {"type": msg_type, "text": text}

        # String format: treat as error per existing behavior in JobSearch
        if isinstance(item, str):
            text = item.strip()
            if not text:
                return None
            return {"type": "ERROR", "text": text}

        # Unknown type: keep it, but don't assume it's an error.
        return {"type": "INFO", "text": str(item)}
