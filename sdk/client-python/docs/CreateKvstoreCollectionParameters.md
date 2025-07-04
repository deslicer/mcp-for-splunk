# CreateKvstoreCollectionParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**app** | **str** |  | 
**collection** | **str** |  | 
**fields** | **str** |  | [optional] [default to 'None']
**accelerated_fields** | **str** |  | [optional] [default to 'None']
**replicated** | **bool** |  | [optional] [default to True]

## Example

```python
from splunk_mcp_client.models.create_kvstore_collection_parameters import CreateKvstoreCollectionParameters

# TODO update the JSON string below
json = "{}"
# create an instance of CreateKvstoreCollectionParameters from a JSON string
create_kvstore_collection_parameters_instance = CreateKvstoreCollectionParameters.from_json(json)
# print the JSON string representation of the object
print(CreateKvstoreCollectionParameters.to_json())

# convert the object into a dict
create_kvstore_collection_parameters_dict = create_kvstore_collection_parameters_instance.to_dict()
# create an instance of CreateKvstoreCollectionParameters from a dict
create_kvstore_collection_parameters_from_dict = CreateKvstoreCollectionParameters.from_dict(create_kvstore_collection_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


