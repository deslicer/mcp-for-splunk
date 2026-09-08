from src.core.utils import extract_client_config_from_headers


def test_web_url_header_maps() -> None:
    cfg = extract_client_config_from_headers(
        {"X-Splunk-Web-Url": "https://splunk-b839c1.deslicer.io"}
    )
    assert cfg["splunk_web_url"] == "https://splunk-b839c1.deslicer.io"


def test_web_port_header_maps_to_int() -> None:
    cfg = extract_client_config_from_headers({"X-Splunk-Web-Port": "8443"})
    assert cfg["splunk_web_port"] == 8443
