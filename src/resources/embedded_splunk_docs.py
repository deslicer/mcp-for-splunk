"""
Embedded Splunk Documentation Resources for MCP Server.

Provides embedded versions of Splunk documentation including cheat sheets,
SPL reference, troubleshooting guides, and administration documentation.
"""

import logging

from src.resources.embedded import EmbeddedResource

logger = logging.getLogger(__name__)


class SplunkCheatSheetEmbeddedResource(EmbeddedResource):
    """
    Embedded Splunk cheat sheet resource.

    Provides comprehensive Splunk cheat sheet with search commands,
    SPL syntax, and common patterns.
    """

    def __init__(self):
        super().__init__(
            uri="embedded://splunk/docs/cheat-sheet",
            name="Splunk Cheat Sheet",
            description="Comprehensive Splunk cheat sheet with search commands, SPL syntax, and common patterns",
            mime_type="text/markdown",
            embedded_content=self._get_cheat_sheet_content(),
            cache_ttl=86400,  # 24 hours
            validate_content=True,
        )

    def _get_cheat_sheet_content(self) -> str:
        """Get the embedded cheat sheet content."""
        return """# Splunk Cheat Sheet

## Search Commands

### Basic Search Commands
- `search` - Start a search (optional, implied)
- `|` - Pipe results to next command
- `where` - Filter results based on conditions
- `head` - Limit results to first N events
- `tail` - Limit results to last N events
- `sort` - Sort results by field
- `dedup` - Remove duplicate events
- `rename` - Rename fields
- `eval` - Create calculated fields
- `rex` - Extract fields using regex
- `replace` - Replace text in fields

### Statistical Commands
- `stats` - Calculate statistics
- `chart` - Create charts
- `timechart` - Create time-based charts
- `top` - Show top values
- `rare` - Show least common values
- `eventstats` - Add statistics to events
- `streamstats` - Calculate running statistics

### Data Manipulation
- `lookup` - Join with lookup table
- `join` - Join with another search
- `append` - Append results
- `union` - Combine multiple searches
- `multisearch` - Run multiple searches
- `subsearch` - Use subsearch results

### Output Commands
- `table` - Display as table
- `list` - Display as list
- `fields` - Select specific fields
- `outputcsv` - Export to CSV
- `outputlookup` - Export to lookup table
- `sendemail` - Send email alert

## SPL (Search Processing Language) Syntax

### Field References
```
field_name
"field name with spaces"
```

### String Operations
```
eval new_field="value"
eval concatenated=field1 . " " . field2
eval length=len(field_name)
```

### Numeric Operations
```
eval sum=field1 + field2
eval product=field1 * field2
eval ratio=field1 / field2
eval remainder=field1 % field2
```

### Boolean Operations
```
eval is_high=if(field > 100, "yes", "no")
eval status=case(field1 > 100, "high", field1 > 50, "medium", 1=1, "low")
```

### Time Functions
```
eval _time=strptime(timestamp, "%Y-%m-%d %H:%M:%S")
eval time_hour=strftime(_time, "%H")
eval time_day=strftime(_time, "%A")
```

## Common Search Patterns

### Error Log Analysis
```
index=main error OR fail OR exception
| stats count by sourcetype
| sort -count
```

### Performance Monitoring
```
index=main sourcetype=perfmon
| timechart avg(cpu_percent) by host
```

### Security Analysis
```
index=main (authentication OR login OR logout)
| stats count by user, action
| where count > 10
```

### Data Validation
```
index=main
| eval is_valid=if(len(field) > 0, "valid", "invalid")
| stats count by is_valid
```

## Time Modifiers

### Relative Time
- `earliest=-1h` - Last hour
- `earliest=-1d` - Last day
- `earliest=-7d` - Last week
- `earliest=-30d` - Last month
- `earliest=-1y` - Last year

### Absolute Time
- `earliest="01/01/2024:00:00:00"` - Specific date
- `latest="01/31/2024:23:59:59"` - End date

### Real-time
- `earliest=rt` - Real-time search

## Field Extraction

### Automatic Extraction
- Splunk automatically extracts common fields
- `_time`, `_raw`, `host`, `source`, `sourcetype`

### Manual Extraction with rex
```
| rex field=_raw "(?<ip>\\d+\\.\\d+\\.\\d+\\.\\d+)"
| rex field=_raw "(?<user>\\w+)@(?<domain>\\w+\\.\\w+)"
```

### JSON Extraction
```
| spath path=json_field
| spath path=json_field.subfield
```

## Statistical Functions

### Basic Stats
- `count()` - Count events
- `sum(field)` - Sum of field values
- `avg(field)` - Average of field values
- `min(field)` - Minimum value
- `max(field)` - Maximum value
- `stdev(field)` - Standard deviation

### Advanced Stats
- `median(field)` - Median value
- `mode(field)` - Most common value
- `perc95(field)` - 95th percentile
- `perc99(field)` - 99th percentile
- `var(field)` - Variance
- `range(field)` - Range (max - min)

## Visualization Commands

### Chart Types
- `chart count by field` - Bar chart
- `chart count by field1, field2` - Multi-series chart
- `timechart count` - Line chart over time
- `timechart avg(field) by category` - Multi-line chart

### Output Formats
- `table field1, field2, field3` - Tabular output
- `list field1, field2` - List format
- `stats count by field | table field, count` - Custom table

## Performance Tips

### Search Optimization
1. Use specific indexes and sourcetypes
2. Filter early with `where` clauses
3. Use `head` or `tail` to limit results
4. Avoid `*` wildcards when possible
5. Use `dedup` to remove duplicates

### Field Optimization
1. Use `fields` to select only needed fields
2. Use `rename` to create meaningful field names
3. Use `eval` for calculations instead of post-processing

### Time Optimization
1. Use appropriate time ranges
2. Use `earliest` and `latest` parameters
3. Consider using `rt` for real-time searches

## Common Use Cases

### Log Analysis
```
index=main sourcetype=access_combined
| stats count by status
| sort -count
```

### Error Monitoring
```
index=main error
| timechart count by sourcetype
```

### User Activity
```
index=main user=*
| stats count by user
| sort -count
| head 10
```

### System Performance
```
index=main sourcetype=perfmon
| timechart avg(cpu_percent) by host
```

### Security Events
```
index=main (authentication OR login OR logout)
| stats count by user, action
| where count > 5
```

## Troubleshooting

### Common Issues
1. **No results**: Check index, sourcetype, and time range
2. **Slow searches**: Add filters and use `head`
3. **Memory errors**: Use `head` or `tail` to limit results
4. **Field not found**: Check field extraction and spelling

### Debugging Commands
```
| stats count by sourcetype
| stats count by index
| stats count by host
| head 1
| table _raw
```

## Best Practices

1. **Start simple**: Begin with basic searches
2. **Add complexity gradually**: Build up to complex searches
3. **Use comments**: Add `#` comments for clarity
4. **Test incrementally**: Test each part of complex searches
5. **Use saved searches**: Save frequently used searches
6. **Monitor performance**: Watch search execution time
7. **Use appropriate time ranges**: Don't search unnecessary time periods
8. **Validate results**: Always verify search results make sense

## Resources

- [Splunk Documentation](https://docs.splunk.com)
- [SPL Reference](https://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Abstract)
- [Search Tutorial](https://docs.splunk.com/Documentation/Splunk/latest/SearchTutorial/Welcome)
- [Search Commands](https://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Abstract)
"""


