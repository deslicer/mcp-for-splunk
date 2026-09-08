"""Build Splunk Web UI URLs from the client scheme. Never emit https://host:8000."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote


def resolve_splunk_web_base(
    *,
    explicit_web_url: str | None,
    management_host: str,
    management_scheme: str = "https",
    management_port: int | None = None,
    web_port: int | None = None,
) -> str:
    if explicit_web_url:
        return explicit_web_url.rstrip("/")

    scheme = (management_scheme or "https").lower()
    host = management_host.split(":")[0]
    if web_port == 8089 or (management_port == 8089 and web_port is None):
        web_port = None

    if scheme == "https":
        if web_port and web_port not in (443, 8000, 8089):
            return f"https://{host}:{web_port}"
        return f"https://{host}"

    port = web_port if web_port and web_port != 8089 else 8000
    if port == 80:
        return f"http://{host}"
    return f"http://{host}:{port}"


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def web_links_from_service(
    service: object,
    client_config: dict[str, Any] | None = None,
) -> "SplunkWebLinks":
    config = client_config if isinstance(client_config, dict) else {}
    explicit = _optional_str(config.get("splunk_web_url"))
    locale = _optional_str(config.get("splunk_web_locale")) or "en-US"
    host = getattr(service, "host", "localhost")
    scheme = getattr(service, "scheme", "https")
    if not isinstance(host, str) or not host:
        host = "localhost"
    if not isinstance(scheme, str) or not scheme:
        scheme = "https"
    base = resolve_splunk_web_base(
        explicit_web_url=explicit,
        management_host=host,
        management_scheme=scheme,
        management_port=_optional_int(getattr(service, "port", None)),
        web_port=_optional_int(config.get("splunk_web_port")),
    )
    return SplunkWebLinks(base_url=base, locale=locale)


@dataclass(frozen=True)
class SplunkWebLinks:
    base_url: str
    locale: str = "en-US"

    def dashboard(self, app: str, name: str) -> str:
        return f"{self.base_url}/{self.locale}/app/{quote(app)}/{quote(name)}"

    def job_details(self, sid: str, app: str = "search") -> str:
        encoded = quote(sid, safe="")
        return (
            f"{self.base_url}/{self.locale}/app/{quote(app)}/"
            f"job_details_dashboard?form.sid={encoded}&tab=layout_1"
        )

    def job_inspector(self, sid: str, app: str = "search") -> str:
        encoded = quote(sid, safe="")
        return (
            f"{self.base_url}/{self.locale}/manager/{quote(app)}/"
            f"job_inspector?sid={encoded}"
        )

    def job_links(self, sid: str, app: str = "search") -> dict[str, str]:
        return {
            "job_id": sid,
            "job_details_url": self.job_details(sid, app),
            "job_inspector_url": self.job_inspector(sid, app),
        }
