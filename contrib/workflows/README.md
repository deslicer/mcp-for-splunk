# Contributing Workflows to MCP Server for Splunk

Welcome to the workflow contribution system! This directory enables community members to create and share custom troubleshooting workflows that integrate seamlessly with the dynamic troubleshoot agent.

## 🚀 Quick Start

**Ready to create a custom workflow? Use our helper tools!**

```bash
# Get detailed requirements for creating workflows
python contrib/tools/workflows/workflow_requirements.py

# Build a new workflow interactively
python contrib/tools/workflows/workflow_builder.py

# Validate your workflow
python contrib/tools/workflows/workflow_builder.py --mode validate --file your_workflow.json
```

## 📁 Directory Structure

```
contrib/workflows/
├── README.md                    # This file - comprehensive guide
├── loaders.py                   # Workflow loading system (auto-discovery)
├── security/                    # Security-focused workflows
│   ├── threat_hunting.json      # Example: Advanced threat hunting workflow
│   └── compliance_check.json    # Example: Compliance verification workflow
├── performance/                 # Performance analysis workflows
│   ├── custom_perf_analysis.json # Example: Custom performance analysis
│   └── capacity_planning.json    # Example: Capacity planning workflow
├── data_quality/               # Data quality and integrity workflows
│   ├── data_validation.json     # Example: Data validation workflow
│   └── ingestion_health.json    # Example: Ingestion health check
└── custom/                     # General purpose custom workflows
    ├── example_workflow.json    # Example: Basic workflow template
    └── advanced_example.json    # Example: Advanced workflow with dependencies
```

## 🔧 Workflow Structure

Each workflow is defined as a JSON file following the `WorkflowDefinition` schema:

```json
{
  "workflow_id": "unique_workflow_identifier",
  "name": "Human-Readable Workflow Name",
  "description": "Detailed description of what this workflow does and when to use it",
  "tasks": [
    {
      "task_id": "unique_task_identifier",
      "name": "Human-Readable Task Name",
      "description": "What this task accomplishes",
      "instructions": "Detailed instructions for the AI agent executing this task",
      "required_tools": ["list", "of", "required", "splunk", "tools"],
      "dependencies": ["list", "of", "task_ids", "this", "depends", "on"],
      "context_requirements": ["list", "of", "context", "variables", "needed"]
    }
  ],
  "default_context": {
    "key": "value",
    "additional": "context variables"
  }
}
```

## 📊 Categories and Use Cases

### 🔒 Security Workflows (`security/`)
- **Threat Hunting**: Advanced threat detection and analysis
- **Incident Response**: Systematic incident investigation
- **Compliance Checking**: Regulatory compliance verification
- **Vulnerability Assessment**: Security posture analysis

### 🚀 Performance Workflows (`performance/`)
- **Custom Performance Analysis**: Tailored performance diagnostics
- **Capacity Planning**: Resource utilization and planning
- **Optimization Recommendations**: System tuning guidance
- **Benchmark Analysis**: Performance baseline establishment

### 📈 Data Quality Workflows (`data_quality/`)
- **Data Validation**: Data integrity and completeness checks
- **Ingestion Health**: Data pipeline health verification
- **Source Monitoring**: Data source availability and quality
- **Format Compliance**: Data format and structure validation

### 🛠️ Custom Workflows (`custom/`)
- **Business-Specific Analysis**: Organization-specific workflows
- **Integration Testing**: Custom integration verification
- **Operational Procedures**: Standardized operational tasks
- **Specialized Diagnostics**: Domain-specific troubleshooting

## 🔧 Available Tools

Your workflows can use any of these Splunk tools:

### Search Tools
- `run_splunk_search`: Execute comprehensive Splunk searches
- `run_oneshot_search`: Quick, lightweight searches for immediate results
- `run_saved_search`: Execute predefined saved searches

### Metadata Tools
- `list_splunk_indexes`: Get available indexes
- `list_splunk_sources`: Get available sources
- `list_splunk_sourcetypes`: Get available sourcetypes

### Administrative Tools
- `get_current_user_info`: Get user roles and permissions
- `get_splunk_health`: Check Splunk server health
- `get_splunk_apps`: List installed Splunk apps

### Specialized Tools
- `get_alert_status`: Check alert configurations and status
- `report_specialist_progress`: Report progress during execution

