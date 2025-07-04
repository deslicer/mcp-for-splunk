# ToolMetadata


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**description** | **str** |  | [optional] 
**input_schema** | **object** |  | [optional] 

## Example

```python
from splunk_mcp_client.models.tool_metadata import ToolMetadata

# TODO update the JSON string below
json = "{}"
# create an instance of ToolMetadata from a JSON string
tool_metadata_instance = ToolMetadata.from_json(json)
# print the JSON string representation of the object
print(ToolMetadata.to_json())

# convert the object into a dict
tool_metadata_dict = tool_metadata_instance.to_dict()
# create an instance of ToolMetadata from a dict
tool_metadata_from_dict = ToolMetadata.from_dict(tool_metadata_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


