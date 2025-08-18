# Splunk Search Tool Template

The enhanced `generate_tool.py` script now includes a specialized **Splunk Search Template** that makes it easy to create new Splunk search tools based on your working `splunk_search.py` tool.

## 🎯 **What is the Splunk Search Template?**

The Splunk Search Template creates fully functional Splunk search tools with:
- ✅ **Custom SPL queries** embedded in the tool
- ✅ **Proper error handling** and connection management
- ✅ **Comprehensive test coverage** with Splunk mocking
- ✅ **Consistent structure** following project standards
- ✅ **Time range parameters** and result limiting
- ✅ **Optional custom parameters** for search flexibility

## 🚀 **How to Use the Template**

### **Basic Usage**
```bash
# Run the enhanced generator
./contrib/scripts/generate_tool.py

# Select template type
1. Tool Template
   1. basic: Basic tool template with standard functionality
   2. splunk_search: Splunk search tool template for custom SPL queries

Select template (1-2): 2
```

### **Template Workflow**
1. **Choose template**: Select `splunk_search`
2. **Select category**: Choose appropriate category (security, devops, analytics, etc.)
3. **Enter tool details**: Name and description
4. **Enter SPL query**: Your custom Splunk search (multiline support)
5. **Query description**: What the search does
6. **Configure defaults**: Time ranges and result limits
7. **Add custom parameters** (optional): Additional search parameters
8. **Generate tool and tests**: Fully functional tool with comprehensive tests

## 🔍 **Example: Creating a Failed Login Detector**

```bash
./contrib/scripts/generate_tool.py

# Template selection
Select template (1-2): 2

# Category selection
Select category (1-4): 2

# Tool details
Tool name: failed login detector
Description: Detects failed login attempts from authentication logs

# SPL Query Input
Splunk Search Query (SPL) Input:
   1. Multi-line input (for complex queries)
   2. Single-line input (for simple queries)

Select input method (1-2): 1

Enter your Splunk search query (SPL):
(Enter your query line by line. Type 'END' on a new line to finish)
> index=security sourcetype=auth
> | search "failed" OR "failure" OR "invalid"
> | stats count by src_ip user
> | where count > 5
> | sort -count
> END


# Query description
Query description: Finds IP addresses and users with more than 5 failed login attempts

# Default parameters
Default earliest time: -1h
Default latest time: now
Default max results: 100

# Custom parameters
Add custom search parameters? (y/n): y
Parameter name: threshold
Type for threshold: int
Description for threshold: Minimum number of failed attempts to trigger alert
Default value for threshold: 5
Parameter name: [Enter to finish]

# Result: Creates FailedLoginDetectorTool with comprehensive tests
```

## 🏗️ **Generated Tool Structure**

The template creates tools with this structure:

```python
class FailedLoginDetectorTool(BaseTool):
    """
    Detects failed login attempts from authentication logs

    This tool executes the following Splunk search:
    Finds IP addresses and users with more than 5 failed login attempts

    SPL Query:
    index=security sourcetype=auth | search "failed" OR "failure" OR "invalid" | stats count by src_ip user | where count > 5 | sort -count
    """

    METADATA = ToolMetadata(
        name="failed_login_detector",
        description="Detects failed login attempts from authentication logs",
        category="security",
        tags=["security", "threat-hunting", "incident-response", "splunk", "search", "spl"],
        requires_connection=True,
        version="1.0.0"
    )

    async def execute(
        self,
        ctx: Context,
        earliest_time: str = "-1h",
        latest_time: str = "now",
        max_results: int = 100,
        threshold: int = 5
    ) -> Dict[str, Any]:
        # ... full implementation with error handling, logging, etc.
```

## 📊 **Generated Test Coverage**

Each tool comes with comprehensive tests:

```python
class TestFailedLoginDetectorTool:
    # ✅ Success scenarios with default and custom parameters
    # ✅ Splunk connection failure handling
    # ✅ Search execution errors
    # ✅ Parameter validation
    # ✅ Metadata verification
    # ✅ Mocked Splunk service and ResultsReader
```

## 🎯 **Use Cases for Splunk Search Templates**

### **Security Tools**
- **Threat Detection**: Suspicious IP patterns, failed logins, malware indicators
- **Incident Response**: Log correlation, timeline analysis, IOC searches
- **Compliance**: Access audits, data usage monitoring, policy violations

### **DevOps Tools**
- **Performance Monitoring**: Error rates, response times, resource usage
- **Alert Analysis**: Service outages, threshold breaches, anomaly detection
- **Capacity Planning**: Usage trends, growth patterns, resource forecasting

### **Analytics Tools**
- **Business Intelligence**: User behavior, feature usage, conversion metrics
- **Operational Metrics**: Transaction volumes, success rates, SLA tracking
- **Custom Dashboards**: KPI calculations, trend analysis, comparative reports

## 🔧 **Advanced Features**

### **Custom Parameters**
Add tool-specific parameters beyond the standard time/results options:

```python
# Example: Log level filtering tool
async def execute(
    self,
    ctx: Context,
    earliest_time: str = "-1h",
    latest_time: str = "now",
    max_results: int = 100,
    log_level: str = "ERROR",          # Custom parameter
    source_app: str = "",              # Custom parameter
    min_occurrences: int = 1           # Custom parameter
):
```

### **Query Templates**
Common SPL patterns you can use:

```spl
# Error detection
index=app_logs level=ERROR | stats count by component error_msg | sort -count

# Performance analysis
index=web_logs | stats avg(response_time) p95(response_time) by endpoint

# Security monitoring
index=security action=blocked | stats count by src_ip dest_port | where count > 10

# User behavior
index=user_events action=login | stats count by user_id hour | sort -count

# System health
index=_internal component=Metrics | stats latest(cpu_usage) by host
```

## 🏆 **Best Practices**

1. **Specific Tool Names**: Use descriptive names like "failed_login_detector" vs "security_tool"

2. **Clear Query Descriptions**: Explain what the search finds and why it's useful

3. **Reasonable Defaults**: Set sensible time ranges and result limits

4. **Proper Categories**:
   - `security`: Threat hunting, incident response
   - `devops`: Monitoring, alerting, performance
   - `analytics`: Business metrics, reporting
   - `examples`: Learning, demos, tutorials

5. **Useful Tags**: Include relevant tags for discoverability

6. **Test Your Queries**: Validate SPL syntax in Splunk before generating

## 🚀 **Integration with Your Project**

The generated tools automatically:
- ✅ **Integrate with your MCP server**
- ✅ **Use your Splunk connection** configuration
- ✅ **Follow project coding standards**
- ✅ **Include comprehensive logging**
- ✅ **Handle connection failures gracefully**
- ✅ **Support Docker hot-reload** (when using watch mode)

## 📈 **Template Evolution**

Your `splunk_search.py` tool serves as the **foundation template**. As you enhance it with new features:
- Error handling improvements
- Performance optimizations
- Additional response fields
- Enhanced logging

These improvements can be **incorporated into the template** to benefit all future generated tools.

---

**Ready to create powerful Splunk search tools? Start with:**
```bash
./contrib/scripts/generate_tool.py
```

Choose `splunk_search` template and build your custom Splunk search arsenal! 🎯
