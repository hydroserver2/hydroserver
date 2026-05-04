# API Reference

## SensorThings API

The interactive documentation for this API is available at:

https://playground.hydroserver.org/api/sensorthings/v1.1/docs

### About

HydroServer implements the [OGC SensorThings API](https://www.ogc.org/standard/sensorthings/) standard, an open specification for connecting Internet of Things (IoT) sensors and their observations to the web. It provides a standardized REST interface for working with Things, Locations, Datastreams, Sensors, Observed Properties, and Observations — enabling interoperability with SensorThings-compliant clients and tools.

## Data Management API

The interactive documentation for this API is available at:

https://playground.hydroserver.org/api/data/docs

### About

This API contains the extended endpoints HydroServer provides outside of the SensorThings spec, transforming the overarching HydroServer API layer into a comprehensive data management tool. Specifically, the Data Management API introduces orchestration systems, data archival, and extended metadata such as units, processing levels, result qualifiers, photos, and tagging. It also contains database fields for storing controlled vocabularies. This API offers endpoints to access both your data and data shared by others in your system.

## Identity and Access Management API

The interactive documentation for this API is available at:

https://playground.hydroserver.org/api/auth/docs

### About

This API extends the SensorThings standard with user authentication and access control. This includes managing user accounts, grouping data into access controlled workspaces, and restricting select actions to with roles and API keys.