class SPLReferenceEmbeddedResource(EmbeddedResource):
    """
    Embedded SPL (Search Processing Language) reference.

    Provides comprehensive SPL syntax and command reference.
    """

    def __init__(self):
        super().__init__(
            uri="embedded://splunk/docs/spl-reference",
            name="SPL Reference",
            description="Comprehensive SPL (Search Processing Language) reference with syntax and examples",
            mime_type="text/markdown",
            embedded_content=self._get_spl_reference_content(),
            cache_ttl=86400,  # 24 hours
            validate_content=True,
        )

    def _get_spl_reference_content(self) -> str:
        """Get the embedded SPL reference content."""
        return """# SPL (Search Processing Language) Reference

## Search Commands Overview

SPL commands are separated by the pipe character `|` and are processed from left to right.

### Command Categories

1. **Generating Commands**: Create or retrieve data
2. **Transforming Commands**: Modify data structure
3. **Filtering Commands**: Reduce data volume
4. **Statistical Commands**: Calculate statistics
5. **Output Commands**: Format and display results

## Generating Commands

### search
```
search [<search-expression>]
```
- Starts a search (optional, implied)
- Filters events based on search expression

### multisearch
```
| multisearch [<search1>] [<search2>] ...
```
- Combines multiple searches
- Each search runs independently

### append
```
| append [<subsearch>]
```
- Appends results from subsearch to current results

### join
```
| join [<join-type>] [<join-field>] [<subsearch>]
```
- Joins current results with subsearch results

## Transforming Commands

### eval
```
| eval <field-name>=<expression>
```
- Creates calculated fields
- Supports mathematical, string, and logical operations

### rex
```
| rex field=<field> "(?<capture-group>regex)"
```
- Extracts fields using regular expressions
- Creates new fields from matched patterns

### spath
```
| spath [path=<json-path>]
```
- Extracts fields from JSON and XML data
- Automatically detects JSON/XML structure

### rename
```
| rename <old-field> AS <new-field>
```
- Renames fields
- Supports wildcards and patterns

### replace
```
| replace <old-value> WITH <new-value> IN <field>
```
- Replaces text in fields
- Supports regular expressions

## Filtering Commands

### where
```
| where <condition>
```
- Filters results based on conditions
- Supports comparison operators and functions

### head
```
| head [<number>]
```
- Limits results to first N events
- Default is 10 events

### tail
```
| tail [<number>]
```
- Limits results to last N events
- Default is 10 events

### dedup
```
| dedup [<field-list>]
```
- Removes duplicate events
- Keeps first occurrence by default

### sort
```
| sort [<field-list>]
```
- Sorts results by specified fields
- Use `-` prefix for descending order

## Statistical Commands

### stats
```
| stats <function>(<field>) [by <field-list>]
```
- Calculates statistics across all events
- Groups results by specified fields

### chart
```
| chart <function>(<field>) [by <field-list>]
```
- Creates chart data
- Similar to stats but optimized for visualization

### timechart
```
| timechart <function>(<field>) [by <field-list>]
```
- Creates time-based charts
- Automatically bins data by time

### top
```
| top [<number>] <field> [by <field-list>]
```
- Shows most common values
- Default is 10 results

### rare
```
| rare [<number>] <field> [by <field-list>]
```
- Shows least common values
- Default is 10 results

### eventstats
```
| eventstats <function>(<field>) [by <field-list>]
```
- Adds statistics to each event
- Preserves original event structure

### streamstats
```
| streamstats <function>(<field>) [by <field-list>]
```
- Calculates running statistics
- Maintains event order

## Output Commands

### table
```
| table [<field-list>]
```
- Displays results as table
- Shows only specified fields

### list
```
| list [<field-list>]
```
- Displays results as list
- Shows all fields by default

### fields
```
| fields [<field-list>]
```
- Selects specific fields
- Removes all other fields

### outputcsv
```
| outputcsv [filename=<filename>]
```
- Exports results to CSV file
- Saves to Splunk home directory

### outputlookup
```
| outputlookup [<lookup-table>]
```
- Exports results to lookup table
- Creates or updates lookup file

## Statistical Functions

### Count Functions
- `count()` - Count of events
- `count(field)` - Count of non-null field values
- `dc(field)` - Distinct count of field values

### Sum Functions
- `sum(field)` - Sum of field values
- `sumsq(field)` - Sum of squared field values

### Average Functions
- `avg(field)` - Average of field values
- `mean(field)` - Mean of field values (same as avg)

### Min/Max Functions
- `min(field)` - Minimum value
- `max(field)` - Maximum value
- `range(field)` - Range (max - min)

### Percentile Functions
- `median(field)` - Median value
- `perc95(field)` - 95th percentile
- `perc99(field)` - 99th percentile

### Statistical Functions
- `stdev(field)` - Standard deviation
- `var(field)` - Variance
- `mode(field)` - Most common value

## String Functions

### Length and Case
- `len(field)` - String length
- `lower(field)` - Convert to lowercase
- `upper(field)` - Convert to uppercase

### Substring Functions
- `substr(field, start, length)` - Extract substring
- `left(field, length)` - Extract left substring
- `right(field, length)` - Extract right substring

### String Operations
- `replace(field, "old", "new")` - Replace text
- `split(field, "delimiter")` - Split string
- `trim(field)` - Remove leading/trailing whitespace

## Mathematical Functions

### Basic Math
- `abs(field)` - Absolute value
- `ceil(field)` - Ceiling function
- `floor(field)` - Floor function
- `round(field, decimals)` - Round to decimal places

### Advanced Math
- `exp(field)` - Exponential function
- `log(field)` - Natural logarithm
- `sqrt(field)` - Square root
- `pow(field, exponent)` - Power function

## Time Functions

### Time Conversion
- `strptime(field, "format")` - Parse time string
- `strftime(field, "format")` - Format time string
- `now()` - Current time
- `relative_time(now(), "-1d")` - Relative time

### Time Components
- `date_hour(field)` - Extract hour
- `date_mday(field)` - Extract day of month
- `date_month(field)` - Extract month
- `date_year(field)` - Extract year
- `date_wday(field)` - Extract day of week

## Conditional Functions

### if/case
```
if(condition, true_value, false_value)
case(condition1, value1, condition2, value2, ..., default_value)
```

### Comparison Operators
- `==` - Equal
- `!=` - Not equal
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal
- `<=` - Less than or equal

### Logical Operators
- `AND` - Logical AND
- `OR` - Logical OR
- `NOT` - Logical NOT

## Regular Expressions

### rex Command
```
| rex field=_raw "(?<ip>\\d+\\.\\d+\\.\\d+\\.\\d+)"
| rex field=_raw "(?<user>\\w+)@(?<domain>\\w+\\.\\w+)"
```

### Common Patterns
- `\\d+` - One or more digits
- `\\w+` - One or more word characters
- `[a-zA-Z]+` - One or more letters
- `.*` - Any characters
- `[^\\s]+` - Non-whitespace characters

## Best Practices

### Performance
1. Use specific indexes and sourcetypes
2. Filter early with `where` clauses
3. Use `head` or `tail` to limit results
4. Avoid `*` wildcards when possible
5. Use `dedup` to remove duplicates

### Readability
1. Use meaningful field names
2. Add comments with `#`
3. Break complex searches into multiple lines
4. Use consistent formatting

### Accuracy
1. Validate search results
2. Test with sample data
3. Use appropriate time ranges
4. Check field extraction

## Examples

### Basic Search
```
index=main sourcetype=access_combined
| stats count by status
| sort -count
```

### Error Analysis
```
index=main error
| rex field=_raw "(?<error_type>\\w+ error)"
| stats count by error_type
| sort -count
```

### Performance Monitoring
```
index=main sourcetype=perfmon
| timechart avg(cpu_percent) by host
```

### User Activity
```
index=main user=*
| stats count by user
| sort -count
| head 10
```

### Data Validation
```
index=main
| eval is_valid=if(len(field) > 0, "valid", "invalid")
| stats count by is_valid
```
"""


