# GetKvstoreDataParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**collection** | **str** |  | 
**app** | **str** |  | [optional] [default to 'None']
**query** | **str** |  | [optional] [default to 'None']

## Example

```python
from splunk_mcp_client.models.get_kvstore_data_parameters import GetKvstoreDataParameters

# TODO update the JSON string below
json = "{}"
# create an instance of GetKvstoreDataParameters from a JSON string
get_kvstore_data_parameters_instance = GetKvstoreDataParameters.from_json(json)
# print the JSON string representation of the object
print(GetKvstoreDataParameters.to_json())

# convert the object into a dict
get_kvstore_data_parameters_dict = get_kvstore_data_parameters_instance.to_dict()
# create an instance of GetKvstoreDataParameters from a dict
get_kvstore_data_parameters_from_dict = GetKvstoreDataParameters.from_dict(get_kvstore_data_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


