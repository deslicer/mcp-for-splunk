# ManageAppsParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action** | **str** |  | 
**app_name** | **str** |  | 

## Example

```python
from splunk_mcp_client.models.manage_apps_parameters import ManageAppsParameters

# TODO update the JSON string below
json = "{}"
# create an instance of ManageAppsParameters from a JSON string
manage_apps_parameters_instance = ManageAppsParameters.from_json(json)
# print the JSON string representation of the object
print(ManageAppsParameters.to_json())

# convert the object into a dict
manage_apps_parameters_dict = manage_apps_parameters_instance.to_dict()
# create an instance of ManageAppsParameters from a dict
manage_apps_parameters_from_dict = ManageAppsParameters.from_dict(manage_apps_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


