# ToolCallRequestParams


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**arguments** | **object** |  | [optional] 

## Example

```python
from splunk_mcp_client.models.tool_call_request_params import ToolCallRequestParams

# TODO update the JSON string below
json = "{}"
# create an instance of ToolCallRequestParams from a JSON string
tool_call_request_params_instance = ToolCallRequestParams.from_json(json)
# print the JSON string representation of the object
print(ToolCallRequestParams.to_json())

# convert the object into a dict
tool_call_request_params_dict = tool_call_request_params_instance.to_dict()
# create an instance of ToolCallRequestParams from a dict
tool_call_request_params_from_dict = ToolCallRequestParams.from_dict(tool_call_request_params_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