## 📝 Task Instructions Guidelines

When writing task instructions, follow these best practices:

### 1. **Be Specific and Actionable**
```
❌ Bad: "Check for performance issues"
✅ Good: "Execute search `index=_internal source=*metrics.log* component=Queues` to analyze queue performance and identify bottlenecks over the last 24 hours"
```

### 2. **Include Context Variables**
Use context variables to make workflows flexible:
```
"Check data availability in index {focus_index} from {earliest_time} to {latest_time}"
```

### 3. **Provide Expected Outcomes**
```
"Expected result: Identify any queues with >1000 pending items or >30 second processing delays"
```

### 4. **Include Splunk Searches**
Provide specific SPL queries when possible:
```
"Use search: `index=_internal source=*license_usage.log* type=Usage | stats sum(b) by pool | where sum(b) > 500000000`"
```

### 5. **Structure Analysis Steps**
Break complex analysis into clear steps:
```
"Analysis:
1. Execute the license usage search
2. Compare usage against pool quotas
3. Identify pools exceeding 80% capacity
4. Calculate projected usage trends
5. Generate capacity recommendations"
```

## 🔄 Context Variables

Your workflows can use these context variables:

### Time Context
- `{earliest_time}`: Start time for analysis
- `{latest_time}`: End time for analysis

### Focus Context
- `{focus_index}`: Target index for analysis
- `{focus_host}`: Target host for analysis
- `{focus_sourcetype}`: Target sourcetype for analysis

### User Context
- `{complexity_level}`: Analysis depth ("basic", "moderate", "advanced")

### Custom Context
Define your own context variables in `default_context`:
```json
{
  "default_context": {
    "compliance_framework": "SOX",
    "risk_threshold": "medium",
    "notification_email": "admin@company.com"
  }
}
```

## 🧪 Testing Your Workflows

### 1. **Validation Testing**
```bash
# Validate workflow structure
python contrib/tools/workflows/workflow_builder.py --mode validate --file your_workflow.json
```

### 2. **Integration Testing**
```bash
# Test with dynamic troubleshoot agent
python -c "
from src.tools.agents.dynamic_troubleshoot_agent import DynamicTroubleshootAgentTool
# Test your workflow with actual agent
"
```

### 3. **Manual Testing**
Use the dynamic troubleshoot agent with your workflow:
```python
# In your test script
await agent.execute(
    ctx=context,
    problem_description="Test description for your workflow",
    workflow_type="your_workflow_id",
    # ... other parameters
)
```

## 📋 Best Practices

### 1. **Workflow Design**
- **Single Responsibility**: Each workflow should address one specific problem domain
- **Modular Tasks**: Break complex analysis into independent, reusable tasks
- **Clear Dependencies**: Only add dependencies when truly necessary for data flow
- **Parallel Execution**: Design tasks to run in parallel when possible

### 2. **Task Design**
- **Specific Instructions**: Provide detailed, actionable instructions
- **Tool Selection**: Use the most appropriate tools for each task
- **Error Handling**: Include guidance for common error scenarios
- **Output Format**: Specify expected output format and structure

### 3. **Documentation**
- **Clear Descriptions**: Explain what the workflow does and when to use it
- **Usage Examples**: Provide example scenarios and expected outcomes
- **Parameter Guidance**: Document required and optional parameters
- **Troubleshooting**: Include common issues and solutions

### 4. **Performance**
- **Efficient Searches**: Use optimized SPL queries
- **Time Bounds**: Include appropriate time ranges for searches
- **Resource Awareness**: Consider system impact of intensive operations
- **Timeout Handling**: Set appropriate timeouts for long-running tasks

## 🔧 Integration with Dynamic Troubleshoot Agent

Your workflows automatically integrate with the dynamic troubleshoot agent. Users can execute them using:

```python
# Using workflow_type parameter
await dynamic_troubleshoot_agent.execute(
    ctx=context,
    problem_description="Description of the issue",
    workflow_type="your_workflow_id",  # Your custom workflow
    earliest_time="-24h",
    latest_time="now",
    focus_index="your_index"
)
```

The agent will:
1. **Load your workflow** from the contrib/workflows directory
2. **Validate the structure** and dependencies
3. **Execute tasks in parallel** where possible
4. **Provide comprehensive results** with findings and recommendations

