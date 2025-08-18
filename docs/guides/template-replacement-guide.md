# Template Replacement Guide for Splunk Triage Agent

## Overview

The Splunk Triage Agent uses template placeholders in its instructions that need to be replaced with actual values during execution. This guide explains how to handle these templates correctly.

## Template Types

### 1. Static Context Templates (Auto-Replaced)
These are replaced automatically when context is available:

- `<your_index>` → Replaced with `focus_index` from diagnostic context
- `<your_host>` → Replaced with `focus_host` from diagnostic context

**Example:**
- Input: `index=<your_index> | head 10`
- Output: `index=security | head 10` (if focus_index="security")

### 2. Dynamic Runtime Templates (Manual Replacement)
These require agent execution to obtain values:

#### Role-Based Templates
**Problem:** `<your_role>` cannot be auto-replaced because role information comes from `get_current_user_info()` during execution.

**Solution:** Use explicit workflow:

1. **Call `get_current_user_info()` first**
2. **Extract role names** from the response (look for "roles" field)
3. **Use actual role names** in subsequent searches

**Example Workflow:**
```
Step 1: Call get_current_user_info()
Response: {"roles": ["admin", "power"], ...}

Step 2: Use actual roles in search
Instead of: | rest /services/authorization/roles | search title=<your_role>
Use: | rest /services/authorization/roles | search title IN ("admin", "power")
```

## Best Practices

### For Agent Instructions
1. **Provide clear examples** showing the replacement workflow
2. **Use placeholder format** that's obviously a placeholder: `YOUR_ROLE_NAME`, `YOUR_INDEX`
3. **Include alternative approaches** for when values are unknown
4. **Explain the workflow** step-by-step

### For Agent Execution
1. **Always call info-gathering tools first** (`get_current_user_info()`, `list_splunk_indexes()`)
2. **Extract values from responses** before using them in searches
3. **Use fallback approaches** when specific values aren't available:
   - `index=*` instead of specific index
   - Check all roles instead of specific role
4. **Explain your replacements** to the user

## Improved Template Examples

### Before (Problematic)
```
Use search: | rest /services/authorization/roles | search title=<your_role>
```

### After (Clear)
```
Example workflow:
1. Call get_current_user_info() and note the roles (e.g., ["admin", "power"])
2. Then use: | rest /services/authorization/roles | search title IN ("admin", "power")
3. Or check each role individually: | rest /services/authorization/roles | search title="admin"
Alternative for overview: | rest /services/authorization/roles | table title, srchIndexesAllowed, srchIndexesDefault
```

## Template Replacement Hierarchy

1. **Context-based replacement** (automatic during instruction generation)
   - `<your_index>` → `{focus_index}`
   - `<your_host>` → `{focus_host}`

2. **Runtime replacement** (manual during execution)
   - Get values from tool calls
   - Replace in search queries
   - Provide fallback options

3. **Fallback approaches** (when values unknown)
   - Use wildcards (`index=*`, `host=*`)
   - Use discovery tools (`list_splunk_indexes()`)
   - Check all items instead of specific ones

## Common Patterns

### Index-Related Searches
```
# Good: Provide multiple options
Check for indexing delays (replace YOUR_INDEX with specific index or use index=*):
index=YOUR_INDEX | eval lag=_indextime-_time | stats avg(lag) max(lag) by index

# Better: Show context-aware replacement
If focus_index is "security": index=security | eval lag=_indextime-_time | stats avg(lag) max(lag) by index
If no focus: index=* | eval lag=_indextime-_time | stats avg(lag) max(lag) by index
```

### Role-Based Searches
```
# Good: Step-by-step workflow
STEP 3A: First, get current user information: Use get_current_user_info()
STEP 3B: Extract the role names from the user info response (look for "roles" field)
STEP 3C: Check role-based index access restrictions using the actual role names
```

This approach ensures agents can handle templates correctly and provide meaningful, executable searches to users.