class SplunkTroubleshootingEmbeddedResource(EmbeddedResource):
    """
    Embedded Splunk troubleshooting guide.

    Provides common troubleshooting scenarios and solutions.
    """

    def __init__(self):
        super().__init__(
            uri="embedded://splunk/docs/troubleshooting",
            name="Splunk Troubleshooting Guide",
            description="Comprehensive troubleshooting guide for common Splunk issues and solutions",
            mime_type="text/markdown",
            embedded_content=self._get_troubleshooting_content(),
            cache_ttl=86400,  # 24 hours
            validate_content=True,
        )

    def _get_troubleshooting_content(self) -> str:
        """Get the embedded troubleshooting content."""
        return """# Splunk Troubleshooting Guide

## Common Issues and Solutions

### Search Issues

#### No Results Returned
**Symptoms**: Search returns no results even when data should exist

**Possible Causes**:
1. Incorrect index or sourcetype
2. Wrong time range
3. Search syntax errors
4. Data not indexed

**Solutions**:
```
# Check if data exists in index
| stats count by index, sourcetype

# Verify time range
| stats count by _time

# Test basic search
index=main | head 1

# Check field extraction
| table _raw
```

#### Slow Search Performance
**Symptoms**: Searches take too long to complete

**Solutions**:
1. Add specific filters early in search
2. Use `head` or `tail` to limit results
3. Use specific indexes and sourcetypes
4. Avoid `*` wildcards
5. Use `dedup` to remove duplicates

```
# Optimize search
index=main sourcetype=access_combined status=200
| head 1000
| stats count by host
```

#### Memory Errors
**Symptoms**: Search fails with memory errors

**Solutions**:
1. Use `head` or `tail` to limit results
2. Add more specific filters
3. Use `stats` instead of `table` for large datasets
4. Break complex searches into smaller parts

### Data Issues

#### Missing Fields
**Symptoms**: Expected fields are not available

**Solutions**:
1. Check field extraction
2. Use `rex` to extract fields manually
3. Verify data format

```
# Check available fields
| stats count by sourcetype
| table _raw

# Extract fields manually
| rex field=_raw "(?<ip>\\d+\\.\\d+\\.\\d+\\.\\d+)"
```

#### Incorrect Data Types
**Symptoms**: Numeric fields treated as strings

**Solutions**:
1. Use `eval` to convert data types
2. Check field extraction settings
3. Use `tonumber()` function

```
# Convert string to number
| eval numeric_field=tonumber(string_field)
```

### Performance Issues

#### High CPU Usage
**Symptoms**: Splunk using excessive CPU

**Solutions**:
1. Check search load
2. Review index settings
3. Optimize field extraction
4. Monitor resource usage

#### High Memory Usage
**Symptoms**: Splunk using excessive memory

**Solutions**:
1. Limit search results
2. Use `stats` instead of `table`
3. Optimize field extraction
4. Review memory settings

### Index Issues

#### Index Not Found
**Symptoms**: Search fails with "index not found"

**Solutions**:
1. Verify index exists
2. Check index permissions
3. Review index configuration

```
# List available indexes
| rest /services/data/indexes
| table title, summary
```

#### Index Corruption
**Symptoms**: Data missing or corrupted

**Solutions**:
1. Check index integrity
2. Rebuild corrupted buckets
3. Restore from backup if necessary

### Forwarder Issues

#### Data Not Reaching Indexer
**Symptoms**: Data not appearing in searches

**Solutions**:
1. Check forwarder status
2. Verify network connectivity
3. Review forwarder configuration
4. Check indexer connectivity

#### Forwarder Disconnected
**Symptoms**: Forwarder not sending data

**Solutions**:
1. Restart forwarder service
2. Check network connectivity
3. Verify authentication
4. Review forwarder logs

### Authentication Issues

#### Login Failures
**Symptoms**: Unable to log into Splunk

**Solutions**:
1. Check user credentials
2. Verify authentication method
3. Review user permissions
4. Check authentication logs

#### Permission Errors
**Symptoms**: Access denied to resources

**Solutions**:
1. Check user roles
2. Verify resource permissions
3. Review role assignments
4. Check capability settings

### Configuration Issues

#### Configuration Not Applied
**Symptoms**: Changes not taking effect

**Solutions**:
1. Restart affected services
2. Check configuration syntax
3. Verify file permissions
4. Review configuration validation

#### Configuration Errors
**Symptoms**: Services failing to start

**Solutions**:
1. Check configuration syntax
2. Review error logs
3. Validate configuration files
4. Use configuration validation tools

## Diagnostic Commands

### System Health
```
| rest /services/server/info
| table version, build, os_name
```

### Index Status
```
| rest /services/data/indexes
| table title, summary, count
```

### Forwarder Status
```
| rest /services/deployment/server
| table title, status
```

### Search Performance
```
| rest /services/search/jobs
| table sid, search, state, runtime
```

### User Activity
```
| rest /services/authentication/users
| table name, realName, email
```

## Log Analysis

### Splunk Logs
```
index=_internal sourcetype=splunkd
| stats count by component
```

### Search Logs
```
index=_internal sourcetype=splunkd_search
| stats count by action
```

### Forwarder Logs
```
index=_internal sourcetype=splunkd_forwarder
| stats count by action
```

### Authentication Logs
```
index=_internal sourcetype=splunkd_auth
| stats count by action
```

## Performance Monitoring

### Search Load
```
| rest /services/search/jobs
| stats count by state
```

### Index Performance
```
| rest /services/data/indexes
| stats avg(count) by title
```

### System Resources
```
| rest /services/server/info
| eval cpu_usage=tonumber(cpu_usage)
| eval mem_usage=tonumber(mem_usage)
```

## Best Practices

### Regular Maintenance
1. Monitor system health
2. Review search performance
3. Clean up old data
4. Update configurations

### Performance Optimization
1. Use appropriate indexes
2. Optimize search queries
3. Monitor resource usage
4. Scale appropriately

### Security
1. Regular security audits
2. Monitor access logs
3. Update authentication
4. Review permissions

### Backup and Recovery
1. Regular backups
2. Test recovery procedures
3. Document procedures
4. Monitor backup status

## Getting Help

### Documentation
- [Splunk Documentation](https://docs.splunk.com)
- [Splunk Answers](https://answers.splunk.com)
- [Splunk Community](https://community.splunk.com)

### Support
- Check Splunk support portal
- Contact Splunk support
- Use Splunk community forums

### Logs
- Review `$SPLUNK_HOME/var/log/`
- Check system logs
- Monitor application logs
"""


