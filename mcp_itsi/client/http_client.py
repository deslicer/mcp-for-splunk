"""Thin async HTTP client for the ITSI splunkd REST endpoints.

Responsibility (single):
    Translate an :class:`ITSIRequestConfig` plus a relative endpoint path into
    an authenticated HTTP request against the ITSI management port (8089) and
    return parsed JSON.

The client deliberately does **not** know about specific ITSI object types --
that domain knowledge lives in :mod:`mcp_itsi.client.endpoints`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from mcp_itsi.config.headers import ITSIRequestConfig

logger = logging.getLogger(__name__)


class ITSIError(RuntimeError):
    """Base error raised for non-2xx responses from the ITSI REST API."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class ITSINotFoundError(ITSIError):
    """Raised for 404 responses; useful for graceful UX in tools."""


class ITSIClient:
    """Lightweight, request-scoped client for the ITSI REST API.

    Usage::

        async with ITSIClient(cfg) as client:
            services = await client.get_json("/itoa_interface/service")
    """

    def __init__(self, cfg: ITSIRequestConfig, timeout: float = 30.0):
        self._cfg = cfg
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ITSIClient:
        self._client = httpx.AsyncClient(
            base_url=self._cfg.base_url,
            timeout=self._timeout,
            verify=self._cfg.verify_ssl,
            headers={"Accept": "application/json"},
            auth=self._build_auth(),
        )
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_auth(self) -> httpx.Auth | None:
        if self._cfg.splunk_token:
            return _BearerAuth(self._cfg.splunk_token)
        if self._cfg.splunk_username and self._cfg.splunk_password:
            return httpx.BasicAuth(self._cfg.splunk_username, self._cfg.splunk_password)
        return None

    def _build_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        if not path.startswith("/"):
            path = "/" + path
        if path.startswith("/servicesNS"):
            return path
        return f"{self._cfg.itsi_namespace}{path}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        data: Any = None,
    ) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("ITSIClient must be used as an async context manager")

        url = self._build_url(path)
        params = self._stringify_params(params)
        params.setdefault("output_mode", "json")

        logger.debug("ITSI %s %s params=%s", method, url, params)

        response = await self._client.request(
            method,
            url,
            params=params,
            json=json_body,
            data=data,
        )

        if response.status_code >= 400:
            self._raise_for_status(response)
        return response

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = await self.request("GET", path, params=params)
        return self._parse_json(resp)

    async def post_json(self, path: str, body: Any, params: dict[str, Any] | None = None) -> Any:
        resp = await self.request("POST", path, params=params, json_body=body)
        return self._parse_json(resp)

    async def delete(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = await self.request("DELETE", path, params=params)
        return {"status_code": resp.status_code}

    @staticmethod
    def _stringify_params(params: dict[str, Any] | None) -> dict[str, str]:
        if not params:
            return {}
        out: dict[str, str] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                out[key] = "1" if value else "0"
            elif isinstance(value, (dict, list)):
                out[key] = json.dumps(value)
            else:
                out[key] = str(value)
        return out

    @staticmethod
    def _parse_json(response: httpx.Response) -> Any:
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        body: Any
        try:
            body = response.json()
        except ValueError:
            body = response.text

        message = f"ITSI API {response.status_code} {response.reason_phrase}"
        if response.status_code == 404:
            raise ITSINotFoundError(message, response.status_code, body)
        raise ITSIError(message, response.status_code, body)


class _BearerAuth(httpx.Auth):
    def __init__(self, token: str):
        self._token = token

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request
