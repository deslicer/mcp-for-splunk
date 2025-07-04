# ToolListResponseResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**tools** | [**List[ToolMetadata]**](ToolMetadata.md) |  | [optional] 

## Example

```python
from splunk_mcp_client.models.tool_list_response_result import ToolListResponseResult

# TODO update the JSON string below
json = "{}"
# create an instance of ToolListResponseResult from a JSON string
tool_list_response_result_instance = ToolListResponseResult.from_json(json)
# print the JSON string representation of the object
print(ToolListResponseResult.to_json())

# convert the object into a dict
tool_list_response_result_dict = tool_list_response_result_instance.to_dict()
# create an instance of ToolListResponseResult from a dict
tool_list_response_result_from_dict = ToolListResponseResult.from_dict(tool_list_response_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


