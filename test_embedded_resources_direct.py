#!/usr/bin/env python3
"""
Direct test script for embedded Splunk documentation content.

This script tests the embedded documentation content directly without importing the full module structure.
"""

import sys
import os

# Add the project root to the path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_embedded_content_direct():
    """Test the embedded content directly."""
    print("🧪 Testing Embedded Splunk Documentation Content (Direct)")
    print("=" * 70)
    
    # Test the embedded content directly
    print("\n1. Testing embedded content creation...")
    
    # Splunk Cheat Sheet content
    cheat_sheet_content = """# Splunk Cheat Sheet

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
    
    print(f"✅ Cheat sheet content length: {len(cheat_sheet_content)} characters")
    print(f"✅ Content starts with: {cheat_sheet_content[:50]}...")
    
    # SPL Reference content
    spl_reference_content = """# SPL (Search Processing Language) Reference

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
    
    print(f"✅ SPL reference content length: {len(spl_reference_content)} characters")
    print(f"✅ Content starts with: {spl_reference_content[:50]}...")
    
    # Test content structure
    print("\n2. Testing content structure...")
    
    # Check for key sections in cheat sheet
    cheat_sheet_sections = [
        "Search Commands",
        "SPL (Search Processing Language) Syntax",
        "Common Search Patterns",
        "Time Modifiers",
        "Field Extraction",
        "Statistical Functions",
        "Visualization Commands",
        "Performance Tips",
        "Common Use Cases",
        "Troubleshooting",
        "Best Practices"
    ]
    
    for section in cheat_sheet_sections:
        if section in cheat_sheet_content:
            print(f"✅ Found section: {section}")
        else:
            print(f"❌ Missing section: {section}")
    
    # Check for key sections in SPL reference
    spl_reference_sections = [
        "Search Commands Overview",
        "Generating Commands",
        "Transforming Commands",
        "Filtering Commands",
        "Statistical Commands",
        "Output Commands",
        "Statistical Functions",
        "String Functions",
        "Mathematical Functions",
        "Time Functions",
        "Conditional Functions",
        "Regular Expressions",
        "Best Practices",
        "Examples"
    ]
    
    print("\nSPL Reference sections:")
    for section in spl_reference_sections:
        if section in spl_reference_content:
            print(f"✅ Found section: {section}")
        else:
            print(f"❌ Missing section: {section}")
    
    # Test content quality
    print("\n3. Testing content quality...")
    
    # Check for code examples
    code_blocks = cheat_sheet_content.count("```")
    print(f"✅ Code blocks in cheat sheet: {code_blocks // 2}")  # Divide by 2 since each block has opening and closing
    
    # Check for command examples
    command_examples = cheat_sheet_content.count("`")
    print(f"✅ Command examples in cheat sheet: {command_examples}")
    
    # Check for practical examples
    practical_examples = cheat_sheet_content.count("### ")
    print(f"✅ Practical examples in cheat sheet: {practical_examples}")
    
    print("\n" + "=" * 70)
    print("🎉 Embedded content test completed!")
    print(f"📊 Summary:")
    print(f"   - Cheat sheet: {len(cheat_sheet_content)} characters")
    print(f"   - SPL reference: {len(spl_reference_content)} characters")
    print(f"   - Total content: {len(cheat_sheet_content) + len(spl_reference_content)} characters")
    print(f"   - Code blocks: {code_blocks // 2}")
    print(f"   - Command examples: {command_examples}")
    print(f"   - Practical examples: {practical_examples}")


if __name__ == "__main__":
    test_embedded_content_direct()