class SplunkAdminGuideEmbeddedResource(EmbeddedResource):
    """
    Embedded Splunk administration guide.

    Provides administration tasks and best practices.
    """

    def __init__(self):
        super().__init__(
            uri="embedded://splunk/docs/admin-guide",
            name="Splunk Administration Guide",
            description="Comprehensive administration guide for Splunk deployment and management",
            mime_type="text/markdown",
            embedded_content=self._get_admin_guide_content(),
            cache_ttl=86400,  # 24 hours
            validate_content=True,
        )

    def _get_admin_guide_content(self) -> str:
        """Get the embedded administration guide content."""
        return """# Splunk Administration Guide

## Installation and Setup

### System Requirements
- **CPU**: 2+ cores recommended
- **Memory**: 8GB+ RAM recommended
- **Storage**: Fast storage for indexes
- **Network**: Stable connectivity

### Installation Steps
1. Download Splunk from official website
2. Extract to desired location
3. Run installation script
4. Configure initial settings
5. Start Splunk services

### Initial Configuration
1. Set admin password
2. Configure license
3. Set up indexes
4. Configure inputs
5. Set up authentication

## Index Management

### Creating Indexes
```
# Via Web UI
Settings > Indexes > New Index

# Via CLI
splunk add index <index_name>
```

### Index Configuration
- **Max size**: Set maximum index size
- **Max time**: Set maximum retention time
- **Frozen time**: Set frozen time period
- **Thawed path**: Set thawed data location

### Index Maintenance
1. **Bucket management**: Monitor bucket sizes
2. **Data retention**: Configure retention policies
3. **Storage optimization**: Optimize storage settings
4. **Backup procedures**: Regular backups

## User Management

### Creating Users
```
# Via Web UI
Settings > Users and authentication > Users > New User

# Via CLI
splunk add user <username> -role <role> -password <password>
```

### Role Management
1. **Admin**: Full system access
2. **Power**: Advanced search capabilities
3. **User**: Basic search capabilities
4. **Can_delete**: Delete permissions
5. **Can_share_app**: Share app permissions

### Authentication Methods
1. **Splunk**: Built-in authentication
2. **LDAP**: Lightweight Directory Access Protocol
3. **SAML**: Security Assertion Markup Language
4. **Scripted**: Custom authentication scripts

## Forwarder Management

### Universal Forwarder
- Lightweight data collection
- Minimal resource usage
- Secure data transmission
- Easy deployment

### Heavy Forwarder
- Data processing capabilities
- Parsing and filtering
- Indexing capabilities
- More resource intensive

### Forwarder Configuration
1. **Inputs.conf**: Configure data inputs
2. **Outputs.conf**: Configure data outputs
3. **Props.conf**: Configure data processing
4. **Transforms.conf**: Configure data transformations

## Monitoring and Alerting

### System Monitoring
1. **Health checks**: Regular system health monitoring
2. **Performance metrics**: Monitor system performance
3. **Resource usage**: Track resource utilization
4. **Error monitoring**: Monitor error conditions

### Alerting Setup
1. **Alert conditions**: Define alert triggers
2. **Alert actions**: Configure alert responses
3. **Alert scheduling**: Set alert schedules
4. **Alert history**: Monitor alert history

### Dashboard Creation
1. **Search dashboards**: Create search-based dashboards
2. **Form dashboards**: Create form-based dashboards
3. **Real-time dashboards**: Create real-time dashboards
4. **Dashboard sharing**: Share dashboards with users

## Security Configuration

### Access Control
1. **User roles**: Define user roles and permissions
2. **Resource permissions**: Set resource access permissions
3. **App permissions**: Configure app access permissions
4. **Network security**: Configure network security settings

### Data Security
1. **Encryption**: Enable data encryption
2. **SSL/TLS**: Configure SSL/TLS settings
3. **Authentication**: Configure authentication methods
4. **Audit logging**: Enable audit logging

### Compliance
1. **Data retention**: Configure data retention policies
2. **Audit trails**: Maintain audit trails
3. **Access logging**: Log access attempts
4. **Security monitoring**: Monitor security events

## Backup and Recovery

### Backup Procedures
1. **Configuration backup**: Backup configuration files
2. **Index backup**: Backup index data
3. **App backup**: Backup app configurations
4. **User backup**: Backup user settings

### Recovery Procedures
1. **Configuration restore**: Restore configuration files
2. **Index restore**: Restore index data
3. **App restore**: Restore app configurations
4. **User restore**: Restore user settings

### Disaster Recovery
1. **Backup strategies**: Develop backup strategies
2. **Recovery testing**: Test recovery procedures
3. **Documentation**: Document recovery procedures
4. **Training**: Train staff on recovery procedures

## Performance Optimization

### Search Optimization
1. **Index optimization**: Optimize index settings
2. **Search optimization**: Optimize search queries
3. **Field extraction**: Optimize field extraction
4. **Caching**: Configure search caching

### System Optimization
1. **Memory optimization**: Optimize memory usage
2. **CPU optimization**: Optimize CPU usage
3. **Storage optimization**: Optimize storage usage
4. **Network optimization**: Optimize network usage

### Scaling Strategies
1. **Horizontal scaling**: Add more indexers
2. **Vertical scaling**: Increase system resources
3. **Load balancing**: Implement load balancing
4. **Clustering**: Implement indexer clustering

## Troubleshooting

### Common Issues
1. **Service failures**: Troubleshoot service failures
2. **Performance issues**: Troubleshoot performance issues
3. **Configuration errors**: Troubleshoot configuration errors
4. **Network issues**: Troubleshoot network issues

### Diagnostic Tools
1. **Splunk CLI**: Use Splunk command line tools
2. **Log analysis**: Analyze Splunk logs
3. **Health checks**: Run health checks
4. **Performance monitoring**: Monitor system performance

### Support Resources
1. **Documentation**: Review Splunk documentation
2. **Community**: Use Splunk community resources
3. **Support**: Contact Splunk support
4. **Training**: Attend Splunk training

## Best Practices

### System Administration
1. **Regular maintenance**: Perform regular maintenance
2. **Monitoring**: Implement comprehensive monitoring
3. **Documentation**: Maintain detailed documentation
4. **Training**: Provide staff training

### Security
1. **Regular audits**: Perform regular security audits
2. **Access control**: Implement proper access control
3. **Monitoring**: Monitor security events
4. **Updates**: Keep system updated

### Performance
1. **Regular optimization**: Perform regular optimization
2. **Monitoring**: Monitor system performance
3. **Scaling**: Plan for scaling
4. **Capacity planning**: Plan for capacity needs

### Compliance
1. **Policy compliance**: Ensure policy compliance
2. **Audit trails**: Maintain audit trails
3. **Documentation**: Maintain compliance documentation
4. **Training**: Provide compliance training
"""


