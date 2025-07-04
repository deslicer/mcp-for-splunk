# ToolCallRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**jsonrpc** | **str** |  | 
**method** | **str** |  | 
**params** | [**ToolCallRequestParams**](ToolCallRequestParams.md) |  | 
**id** | **str** |  | [optional] 

## Example

```python
from splunk_mcp_client.models.tool_call_request import ToolCallRequest

# TODO update the JSON string below
json = "{}"
# create an instance of ToolCallRequest from a JSON string
tool_call_request_instance = ToolCallRequest.from_json(json)
# print the JSON string representation of the object
print(ToolCallRequest.to_json())

# convert the object into a dict
tool_call_request_dict = tool_call_request_instance.to_dict()
# create an instance of ToolCallRequest from a dict
tool_call_request_from_dict = ToolCallRequest.from_dict(tool_call_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


