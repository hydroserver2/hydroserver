# Data Management API

This API is designed to enhance the [SensorThings standard](sensor-things-api.md), transforming it into a comprehensive data management tool. While the SensorThings standard offers a fundamental suite of endpoints for IoT device management, the Data Management API introduces additional features such as the ability to control data access through workspaces, ownership, collaborators, and roles. It also incorporates new metadata elements for quality control and data management, including processing levels, result qualifiers, photos, and site tagging.

The Data Management API offers suite of endpoints to access both your data and data shared by others on HydroServer. By default, all data within the database is set to public. Consequently, invoking the "GET api/data/things" endpoint retrieves basic information for all hydrologic sites (referred to as "things") in the system, unless they have been specifically marked as private by their respective site owners.

## Endpoints

For the list of available endpoints and required parameters, check out the interactive docs at:

https://playground.hydroserver.org/api/data/docs