# Registry for embedded Splunk documentation
embedded_splunk_docs_registry = {
    "cheat_sheet": SplunkCheatSheetEmbeddedResource(),
    "spl_reference": SPLReferenceEmbeddedResource(),
    "troubleshooting": SplunkTroubleshootingEmbeddedResource(),
    "admin_guide": SplunkAdminGuideEmbeddedResource(),
}


def register_embedded_splunk_docs():
    """Register all embedded Splunk documentation resources."""
    from src.resources.embedded import embedded_resource_registry

    for name, resource in embedded_splunk_docs_registry.items():
        embedded_resource_registry.register_embedded_resource(resource)
        logger.info(f"Registered embedded Splunk documentation: {name}")

    logger.info("Successfully registered all embedded Splunk documentation resources")


def get_embedded_splunk_doc(uri: str) -> EmbeddedResource | None:
    """Get embedded Splunk documentation by URI."""
    for _name, resource in embedded_splunk_docs_registry.items():
        if resource.uri == uri:
            return resource
    return None


def list_embedded_splunk_docs() -> list[dict[str, str]]:
    """List all available embedded Splunk documentation."""
    docs = []
    for name, resource in embedded_splunk_docs_registry.items():
        docs.append(
            {
                "name": name,
                "uri": resource.uri,
                "title": resource.name,
                "description": resource.description,
            }
        )
    return docs
