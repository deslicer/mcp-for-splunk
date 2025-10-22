"""
Splunk Common Information Model (CIM) resources for MCP server.

Provides access to CIM data model documentation for data normalization and onboarding.
"""

import logging
from datetime import datetime

from fastmcp import Context

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from src.core.base import BaseResource, ResourceMetadata
from src.core.registry import resource_registry

from .processors.html_processor import SplunkDocsProcessor
from .splunk_docs import _doc_cache

logger = logging.getLogger(__name__)


class SplunkCIMResource(BaseResource):
    """Base class for Splunk CIM resources."""

    SPLUNK_HELP_BASE = "https://help.splunk.com"
    CIM_VERSION_MAPPING = {
        "6.1": "6.1",
        "6.0": "6.0",
        "5.3": "5.3",
        "5.2": "5.2",
        "5.1": "5.1",
        "latest": "6.1",  # Current latest CIM version
    }

    # All 26 CIM data models with their metadata
    CIM_DATA_MODELS = {
        "alerts": {
            "name": "Alerts",
            "description": "Alert notifications from security and monitoring systems",
            "url_slug": "alerts",
            "use_case": "Use for alert/notification events from IDS, SIEM, monitoring tools",
            "tags": ["alert"],
            "deprecated": False,
        },
        "application-state": {
            "name": "Application State",
            "description": "Application availability and state changes (deprecated)",
            "url_slug": "application-state",
            "use_case": "Use for application availability monitoring (deprecated in 6.0+)",
            "tags": ["application", "state"],
            "deprecated": True,
        },
        "authentication": {
            "name": "Authentication",
            "description": "User authentication events (logins, logouts, failures)",
            "url_slug": "authentication",
            "use_case": "Use for login/logout events, authentication failures, access attempts",
            "tags": ["authentication"],
            "deprecated": False,
        },
        "certificates": {
            "name": "Certificates",
            "description": "SSL/TLS certificate information and events",
            "url_slug": "certificates",
            "use_case": "Use for SSL certificate validation, expiration, and deployment events",
            "tags": ["certificate"],
            "deprecated": False,
        },
        "change": {
            "name": "Change",
            "description": "Configuration and system changes",
            "url_slug": "change",
            "use_case": "Use for system changes, configuration modifications, auditing",
            "tags": ["change"],
            "deprecated": False,
        },
        "change-analysis": {
            "name": "Change Analysis",
            "description": "Change tracking and analysis (deprecated)",
            "url_slug": "change-analysis",
            "use_case": "Use for change tracking (deprecated in 6.0+)",
            "tags": ["change"],
            "deprecated": True,
        },
        "data-access": {
            "name": "Data Access",
            "description": "Data access events (file access, database queries)",
            "url_slug": "data-access",
            "use_case": "Use for file access, database queries, data read/write events",
            "tags": ["data", "access"],
            "deprecated": False,
        },
        "databases": {
            "name": "Databases",
            "description": "Database operations and queries",
            "url_slug": "databases",
            "use_case": "Use for database query logs, performance metrics, operations",
            "tags": ["database"],
            "deprecated": False,
        },
        "dlp": {
            "name": "Data Loss Prevention",
            "description": "DLP incidents and policy violations",
            "url_slug": "data-loss-prevention",
            "url_slug_alt": "dlp",
            "use_case": "Use for data leakage events, policy violations, sensitive data alerts",
            "tags": ["dlp"],
            "deprecated": False,
        },
        "email": {
            "name": "Email",
            "description": "Email message tracking and delivery",
            "url_slug": "email",
            "use_case": "Use for email logs, delivery tracking, spam/phishing events",
            "tags": ["email"],
            "deprecated": False,
        },
        "endpoint": {
            "name": "Endpoint",
            "description": "Endpoint security events (processes, services, registry)",
            "url_slug": "endpoint",
            "use_case": "Use for endpoint protection, process monitoring, system events",
            "tags": ["endpoint"],
            "deprecated": False,
        },
        "event-signatures": {
            "name": "Event Signatures",
            "description": "Security event signatures and rules",
            "url_slug": "event-signatures",
            "use_case": "Use for IDS/IPS signatures, correlation rules, detection patterns",
            "tags": ["signature"],
            "deprecated": False,
        },
        "interprocess-messaging": {
            "name": "Interprocess Messaging",
            "description": "Inter-process communication and messaging",
            "url_slug": "interprocess-messaging",
            "use_case": "Use for message queue events, IPC logs, pub/sub systems",
            "tags": ["messaging"],
            "deprecated": False,
        },
        "intrusion-detection": {
            "name": "Intrusion Detection",
            "description": "IDS/IPS alerts and network intrusion events",
            "url_slug": "intrusion-detection",
            "use_case": "Use for IDS/IPS alerts, network intrusion events, threat detection",
            "tags": ["ids", "ips"],
            "deprecated": False,
        },
        "inventory": {
            "name": "Inventory",
            "description": "Asset and system inventory information",
            "url_slug": "inventory",
            "use_case": "Use for asset inventory, system information, configuration items",
            "tags": ["inventory"],
            "deprecated": False,
        },
        "jvm": {
            "name": "Java Virtual Machines",
            "description": "JVM performance and operational metrics",
            "url_slug": "java-virtual-machines-jvm",
            "url_slug_alt": "jvm",
            "use_case": "Use for JVM monitoring, garbage collection, thread metrics",
            "tags": ["jvm"],
            "deprecated": False,
        },
        "malware": {
            "name": "Malware",
            "description": "Malware detection and prevention events",
            "url_slug": "malware",
            "use_case": "Use for antivirus alerts, malware detection, quarantine events",
            "tags": ["malware"],
            "deprecated": False,
        },
        "network-resolution": {
            "name": "Network Resolution (DNS)",
            "description": "DNS queries and resolution events",
            "url_slug": "network-resolution-dns",
            "url_slug_alt": "network-resolution",
            "use_case": "Use for DNS query logs, resolution failures, DHCP events",
            "tags": ["dns", "network", "resolution"],
            "deprecated": False,
        },
        "network-sessions": {
            "name": "Network Sessions",
            "description": "Network session and connection tracking",
            "url_slug": "network-sessions",
            "use_case": "Use for network session logs, connection tracking, NAT events",
            "tags": ["network", "session"],
            "deprecated": False,
        },
        "network-traffic": {
            "name": "Network Traffic",
            "description": "Network packet and traffic data",
            "url_slug": "network-traffic",
            "use_case": "Use for network flow data, firewall logs, packet captures",
            "tags": ["network", "traffic"],
            "deprecated": False,
        },
        "performance": {
            "name": "Performance",
            "description": "System and application performance metrics",
            "url_slug": "performance",
            "use_case": "Use for CPU, memory, disk I/O, and application performance data",
            "tags": ["performance"],
            "deprecated": False,
        },
        "splunk-audit": {
            "name": "Splunk Audit Logs",
            "description": "Splunk internal audit events",
            "url_slug": "splunk-audit-logs",
            "url_slug_alt": "splunk-audit",
            "use_case": "Use for Splunk configuration changes, user actions, system events",
            "tags": ["audit"],
            "deprecated": False,
        },
        "ticket-management": {
            "name": "Ticket Management",
            "description": "IT ticketing and incident tracking",
            "url_slug": "ticket-management",
            "use_case": "Use for help desk tickets, incident management, change requests",
            "tags": ["ticket"],
            "deprecated": False,
        },
        "updates": {
            "name": "Updates",
            "description": "System and software update events",
            "url_slug": "updates",
            "use_case": "Use for patch management, software updates, system upgrades",
            "tags": ["update"],
            "deprecated": False,
        },
        "vulnerabilities": {
            "name": "Vulnerabilities",
            "description": "Vulnerability scan results and assessments",
            "url_slug": "vulnerabilities",
            "use_case": "Use for vulnerability scan data, risk assessments, CVE tracking",
            "tags": ["vulnerability"],
            "deprecated": False,
        },
        "web": {
            "name": "Web",
            "description": "Web server logs and HTTP traffic",
            "url_slug": "web",
            "use_case": "Use for web server logs, HTTP requests, proxy logs",
            "tags": ["web"],
            "deprecated": False,
        },
    }

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "text/markdown"):
        super().__init__(uri, name, description, mime_type)
        self.processor = SplunkDocsProcessor()

    def normalize_cim_version(self, version: str) -> str:
        """Convert version to CIM docs URL format."""
        # Handle auto-detection or missing version
        if not version or version == "auto":
            version = "latest"

        return self.CIM_VERSION_MAPPING.get(version, self.CIM_VERSION_MAPPING["latest"])

    def format_cim_url(self, version: str, model_slug: str) -> str:
        """Format URL for CIM data model documentation.

        Args:
            version: CIM version (e.g., "6.1", "latest")
            model_slug: URL slug for the data model

        Returns:
            Complete URL to the data model documentation
        """
        norm_version = self.normalize_cim_version(version)
        return f"{self.SPLUNK_HELP_BASE}/en/data-management/common-information-model/{norm_version}/data-models/{model_slug}"

    async def fetch_cim_content(self, url: str) -> str:
        """Fetch and process CIM documentation content."""
        if not HAS_HTTPX:
            return f"""# Documentation Unavailable

HTTP client not available. To enable CIM documentation fetching, install httpx:

```bash
pip install httpx
```

**Requested URL**: {url}
**Time**: {datetime.now().isoformat()}
"""

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            async with httpx.AsyncClient(
                timeout=30.0, headers=headers, follow_redirects=True
            ) as client:
                logger.debug("Fetching CIM documentation from: %s", url)
                response = await client.get(url)
                response.raise_for_status()

                content = self.processor.process_html(response.text, url)
                logger.debug("Successfully processed CIM documentation from %s", url)
                return content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"""# CIM Documentation Not Found

The requested CIM data model documentation was not found.

**URL**: {url}
**Status**: 404 Not Found
**Time**: {datetime.now().isoformat()}

This may indicate:
- The data model name is incorrect
- This CIM version doesn't include this data model
- The documentation has moved

Available data models: {", ".join(self.CIM_DATA_MODELS.keys())}

Please check the [CIM Discovery Resource](splunk-cim://discovery) for available models.
"""
            else:
                return f"""# CIM Documentation Error

Failed to fetch CIM documentation due to HTTP error.

**URL**: {url}
**Status**: {e.response.status_code}
**Error**: {str(e)}
**Time**: {datetime.now().isoformat()}
"""
        except Exception as e:
            logger.error("Error fetching CIM documentation from %s: %s", url, str(e))
            return f"""# CIM Documentation Error

Failed to fetch CIM documentation due to an error.

**URL**: {url}
**Error**: {str(e)}
**Time**: {datetime.now().isoformat()}

Please check your internet connection and try again.
"""