## 🚀 Example: Simple Security Workflow

Here's a complete example workflow for basic security monitoring:

```json
{
  "workflow_id": "basic_security_monitoring",
  "name": "Basic Security Monitoring",
  "description": "Comprehensive security monitoring workflow for detecting common threats and anomalies",
  "tasks": [
    {
      "task_id": "failed_authentication_analysis",
      "name": "Failed Authentication Analysis",
      "description": "Analyze failed authentication attempts and identify potential brute force attacks",
      "instructions": "Execute search to identify failed authentication patterns: `index={focus_index} sourcetype=access_* OR sourcetype=linux_secure OR sourcetype=WinEventLog:Security EventCode=4625 | stats count by src_ip, user | where count > 10 | sort -count`. Analyze results for: 1. IPs with high failure counts 2. Targeted user accounts 3. Time-based patterns 4. Geographic anomalies. Provide specific recommendations for blocking suspicious IPs and strengthening authentication.",
      "required_tools": ["run_splunk_search"],
      "dependencies": [],
      "context_requirements": ["focus_index", "earliest_time", "latest_time"]
    },
    {
      "task_id": "privilege_escalation_detection",
      "name": "Privilege Escalation Detection",
      "description": "Detect potential privilege escalation attempts and unauthorized administrative access",
      "instructions": "Search for privilege escalation indicators: `index={focus_index} (sourcetype=linux_secure sudo) OR (sourcetype=WinEventLog:Security EventCode=4672) OR (\"privilege escalation\" OR \"admin access\" OR \"root access\") | stats count by user, src_ip, action | sort -count`. Look for: 1. Unusual sudo usage patterns 2. Unexpected administrative logons 3. Service account privilege changes 4. Cross-system privilege requests. Generate alerts for suspicious privilege usage.",
      "required_tools": ["run_splunk_search"],
      "dependencies": [],
      "context_requirements": ["focus_index", "earliest_time", "latest_time"]
    }
  ],
  "default_context": {
    "security_threshold": "medium",
    "alert_priority": "high"
  }
}
```

## 🤝 Community Guidelines

### Contribution Process
1. **Design your workflow** using the requirements and builder tools
2. **Test thoroughly** with validation and integration testing
3. **Document clearly** with examples and use cases
4. **Submit via pull request** with detailed description
5. **Respond to feedback** during the review process

### Quality Standards
- **Functional**: Workflows must execute successfully
- **Documented**: Clear descriptions and usage guidance
- **Tested**: Validated structure and integration
- **Secure**: No hardcoded credentials or sensitive data
- **Efficient**: Optimized for performance and resource usage

### Review Process
All workflow contributions are reviewed for:
- **Technical correctness** and functionality
- **Security best practices** and safety
- **Documentation quality** and completeness
- **Integration compatibility** with existing system
- **Performance impact** and optimization

## 🆘 Getting Help

- **Check examples** in each category directory
- **Use the builder tool** for interactive guidance
- **Read the requirements** for detailed specifications
- **Open an issue** on GitHub for questions
- **Join discussions** in the community forum

## 🔮 Advanced Features

### Dynamic Context Resolution
Workflows can reference other workflow results:
```json
{
  "dependencies": ["previous_task_id"],
  "instructions": "Use results from {previous_task_id} to guide analysis..."
}
```

### Conditional Execution
Include conditional logic in instructions:
```
"If {focus_index} is 'security', execute enhanced security analysis. Otherwise, perform basic checks."
```

### Multi-Stage Analysis
Design workflows with multiple analysis phases:
```json
{
  "tasks": [
    {"task_id": "initial_scan", "dependencies": []},
    {"task_id": "detailed_analysis", "dependencies": ["initial_scan"]},
    {"task_id": "recommendations", "dependencies": ["detailed_analysis"]}
  ]
}
```

## 📈 Contributing Back to the Community

We encourage you to:
- **Share your workflows** with the community
- **Improve existing workflows** with enhancements
- **Document best practices** you discover
- **Help others** with questions and guidance
- **Suggest improvements** to the workflow system

Together, we can build a comprehensive library of Splunk troubleshooting workflows that benefit everyone!

---

**Ready to create your first workflow?** Start with the workflow requirements tool to understand the full structure, then use the builder tool to create your custom workflow interactively. Happy troubleshooting! 🎉 