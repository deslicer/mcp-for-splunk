import pytest

from src.resources.splunk_cim import CIMDataModelResource, SplunkCIMResource


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("authentication", "authentication"),
        ("Authentication", "authentication"),
        ("Change", "change"),
        ("Web", "web"),
        ("Network_Traffic", "network-traffic"),
        ("Network Sessions", "network-sessions"),
        ("network_resolution", "network-resolution"),
        ("Network Resolution (DNS)", "network-resolution"),
        ("Data Loss Prevention", "dlp"),
        ("JVM", "jvm"),
        ("Java Virtual Machines", "jvm"),
        ("Splunk_Audit", "splunk-audit"),
    ],
)
def test_resolve_model_key_accepts_common_spellings(given, expected):
    assert SplunkCIMResource.resolve_model_key(given) == expected


@pytest.mark.parametrize("given", ["", "not-a-model", "Authentications"])
def test_resolve_model_key_rejects_unknown(given):
    assert SplunkCIMResource.resolve_model_key(given) is None


def test_resource_uses_canonical_key_for_title_case_input():
    resource = CIMDataModelResource("latest", "Network_Traffic")
    assert resource.model == "network-traffic"
    assert resource.uri == "splunk-cim://latest/network-traffic"


def test_resource_still_rejects_unknown_model():
    with pytest.raises(ValueError, match="Unknown CIM data model"):
        CIMDataModelResource("latest", "Authentications")
