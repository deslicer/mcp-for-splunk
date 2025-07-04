# ToolListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**jsonrpc** | **str** |  | [optional] 
**result** | [**ToolListResponseResult**](ToolListResponseResult.md) |  | [optional] 

## Example

```python
from splunk_mcp_client.models.tool_list_response import ToolListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ToolListResponse from a JSON string
tool_list_response_instance = ToolListResponse.from_json(json)
# print the JSON string representation of the object
print(ToolListResponse.to_json())

# convert the object into a dict
tool_list_response_dict = tool_list_response_instance.to_dict()
# create an instance of ToolListResponse from a dict
tool_list_response_from_dict = ToolListResponse.from_dict(tool_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


