# Data Management API

This API is designed to enhance the [SensorThings standard](sensor-things-api.md), transforming it into a comprehensive data management tool. While the SensorThings standard offers a fundamental suite of endpoints for IoT device management, the Data Management API introduces features like site ownership
and datastream metadata elements, including processing levels and qualifier codes.

The Data Management API offers suite of endpoints to access both your data and data shared by others on HydroServer. By default, all data within the database is set to public. Consequently, invoking the "GET api/data/things" endpoint retrieves basic information for all hydrologic sites (referred to as "things") in the system, unless they have been specifically marked as private by their respective site owners.

## Endpoints

For the list of available endpoints and required parameters, check out the interactive docs at:

https://playground.hydroserver.org/api/data/docs

## Access Control

This API provides the ability for you to set your entire site or specific datastreams to private. For example,

```
# Pass {"isPrivate": true} as the request body to make your site visible
# only to you and the other owners of your site

PATCH api/data/things/{thing_id}/privacy
```

See the [Account Management API documentation](/api/account-management-api.md) for instructions on sending authenticated requests
