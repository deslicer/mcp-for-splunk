# ToolCallResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**jsonrpc** | **str** |  | [optional] 
**result** | [**ToolCallResponseResult**](ToolCallResponseResult.md) |  | [optional] 
**id** | **str** |  | [optional] 

## Example

```python
from splunk_mcp_client.models.tool_call_response import ToolCallResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ToolCallResponse from a JSON string
tool_call_response_instance = ToolCallResponse.from_json(json)
# print the JSON string representation of the object
print(ToolCallResponse.to_json())

# convert the object into a dict
tool_call_response_dict = tool_call_response_instance.to_dict()
# create an instance of ToolCallResponse from a dict
tool_call_response_from_dict = ToolCallResponse.from_dict(tool_call_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


