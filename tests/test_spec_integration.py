"""
Quick integration test to verify SplunkSpecReferenceResource registration.
"""

from src.core.registry import resource_registry
from src.resources.splunk_docs import create_spec_reference_resource


def main():
    """Test that spec reference resource is registered and functional."""
    print("Testing SplunkSpecReferenceResource integration...\n")

    # Test 1: Check resource is registered
    print("1. Checking resource registry...")
    all_resources = resource_registry.list_resources()
    spec_resources = [r for r in all_resources if "spec" in r.name.lower()]

    if spec_resources:
        print(f"   ✓ Found {len(spec_resources)} spec-related resource(s) in registry")
        for res in spec_resources:
            print(f"     - {res.name}: {res.uri}")
    else:
        print("   ✗ No spec resources found in registry")
        return False

    # Test 2: Create resource using factory
    print("\n2. Testing factory function...")
    try:
        resource = create_spec_reference_resource("10.0", "alert_actions.conf")
        print(f"   ✓ Created resource: {resource.name}")
        print(f"     URI: {resource.uri}")
        print(f"     Description: {resource.description}")
    except Exception as e:
        print(f"   ✗ Failed to create resource: {e}")
        return False

    # Test 3: Test version parsing
    print("\n3. Testing version parsing...")
    test_versions = [
        ("10.0", ("10.0", "10.0.0")),
        ("10.0.0", ("10.0", "10.0.0")),
        ("9.4.0", ("9.4", "9.4.0")),
        ("latest", ("10.0", "10.0.0")),
        ("auto", ("10.0", "10.0.0")),
    ]

    for version_input, expected in test_versions:
        resource = create_spec_reference_resource(version_input, "test.conf")
        minor, full = resource._parse_version_components(version_input)
        if (minor, full) == expected:
            print(f"   ✓ {version_input} -> minor={minor}, full={full}")
        else:
            print(f"   ✗ {version_input} -> Got ({minor}, {full}), expected {expected}")
            return False

    # Test 4: Test config name normalization
    print("\n4. Testing config name normalization...")
    test_configs = [
        ("alert_actions", "alert_actions.conf"),
        ("alert_actions.conf", "alert_actions.conf"),
        ("alert_actions.conf.spec", "alert_actions.conf"),
        ("limits", "limits.conf"),
    ]

    for config_input, expected in test_configs:
        resource = create_spec_reference_resource("10.0", config_input)
        normalized = resource._normalize_config_name(config_input)
        if normalized == expected:
            print(f"   ✓ {config_input} -> {normalized}")
        else:
            print(f"   ✗ {config_input} -> Got {normalized}, expected {expected}")
            return False

    # Test 5: Test URL construction
    print("\n5. Testing URL construction...")
    resource = create_spec_reference_resource("10.0", "alert_actions.conf")
    minor, full = resource._parse_version_components("10.0")
    config = resource._normalize_config_name("alert_actions.conf")

    expected_primary = (
        "https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/"
        "10.0/configuration-file-reference/10.0.0-configuration-file-reference/alert_actions.conf"
    )
    primary_url = f"{resource.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer/admin-manual/{minor}/configuration-file-reference/{full}-configuration-file-reference/{config}"

    if primary_url == expected_primary:
        print("   ✓ Primary URL constructed correctly")
        print(f"     {primary_url}")
    else:
        print("   ✗ URL mismatch")
        print(f"     Expected: {expected_primary}")
        print(f"     Got:      {primary_url}")
        return False

    print("\n✅ All integration tests passed!")
    print("\nExample URIs:")
    print("  - splunk-spec://10.0/alert_actions.conf")
    print("  - splunk-spec://latest/limits.conf")
    print("  - splunk-spec://9.4.0/inputs.conf")
    print("  - splunk-spec://auto/props.conf")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
