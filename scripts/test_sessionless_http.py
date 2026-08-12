#!/usr/bin/env python3
"""
Sessionless Streamable HTTP probe with Splunk bearer-token headers.

Starts nothing — point MCP_URL at a running server with:
  MCP_STATELESS_HTTP=true
  MCP_JSON_RESPONSE=true
  MCP_AUTH_DISABLED=true

Client credentials (headers only; never hard-coded):
  SPLUNK_HOST, SPLUNK_PORT, SPLUNK_SCHEME, SPLUNK_VERIFY_SSL
  and SPLUNK_TOKEN (required for this probe)

Intentionally omits X-Session-ID / MCP-Session-ID so the identity-hash /
per-request header path is exercised.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@dataclass
class ProbeResult:
    name: str
    outcome: str
    detail: str = ""
    elapsed_ms: int = 0


class SessionlessHeaderBuilder:
    """Build Splunk HTTP headers for sessionless token auth."""

    def build(self) -> dict[str, str]:
        host = os.environ.get("SPLUNK_HOST", "").strip()
        token = os.environ.get("SPLUNK_TOKEN", "").strip()
        if not host:
            raise SystemExit("SPLUNK_HOST is required")
        if not token:
            raise SystemExit("SPLUNK_TOKEN is required for the sessionless token probe")

        headers = {
            "X-Splunk-Host": host,
            "X-Splunk-Port": os.environ.get("SPLUNK_PORT", "8089").strip() or "8089",
            "X-Splunk-Scheme": os.environ.get("SPLUNK_SCHEME", "https").strip() or "https",
            "X-Splunk-Verify-SSL": os.environ.get("SPLUNK_VERIFY_SSL", "false").strip()
            or "false",
            "X-Splunk-Token": token,
        }
        # Optional username is fine; password must stay unset for token-only.
        username = os.environ.get("SPLUNK_USERNAME", "").strip()
        if username:
            headers["X-Splunk-Username"] = username
        return headers


class SessionlessHttpProbe:
    """Exercise FastMCP Client over Streamable HTTP without session sticky ids."""

    def __init__(self, url: str, headers: dict[str, str]) -> None:
        self._url = url
        self._headers = headers

    def _extract(self, result: Any) -> Any:
        if getattr(result, "data", None) is not None:
            return result.data
        if getattr(result, "structured_content", None) is not None:
            return result.structured_content
        texts = [
            getattr(c, "text", None)
            for c in (getattr(result, "content", None) or [])
            if getattr(c, "text", None)
        ]
        if not texts:
            return None
        try:
            return json.loads(texts[0])
        except Exception:
            return texts[0]

    async def _call(self, client: Any, name: str, args: dict[str, Any]) -> ProbeResult:
        started = time.perf_counter()
        try:
            raw = await client.call_tool(name, args)
            payload = self._extract(raw)
            is_error = bool(getattr(raw, "is_error", False) or getattr(raw, "isError", False))
            ms = int((time.perf_counter() - started) * 1000)
            if is_error:
                return ProbeResult(name, "FAIL", str(payload)[:200], ms)
            if isinstance(payload, dict) and payload.get("status") == "error":
                return ProbeResult(
                    name,
                    "FAIL",
                    str(payload.get("error") or payload.get("message") or payload)[:200],
                    ms,
                )
            detail = ""
            if isinstance(payload, dict):
                detail = str(payload.get("status") or "ok")
            return ProbeResult(name, "PASS", detail, ms)
        except Exception as exc:  # pylint: disable=broad-except
            return ProbeResult(name, "FAIL", str(exc)[:240], int((time.perf_counter() - started) * 1000))

    async def run(self) -> int:
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport

        assert "X-Session-ID" not in self._headers
        assert "MCP-Session-ID" not in self._headers
        assert "X-Splunk-Token" in self._headers
        assert "X-Splunk-Password" not in self._headers

        transport = StreamableHttpTransport(url=self._url, headers=self._headers)
        results: list[ProbeResult] = []

        print(f"Sessionless HTTP probe → {self._url}")
        print("Headers: X-Splunk-Host/Port/Scheme/Verify-SSL + X-Splunk-Token (no session ids)")

        async with Client(transport) as client:
            started = time.perf_counter()
            tools = await client.list_tools()
            results.append(
                ProbeResult(
                    "list_tools",
                    "PASS" if tools else "FAIL",
                    f"count={len(tools)}",
                    int((time.perf_counter() - started) * 1000),
                )
            )

            plan = [
                ("get_splunk_health", {}),
                ("me", {}),
                ("list_indexes", {}),
                ("user_agent_info", {}),
                ("list_saved_searches", {"include_disabled": True}),
                ("run_oneshot_search", {
                    "query": "index=_internal | head 1",
                    "earliest_time": "-15m",
                    "latest_time": "now",
                    "max_results": 1,
                }),
                # Second health call proves sessionless reuse without sticky MCP session.
                ("get_splunk_health", {}),
            ]
            for name, args in plan:
                print(f"  -> {name}...", flush=True)
                run = await self._call(client, name, args)
                if name == "get_splunk_health" and results and results[-1].name == "get_splunk_health":
                    run.name = "get_splunk_health(repeat)"
                results.append(run)
                print(f"     [{run.outcome}] {run.detail} ({run.elapsed_ms}ms)")

        print("\n" + "=" * 64)
        print("SESSIONLESS HTTP + TOKEN SUMMARY")
        print("=" * 64)
        passed = [r for r in results if r.outcome == "PASS"]
        failed = [r for r in results if r.outcome == "FAIL"]
        print(f"PASS: {len(passed)}  FAIL: {len(failed)}  TOTAL: {len(results)}")
        for run in results:
            line = f"[{run.outcome:4}] {run.name} ({run.elapsed_ms}ms)"
            if run.detail:
                line += f" — {run.detail}"
            print(line)
        return 1 if failed else 0


async def _amain() -> int:
    url = os.environ.get("MCP_URL", "http://127.0.0.1:8014/mcp").strip()
    headers = SessionlessHeaderBuilder().build()
    return await SessionlessHttpProbe(url, headers).run()


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