class CIMDiscoveryResource(SplunkCIMResource):
    """Discovery resource listing all CIM data models."""

    METADATA = ResourceMetadata(
        uri="splunk-cim://discovery",
        name="cim_discovery",
        description="Discover available Splunk CIM data models for data normalization",
        mime_type="text/markdown",
        category="discovery",
        tags=["cim", "discovery", "data-model", "normalization"],
    )

    def __init__(
        self,
        uri: str = None,
        name: str = None,
        description: str = None,
        mime_type: str = "text/markdown",
    ):
        uri = uri or self.METADATA.uri
        name = name or self.METADATA.name
        description = description or self.METADATA.description
        super().__init__(uri, name, description, mime_type)

    async def get_content(self, ctx: Context) -> str:
        """Get CIM discovery content listing all data models."""

        content = f"""# Splunk Common Information Model (CIM) Discovery

**CIM Version**: 6.1 (latest)
**Generated**: {datetime.now().isoformat()}

The Splunk Common Information Model (CIM) provides a standardized way to normalize data from different sources, making it easier to correlate events and create consistent searches across diverse data types.

## What is the CIM?

The CIM is a shared semantic model that:
- **Normalizes data** from different vendors/products to common field names
- **Tags events** to identify them as belonging to specific data models
- **Standardizes searches** across different data sources
- **Enables pre-built content** like Enterprise Security correlation searches

## How to Use This Resource

1. **Identify your data type** - What kind of events are you working with?
2. **Choose the appropriate data model** - Match your data to one or more models below
3. **Access the model details** - Use the URI pattern `splunk-cim://{{model}}` or `splunk-cim://{{version}}/{{model}}`
4. **Tag and normalize** - Follow the field mappings and tagging guidance

---

## Available Data Models

### 🔐 Security Data Models

#### Authentication
**URI**: `splunk-cim://authentication`
**Use Case**: {self.CIM_DATA_MODELS["authentication"]["use_case"]}
**Tags Required**: `authentication`
**Common Sources**: Active Directory, Unix/Linux auth logs, VPN logs, web authentication

#### Intrusion Detection
**URI**: `splunk-cim://intrusion-detection`
**Use Case**: {self.CIM_DATA_MODELS["intrusion-detection"]["use_case"]}
**Tags Required**: `ids`, `ips`
**Common Sources**: Snort, Suricata, Palo Alto, Cisco Firepower

#### Malware
**URI**: `splunk-cim://malware`
**Use Case**: {self.CIM_DATA_MODELS["malware"]["use_case"]}
**Tags Required**: `malware`
**Common Sources**: Antivirus systems, EDR platforms, sandbox analysis

#### Endpoint
**URI**: `splunk-cim://endpoint`
**Use Case**: {self.CIM_DATA_MODELS["endpoint"]["use_case"]}
**Tags Required**: `endpoint`
**Common Sources**: Sysmon, Carbon Black, CrowdStrike, Windows Event Logs

#### Data Access
**URI**: `splunk-cim://data-access`
**Use Case**: {self.CIM_DATA_MODELS["data-access"]["use_case"]}
**Tags Required**: `data`, `access`
**Common Sources**: File system logs, database audit logs, cloud storage logs

#### Data Loss Prevention
**URI**: `splunk-cim://dlp`
**Use Case**: {self.CIM_DATA_MODELS["dlp"]["use_case"]}
**Tags Required**: `dlp`
**Common Sources**: DLP systems, email gateways, cloud access security brokers

#### Vulnerabilities
**URI**: `splunk-cim://vulnerabilities`
**Use Case**: {self.CIM_DATA_MODELS["vulnerabilities"]["use_case"]}
**Tags Required**: `vulnerability`
**Common Sources**: Nessus, Qualys, Rapid7, OpenVAS

#### Change
**URI**: `splunk-cim://change`
**Use Case**: {self.CIM_DATA_MODELS["change"]["use_case"]}
**Tags Required**: `change`
**Common Sources**: Configuration management tools, audit logs, version control

### 🌐 Network Data Models

#### Network Traffic
**URI**: `splunk-cim://network-traffic`
**Use Case**: {self.CIM_DATA_MODELS["network-traffic"]["use_case"]}
**Tags Required**: `network`, `traffic`
**Common Sources**: Firewall logs, NetFlow/IPFIX, packet captures, proxy logs

#### Network Sessions
**URI**: `splunk-cim://network-sessions`
**Use Case**: {self.CIM_DATA_MODELS["network-sessions"]["use_case"]}
**Tags Required**: `network`, `session`
**Common Sources**: NAT logs, load balancer logs, session state tables

#### Network Resolution (DNS)
**URI**: `splunk-cim://network-resolution`
**Use Case**: {self.CIM_DATA_MODELS["network-resolution"]["use_case"]}
**Tags Required**: `dns`, `network`, `resolution`
**Common Sources**: DNS servers, DHCP servers, name resolution logs

### 📊 Application & System Data Models

#### Web
**URI**: `splunk-cim://web`
**Use Case**: {self.CIM_DATA_MODELS["web"]["use_case"]}
**Tags Required**: `web`
**Common Sources**: Apache, Nginx, IIS, proxy servers, CDN logs

#### Email
**URI**: `splunk-cim://email`
**Use Case**: {self.CIM_DATA_MODELS["email"]["use_case"]}
**Tags Required**: `email`
**Common Sources**: Exchange, Sendmail, Postfix, email gateways

#### Databases
**URI**: `splunk-cim://databases`
**Use Case**: {self.CIM_DATA_MODELS["databases"]["use_case"]}
**Tags Required**: `database`
**Common Sources**: MySQL, PostgreSQL, Oracle, SQL Server audit logs

#### Performance
**URI**: `splunk-cim://performance`
**Use Case**: {self.CIM_DATA_MODELS["performance"]["use_case"]}
**Tags Required**: `performance`
**Common Sources**: OS metrics, APM tools, infrastructure monitoring

#### JVM (Java Virtual Machines)
**URI**: `splunk-cim://jvm`
**Use Case**: {self.CIM_DATA_MODELS["jvm"]["use_case"]}
**Tags Required**: `jvm`
**Common Sources**: Java application logs, JMX metrics, garbage collection logs

### 🔔 Alerting & Management Data Models

#### Alerts
**URI**: `splunk-cim://alerts`
**Use Case**: {self.CIM_DATA_MODELS["alerts"]["use_case"]}
**Tags Required**: `alert`
**Common Sources**: SIEM systems, monitoring tools, security appliances

#### Ticket Management
**URI**: `splunk-cim://ticket-management`
**Use Case**: {self.CIM_DATA_MODELS["ticket-management"]["use_case"]}
**Tags Required**: `ticket`
**Common Sources**: ServiceNow, Jira, Remedy, help desk systems

#### Updates
**URI**: `splunk-cim://updates`
**Use Case**: {self.CIM_DATA_MODELS["updates"]["use_case"]}
**Tags Required**: `update`
**Common Sources**: WSUS, patch management systems, software deployment tools

### 📦 Infrastructure & Asset Data Models

#### Inventory
**URI**: `splunk-cim://inventory`
**Use Case**: {self.CIM_DATA_MODELS["inventory"]["use_case"]}
**Tags Required**: `inventory`
**Common Sources**: Asset management systems, CMDB, discovery scans

#### Certificates
**URI**: `splunk-cim://certificates`
**Use Case**: {self.CIM_DATA_MODELS["certificates"]["use_case"]}
**Tags Required**: `certificate`
**Common Sources**: Certificate authorities, SSL/TLS logs, certificate managers

### 🔍 Monitoring & Detection Data Models

#### Event Signatures
**URI**: `splunk-cim://event-signatures`
**Use Case**: {self.CIM_DATA_MODELS["event-signatures"]["use_case"]}
**Tags Required**: `signature`
**Common Sources**: IDS/IPS systems, correlation rules, detection frameworks

#### Interprocess Messaging
**URI**: `splunk-cim://interprocess-messaging`
**Use Case**: {self.CIM_DATA_MODELS["interprocess-messaging"]["use_case"]}
**Tags Required**: `messaging`
**Common Sources**: Message queues, pub/sub systems, event buses

### 🔧 Splunk Internal Data Models

#### Splunk Audit Logs
**URI**: `splunk-cim://splunk-audit`
**Use Case**: {self.CIM_DATA_MODELS["splunk-audit"]["use_case"]}
**Tags Required**: `audit`
**Common Sources**: Splunk internal logs (_audit, _internal indexes)

---

## Deprecated Data Models

The following models are deprecated in CIM 6.0+ and should not be used for new implementations:

- **Application State** (use Endpoint or Performance instead)
- **Change Analysis** (use Change instead)

---

## Decision Guide: Which Data Model to Use?

### I have authentication logs (logins/logouts)
→ Use **Authentication** model

### I have firewall or network flow data
→ Use **Network Traffic** model

### I have IDS/IPS alerts
→ Use **Intrusion Detection** model

### I have antivirus or EDR events
→ Use **Malware** and/or **Endpoint** models

### I have web server logs
→ Use **Web** model

### I have DNS query logs
→ Use **Network Resolution** model

### I have email logs
→ Use **Email** model

### I have vulnerability scan results
→ Use **Vulnerabilities** model

### I have system performance metrics
→ Use **Performance** model

### I have file access or database audit logs
→ Use **Data Access** model

### I have DLP alerts
→ Use **Data Loss Prevention** model

---

## Using CIM Resources

### Access a Specific Data Model

```
# Latest version (default)
splunk-cim://authentication

# Explicit latest version
splunk-cim://latest/authentication

# Specific version
splunk-cim://6.0/authentication
```

### Typical Workflow

1. **Read the model documentation**: Access via `splunk-cim://{{model}}`
2. **Identify required fields and tags**: Note which fields are required vs recommended
3. **Create event types and tags**: Define tags.conf and eventtypes.conf
4. **Map fields**: Use FIELDALIAS, EVAL, or transforms in props.conf
5. **Test your mappings**: Run searches to validate normalization
6. **Use CIM-compatible searches**: Leverage pre-built content

---

## Version Support

- **Latest**: 6.1 (default when version not specified)
- **Supported**: 6.1, 6.0, 5.3, 5.2, 5.1

---

## Additional Resources

- [CIM Documentation](https://help.splunk.com/en/data-management/common-information-model/6.1)
- [Splunk Add-on Builder](splunk-docs://latest/admin/addon-builder) - Tool for creating CIM-compliant add-ons
- [Props.conf Reference](splunk-spec://props.conf) - Field extraction and transformation
- [Transforms.conf Reference](splunk-spec://transforms.conf) - Advanced field transformations
- [Tags.conf Reference](splunk-spec://tags.conf) - Event tagging configuration

---

**Need help with a specific data model?** Access detailed documentation using the URIs listed above!
"""

        return content


