from src.core.splunk_web_urls import SplunkWebLinks, resolve_splunk_web_base


def test_explicit_url_wins_and_strips_slash() -> None:
    base = resolve_splunk_web_base(
        explicit_web_url="https://splunk-b839c1.deslicer.io/",
        management_host="splunk-b839c1.deslicer.io",
        management_scheme="https",
    )
    assert base == "https://splunk-b839c1.deslicer.io"


def test_https_scheme_omits_port() -> None:
    base = resolve_splunk_web_base(
        explicit_web_url=None,
        management_host="splunk-b839c1.deslicer.io",
        management_scheme="https",
    )
    assert base == "https://splunk-b839c1.deslicer.io"


def test_http_scheme_uses_splunk_web_port() -> None:
    base = resolve_splunk_web_base(
        explicit_web_url=None,
        management_host="so1",
        management_scheme="http",
    )
    assert base == "http://so1:8000"


def test_https_never_appends_8000() -> None:
    base = resolve_splunk_web_base(
        explicit_web_url=None,
        management_host="so1",
        management_scheme="https",
        web_port=8000,
    )
    assert base == "https://so1"


def test_never_uses_management_port() -> None:
    base = resolve_splunk_web_base(
        explicit_web_url=None,
        management_host="search.example.com",
        management_scheme="https",
        management_port=8089,
        web_port=8089,
    )
    assert ":8089" not in base
    assert base == "https://search.example.com"


def test_job_and_dashboard_paths() -> None:
    links = SplunkWebLinks(base_url="https://splunk-b839c1.deslicer.io")
    sid = "scheduler__admin__search__RMD5ba17a0a9008ada7f_at_1788849600_3941"
    assert links.job_details(sid) == (
        "https://splunk-b839c1.deslicer.io/en-US/app/search/"
        f"job_details_dashboard?form.sid={sid}&tab=layout_1"
    )
    assert links.job_inspector(sid) == (
        f"https://splunk-b839c1.deslicer.io/en-US/manager/search/job_inspector?sid={sid}"
    )
    assert links.dashboard("search", "system_health") == (
        "https://splunk-b839c1.deslicer.io/en-US/app/search/system_health"
    )
