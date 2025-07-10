# Community Workflows for MCP Server for Splunk

This directory contains community-contributed workflow definitions in JSON format that extend the troubleshooting capabilities of the MCP Server for Splunk.

## 🚀 Quick Start

### Using an Existing Workflow

```bash
# List available community workflows
find contrib/workflows -name "*.json" -type f

# Use a workflow with the dynamic troubleshoot agent
await dynamic_troubleshoot_agent.execute(
    ctx=context,
    problem_description="Your specific issue description",
    workflow_type="security_analysis_workflow",  # Use the workflow_id from JSON
    earliest_time="-24h",
    latest_time="now"
)
```

### Creating Your Own Workflow

```bash
# Use the core workflow builder tool to create a new workflow
workflow_builder.execute(
    ctx=context,
    mode="create"
)

# Or start with a template
workflow_builder.execute(
    ctx=context,
    mode="template",
    template_type="security"  # security, performance, data_quality, etc.
)

# Validate your workflow
workflow_requirements.execute(
    ctx=context,
    format_type="schema"  # Get validation schema
)
```

## 📁 Directory Structure

```
contrib/workflows/
├── security/           # Security analysis workflows
├── performance/        # Performance monitoring workflows  
├── data_quality/       # Data quality assessment workflows
├── custom/            # Custom user workflows
└── examples/          # Example workflows for learning
```

## 🔧 Workflow Structure

Each workflow is a JSON file following the `WorkflowDefinition` schema:

```json
{
  "workflow_id": "my_custom_workflow",
  "name": "My Custom Workflow",
  "description": "Description of what this workflow does",
  "tasks": [
    {
      "task_id": "initial_check",
      "name": "Initial System Check",
      "description": "Perform initial assessment",
      "instructions": "Detailed instructions for the AI agent...",
      "required_tools": ["get_splunk_health"],
      "dependencies": [],
      "context_requirements": ["earliest_time", "latest_time"]
    }
  ]
}
```

## 🛠️ Available Tools

Use the `workflow_requirements` tool to get the complete list of available tools:

### Core Search Tools
- `run_splunk_search` - Execute comprehensive Splunk searches
- `run_oneshot_search` - Quick lightweight searches
- `run_saved_search` - Execute saved searches

### Metadata Tools  
- `list_splunk_indexes` - Get available indexes
- `list_splunk_sources` - Get data sources
- `list_splunk_sourcetypes` - Get sourcetypes

### Administrative Tools
- `get_current_user_info` - User permissions and roles
- `get_splunk_health` - Server health status
- `get_splunk_apps` - Installed applications

### Alert Tools
- `get_alert_status` - Alert configurations and status

## 📝 Context Variables

Available context variables for use in task instructions:

### Time Context
- `{earliest_time}` - Analysis start time
- `{latest_time}` - Analysis end time

### Focus Context
- `{focus_index}` - Target index for analysis
- `{focus_host}` - Target host for analysis
- `{focus_sourcetype}` - Target sourcetype for analysis

### User Context
- `{complexity_level}` - Analysis depth (basic/moderate/advanced)

## ✍️ Writing Task Instructions

### Best Practices

**✅ Do:**
- Be specific and actionable
- Include exact Splunk searches when possible
- Use context variables for flexibility
- Provide clear analysis steps
- Include expected outcomes

**❌ Don't:**
- Use vague instructions
- Hard-code values that should be variables
- Skip error handling guidance
- Create overly complex single tasks

### Template Structure

```
You are performing [TASK PURPOSE].

**Context:** [Description using context variables]

**Analysis Steps:**
1. [Specific step with tools to use]
2. [Next step with expected outcome]
3. [Final step with reporting]

**Searches to Execute:**
- [Specific SPL search with context variables]
- [Additional searches as needed]

**What to Look For:**
- [Key indicators and patterns]
- [Warning signs and thresholds]
- [Success criteria]

**Output:** Return DiagnosticResult with [specific findings format].
```

## 🧪 Testing Workflows

### Validation Steps

1. **Schema Validation**
   ```bash
   # Use workflow requirements tool to get schema
   workflow_requirements.execute(format_type="schema")
   
   # Validate your JSON against the schema
   ```

2. **Tool Validation**
   ```bash
   # Check all required tools are available
   workflow_requirements.execute(format_type="detailed")
   ```

3. **Integration Testing**
   ```bash
   # Test with dynamic troubleshoot agent
   dynamic_troubleshoot_agent.execute(
       problem_description="Test issue",
       workflow_type="your_workflow_id"
   )
   ```

## 📚 Example Workflows

### Minimal Example
```json
{
  "workflow_id": "simple_health_check",
  "name": "Simple Health Check", 
  "description": "Basic Splunk server health verification",
  "tasks": [
    {
      "task_id": "health_check",
      "name": "Server Health Check",
      "description": "Check basic Splunk server health",
      "instructions": "Execute health check using get_splunk_health tool. Report server status and any issues.",
      "required_tools": ["get_splunk_health"],
      "dependencies": [],
      "context_requirements": []
    }
  ]
}
```

### Security Analysis Example
```json
{
  "workflow_id": "security_analysis",
  "name": "Security Analysis Workflow",
  "description": "Comprehensive security threat analysis",
  "tasks": [
    {
      "task_id": "auth_analysis", 
      "name": "Authentication Analysis",
      "description": "Analyze authentication patterns and failures",
      "instructions": "Search for authentication events in {focus_index} from {earliest_time} to {latest_time}. Look for failed logins and unusual patterns.",
      "required_tools": ["run_splunk_search"],
      "dependencies": [],
      "context_requirements": ["focus_index", "earliest_time", "latest_time"]
    }
  ]
}
```

## 🤝 Contributing Guidelines

### Workflow Categories

- **security/** - Threat hunting, incident response, security analysis
- **performance/** - System monitoring, resource analysis, optimization
- **data_quality/** - Data integrity, availability, ingestion analysis
- **custom/** - Specialized workflows for specific use cases
- **examples/** - Learning examples and templates

### Submission Process

1. Create your workflow JSON file
2. Validate using the workflow tools
3. Test with the dynamic troubleshoot agent
4. Submit a pull request with:
   - Workflow JSON file in appropriate category
   - Brief description of use case
   - Testing evidence

### Naming Conventions

- **File names**: `category_purpose_workflow.json`
- **Workflow IDs**: `snake_case_format`
- **Task IDs**: `descriptive_snake_case`

## 🎯 Priority Workflows Needed

### High-Impact Areas
- Advanced threat hunting workflows
- Performance bottleneck analysis
- Data ingestion troubleshooting
- Compliance and audit workflows

### Beginner-Friendly
- Basic health check workflows
- Simple data quality checks
- Standard monitoring patterns
- Common troubleshooting procedures

## 📖 Resources

- **Core Tools**: Use `workflow_builder` and `workflow_requirements` tools
- **Schema Reference**: Get complete schema with `workflow_requirements.execute(format_type="schema")`
- **Examples**: Browse existing workflows in category directories
- **Integration**: See `dynamic_troubleshoot_agent.py` for usage patterns

---

**Ready to create workflows?** 🚀

Start with the `workflow_builder` tool to create your first custom troubleshooting workflow! 