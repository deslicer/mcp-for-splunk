# ToolCallResponseResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**content** | **List[object]** |  | [optional] 
**is_error** | **bool** |  | [optional] 

## Example

```python
from splunk_mcp_client.models.tool_call_response_result import ToolCallResponseResult

# TODO update the JSON string below
json = "{}"
# create an instance of ToolCallResponseResult from a JSON string
tool_call_response_result_instance = ToolCallResponseResult.from_json(json)
# print the JSON string representation of the object
print(ToolCallResponseResult.to_json())

# convert the object into a dict
tool_call_response_result_dict = tool_call_response_result_instance.to_dict()
# create an instance of ToolCallResponseResult from a dict
tool_call_response_result_from_dict = ToolCallResponseResult.from_dict(tool_call_response_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