class CIMDataModelResource(SplunkCIMResource):
    """Template resource for individual CIM data models."""

    METADATA = ResourceMetadata(
        uri="splunk-cim://{version}/{model}",
        name="cim_data_model",
        description="Splunk CIM data model documentation with field specifications and configuration examples",
        mime_type="text/markdown",
        category="reference",
        tags=["cim", "data-model", "normalization", "fields"],
    )

    def __init__(self, version: str, model: str):
        self.version = version if version else "latest"
        self.model = model

        if model not in self.CIM_DATA_MODELS:
            available_models = ", ".join(sorted(self.CIM_DATA_MODELS.keys()))
            raise ValueError(
                f"Unknown CIM data model: {model}. Available models: {available_models}"
            )

        model_info = self.CIM_DATA_MODELS[model]
        uri = f"splunk-cim://{self.version}/{model}"

        super().__init__(
            uri=uri,
            name=f"cim_{model.replace('-', '_')}_{self.version}",
            description=f"CIM {model_info['name']} data model: {model_info['description']} (version {self.version})",
        )

    async def get_content(self, ctx: Context) -> str:
        """Get CIM data model documentation with field specs and examples."""

        async def fetch_model_docs():
            model_info = self.CIM_DATA_MODELS[self.model]
            norm_version = self.normalize_cim_version(self.version)

            # Try primary URL slug first
            url_slug = model_info["url_slug"]
            url = self.format_cim_url(norm_version, url_slug)
            content = await self.fetch_cim_content(url)

            # If primary fails and there's an alternative slug, try it
            if content.startswith("# CIM Documentation Not Found") and "url_slug_alt" in model_info:
                alt_slug = model_info["url_slug_alt"]
                logger.debug("Trying alternative URL slug: %s", alt_slug)
                url = self.format_cim_url(norm_version, alt_slug)
                content = await self.fetch_cim_content(url)

            # Build comprehensive documentation
            deprecation_notice = ""
            if model_info.get("deprecated", False):
                deprecation_notice = """
## ⚠️ Deprecation Notice

**This data model is deprecated** in CIM 6.0 and later versions. It is included for backward compatibility but should not be used for new implementations. Please consult the CIM documentation for recommended alternatives.

"""

            result = f"""# CIM Data Model: {model_info["name"]}

**Version**: CIM {self.version}
**Category**: Common Information Model
**Status**: {"Deprecated" if model_info.get("deprecated") else "Active"}
**Tags Required**: {", ".join(f"`{tag}`" for tag in model_info["tags"])}

{deprecation_notice}

## Overview

{model_info["description"]}

**{model_info["use_case"]}**

### When to Use This Model

{self._generate_use_case_guidance(self.model, model_info)}

---

## Documentation Content

{content}

---

## Configuration Guide

### Step 1: Define Event Types

Event types identify which events belong to this data model. Create event type definitions that match your data source.

**File**: `eventtypes.conf`

```conf
# Example event type for {model_info["name"]}
[{self.model.replace("-", "_")}_events]
search = sourcetype=your_sourcetype_here
# Add more specific search criteria as needed
```

### Step 2: Tag Events

Tags associate events with CIM data models. Apply the required tags for this model.

**File**: `tags.conf`

```conf
# Tag the event type with required tags
[eventtype={self.model.replace("-", "_")}_events]
{self._generate_tag_config(model_info["tags"])}
```

### Step 3: Normalize Fields

Map your vendor-specific fields to CIM field names using field aliases, extractions, or evaluations.

**File**: `props.conf`

```conf
[your_sourcetype_here]
# Field aliases (rename existing fields)
# FIELDALIAS-alias_name = vendor_field AS cim_field

# Field extractions (extract new fields)
# EXTRACT-field_name = regex_pattern

# Field evaluations (compute fields)
# EVAL-cim_field = if(condition, value1, value2)

{self._generate_example_field_mappings(self.model)}
```

### Step 4: Advanced Transformations (Optional)

For complex mappings, use transforms.conf for lookup-based field enrichment.

**File**: `transforms.conf`

```conf
# Example lookup-based field transformation
[{self.model}_field_lookup]
filename = {self.model}_mappings.csv
# Define lookup fields and transformations
```

---

## Testing Your Configuration

### Validate Tagging

```spl
# Check if events are properly tagged
tag={model_info["tags"][0]} earliest=-1h
| stats count by sourcetype tag
```

### Verify Field Normalization

```spl
# Check field presence and values
tag={model_info["tags"][0]} earliest=-1h
| table _time sourcetype {self._generate_common_fields_list(self.model)}
| head 100
```

### CIM Validation

```spl
# Use the CIM validation searches included with Enterprise Security or the CIM Add-on
# These searches check field coverage and data quality
```

---

## Common Field Categories

CIM fields are categorized as:

- **Required**: Must be present for events to be valid
- **Recommended**: Should be present for full functionality
- **Optional**: Provide additional context when available

Consult the detailed field tables in the documentation content above for specifics.

---

## Best Practices

### Field Mapping Strategy

1. **Use FIELDALIAS** for simple field renames (most efficient)
2. **Use EVAL** for computed fields and conditional logic
3. **Use EXTRACT** for parsing unstructured data
4. **Use transforms lookups** for complex mappings or enrichment

### Data Quality

- **Consistency**: Ensure field values use consistent formats across sources
- **Completeness**: Populate as many recommended fields as possible
- **Validation**: Test field mappings with real data samples
- **Documentation**: Document your field mappings for maintenance

### Performance

- **Index-time vs Search-time**: Prefer search-time field extractions for flexibility
- **Field extraction efficiency**: Use specific regex patterns, avoid wildcards
- **Accelerated data models**: Enable acceleration for frequently-searched models

---

## Related Data Models

{self._generate_related_models(self.model)}

---

## Additional Resources

- [CIM Discovery Resource](splunk-cim://discovery) - Browse all available data models
- [Props.conf Specification](splunk-spec://props.conf) - Field extraction reference
- [Transforms.conf Specification](splunk-spec://transforms.conf) - Advanced transformations
- [Tags.conf Specification](splunk-spec://tags.conf) - Event tagging reference
- [CIM Documentation](https://help.splunk.com/en/data-management/common-information-model/{norm_version})

---

**Generated**: {datetime.now().isoformat()}
**Source URL**: {url}
"""

            return result

        return await _doc_cache.get_or_fetch(self.version, "cim", self.model, fetch_model_docs)

    def _generate_use_case_guidance(self, model: str, model_info: dict) -> str:
        """Generate contextual guidance for when to use this data model."""
        guidance_map = {
            "authentication": "Use this model when you have logs showing user login/logout activity, authentication attempts, or access control events from systems like Active Directory, LDAP, SSO platforms, or application authentication logs.",
            "network-traffic": "Use this model for any data showing network communication: firewall permits/denies, NetFlow/sFlow data, packet captures, or any logs containing source/destination IP addresses and ports.",
            "intrusion-detection": "Use this model for security alerts from IDS/IPS systems, network threat detection platforms, or signature-based detection tools that identify potential attacks or policy violations.",
            "malware": "Use this model for antivirus alerts, endpoint detection responses, sandbox analysis results, or any events indicating malicious software detection or quarantine.",
            "endpoint": "Use this model for endpoint security events including process execution, service changes, registry modifications, file system changes, and other system-level activity on workstations or servers.",
            "web": "Use this model for HTTP/HTTPS request logs from web servers (Apache, Nginx, IIS), proxies, CDNs, or application servers that show user web browsing activity.",
            "vulnerabilities": "Use this model for vulnerability scanner results (Nessus, Qualys, etc.), security assessment reports, or CVE tracking data that identifies security weaknesses in your environment.",
            "data-access": "Use this model when tracking file access events, database queries, or any logs showing users accessing or modifying sensitive data resources.",
        }

        return guidance_map.get(
            model, f"Use this model for events related to {model_info['name'].lower()}."
        )

    def _generate_tag_config(self, tags: list) -> str:
        """Generate tag configuration entries."""
        return "\n".join(f"{tag} = enabled" for tag in tags)

    def _generate_example_field_mappings(self, model: str) -> str:
        """Generate example field mapping configurations."""
        examples = {
            "authentication": """# Example field mappings for authentication data
FIELDALIAS-user = username AS user
FIELDALIAS-src = client_ip AS src
FIELDALIAS-dest = server_ip AS dest
EVAL-action = if(status="success", "success", "failure")
EVAL-app = coalesce(application, service_name, "unknown")""",
            "network-traffic": """# Example field mappings for network traffic
FIELDALIAS-src = source_ip AS src
FIELDALIAS-dest = destination_ip AS dest
FIELDALIAS-src_port = source_port AS src_port
FIELDALIAS-dest_port = destination_port AS dest_port
EVAL-action = case(action="allow", "allowed", action="deny", "blocked", 1=1, action)""",
            "web": """# Example field mappings for web logs
FIELDALIAS-src = client_ip AS src
FIELDALIAS-dest = server_ip AS dest
FIELDALIAS-url = uri AS url
FIELDALIAS-http_method = method AS http_method
FIELDALIAS-status = response_code AS status""",
            "malware": """# Example field mappings for malware events
FIELDALIAS-file_name = filename AS file_name
FIELDALIAS-file_hash = hash AS file_hash
FIELDALIAS-signature = malware_name AS signature
EVAL-action = case(action="quarantine", "blocked", action="delete", "blocked", 1=1, action)""",
            "endpoint": """# Example field mappings for endpoint events
FIELDALIAS-user = account_name AS user
FIELDALIAS-dest = hostname AS dest
FIELDALIAS-process = process_name AS process
FIELDALIAS-parent_process = parent_process_name AS parent_process
EVAL-action = case(event_type="start", "allowed", event_type="block", "blocked", 1=1, event_type)""",
        }

        return examples.get(
            model,
            """# Add your field mappings here
# FIELDALIAS-alias_name = vendor_field AS cim_field
# EVAL-cim_field = expression""",
        )

    def _generate_common_fields_list(self, model: str) -> str:
        """Generate a list of common fields for this model."""
        common_fields = {
            "authentication": "user, src, dest, action, app, signature",
            "network-traffic": "src, dest, src_port, dest_port, action, bytes_in, bytes_out",
            "web": "src, dest, url, http_method, status, bytes, user_agent",
            "malware": "file_name, file_hash, signature, action, user, dest",
            "endpoint": "user, dest, process, parent_process, process_id, action",
            "intrusion-detection": "src, dest, signature, category, severity, ids_type",
            "vulnerabilities": "dest, signature, severity, cve, category",
            "data-access": "user, src, object, object_type, action, file_name",
        }

        return common_fields.get(model, "tag, sourcetype, source")

    def _generate_related_models(self, model: str) -> str:
        """Generate links to related data models."""
        related_map = {
            "authentication": ["endpoint", "change", "data-access"],
            "network-traffic": ["network-sessions", "network-resolution", "intrusion-detection"],
            "intrusion-detection": ["network-traffic", "malware", "endpoint"],
            "malware": ["endpoint", "intrusion-detection", "email"],
            "endpoint": ["authentication", "malware", "change"],
            "web": ["network-traffic", "email", "data-access"],
            "email": ["malware", "dlp", "web"],
            "vulnerabilities": ["endpoint", "inventory", "change"],
            "data-access": ["authentication", "dlp", "databases"],
        }

        related = related_map.get(model, [])
        if not related:
            return "Consult the [CIM Discovery Resource](splunk-cim://discovery) for related data models."

        links = []
        for related_model in related:
            if related_model in self.CIM_DATA_MODELS:
                model_info = self.CIM_DATA_MODELS[related_model]
                links.append(
                    f"- [{model_info['name']}](splunk-cim://{related_model}) - {model_info['description']}"
                )

        return "\n".join(links)


# Factory functions
def create_cim_data_model_resource(version: str, model: str) -> CIMDataModelResource:
    """Factory function to create CIM data model resources.

    Args:
        version: CIM version (e.g., "6.1", "latest") - defaults to "latest" if not provided
        model: Data model name (e.g., "authentication", "network-traffic")

    Returns:
        CIMDataModelResource instance
    """
    return CIMDataModelResource(version or "latest", model)


# Registry function
def register_all_cim_resources():
    """Register all CIM resources with the resource registry."""
    try:
        # Register discovery resource
        resource_registry.register(CIMDiscoveryResource, CIMDiscoveryResource.METADATA)

        # Register data model template resource
        resource_registry.register(CIMDataModelResource, CIMDataModelResource.METADATA)

        logger.info(
            "Successfully registered %d Splunk CIM resources (%d static discovery, %d dynamic template for %d data models)",
            2,
            1,
            1,
            26,
        )

    except Exception as exc:
        logger.error("Failed to register CIM resources: %s", str(exc))


# Auto-register resources when module is imported
register_all_cim_resources()
