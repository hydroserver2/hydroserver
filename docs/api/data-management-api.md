# Data Management API

The purpose of this API is to extend the [SensorThings standard](sensor-things-api.md) into a fully functional data management API.
While SensorThings provides a core set of endpoints for managing internet of things (IoT) devices, the Data Management API adds the
concepts of people that own these IoT devices, organizations, and datastream metadata such as processing levels and qualifier codes.

The Data Management API gives you a full range of endpoints to work with the data you and others have stored on HydroServer. By default,
all data stored in the database is public, meaning a call to "GET api/data/things" will retrieve the basic information for all hydrologic
sites (things) in the system that haven't been explicitly set to private by their site owners.

## Access Control

User authentication is optional for most data management GET endpoints. Unauthorized requests will be able to view all
public data hosted by HydroServer. Authorized requests will view public data plus any data owned by the authenticated
user. PATCH, and DELETE requests require the user to be authenticated and an owner of the resources being modified.
POST requests require the user to be authenticated and will create a new resource owned by the authenticated user.

You may use either basic authentication or API access tokens to authenticate requests to the Data Management API.
See the account API documentation for additional instructions on how to use both of these authentication methods.

There are endpoints available for you to set your site and/or datastreams to private as well as add secondary owners to your site. For example,

```
# Pass {"isPrivate": true} as the request body to make your site visible
# Only to the owners of that site

PATCH api/data/things/{thing_id}/privacy
```

## Endpoints

Go to [https://beta.hydroserver2.org/api/data/docs](https://beta.hydroserver2.org/api/data/docs) for the comprehensive list of available endpoints
and the required parameters.

In addition, this section provides a quick overview of the endpoints. Portions of URLs
enclosed in angle brackets, such as {thing_id}, represent user provided parameters; these are typically UUIDs associated
with the record that will be returned or modified by the endpoint.

The Data Management API provides the following endpoints:

### Things

- **GET /things**: Retrieve a list of public and owned Things.
- **POST /things**: Create a new Thing owned by the authenticated user.
- **GET /things/{thing_id}**: Retrieve details for a single Thing record using the given Thing ID.
- **PATCH /things/{thing_id}**: Update properties of a Thing owned by the authenticated user.
- **DELETE /things/{thing_id}**: Delete a Thing. Authenticated user must be the primary owner.
- **PATCH /things/{thing_id}/ownership**: Update a Thing's ownership. Owners can be added or removed, and primary
  ownership can be transferred.
- **PATCH /things/{thing_id}/privacy**: Update the privacy of a Thing owned by the authenticated user to either public
  or private.
- **PATCH /things/{thing_id}/followership**: Toggle between following and not following a thing for an authenticated
  user who doesn't own the Thing.
- **GET /things/{thing_id}/metadata**: Get all custom metadata elements associated with the given Thing. Returned
  metadata elements include units, sensors, processing levels, and observed properties.
- **GET /things/{thing_id}/datastreams**: Get all datastreams associated with the given Thing ID.
- **GET /things/{thing_id}/photos**: Get a list of photo links associated with the given Thing ID.
- **POST /things/{thing_id}/photos**: Upload or delete photos associated with the given Thing ID owned by the
  authenticated user.

### Datastreams

- **GET /datastreams**: Retrieve a list of public and owned Datastreams.
- **POST /datastreams**: Create a new Datastream owned by the authenticated user.
- **GET /datastreams/{datastream_id}**: Retrieve details for a single Datastream record using the given Datastream ID.
- **PATCH /datastreams/{datastream_id}**: Update properties of a Datastream owned by the authenticated user.
- **DELETE /datastreams/{datastream_id}**: Delete a Datastream. Authenticated user must be the primary owner.

### Observed Properties

- **GET /observed-properties**: Retrieve a list of public and owned Observed Properties.
- **POST /observed-properties**: Create a new Observed Property owned by the authenticated user.
- **GET /observed-properties/{observed_property_id}**: Retrieve details for a single Observed Property record using the
  given Observed Property ID.
- **PATCH /observed-properties/{observed_property_id}**: Update properties of a Observed Property owned by the
  authenticated user.
- **DELETE /observed-properties/{observed_property_id}**: Delete a Observed Property. Authenticated user must be the
  primary owner.

### Processing Levels

- **GET /processing-levels**: Retrieve a list of public and owned Processing Levels.
- **POST /processing-levels**: Create a new Processing Level owned by the authenticated user.
- **GET /processing-levels/{processing_level_id}**: Retrieve details for a single Processing Level record using the
  given Processing Level ID.
- **PATCH /processing-levels/{processing_level_id}**: Update properties of a Processing Level owned by the authenticated
  user.
- **DELETE /processing-levels/{processing_level_id}**: Delete a Processing Level. Authenticated user must be the primary
  owner.

### Sensors

- **GET /sensors**: Retrieve a list of public and owned Sensors.
- **POST /sensors**: Create a new Sensor owned by the authenticated user.
- **GET /sensors/{sensor_id}**: Retrieve details for a single Sensor record using the given Sensor ID.
- **PATCH /sensors/{sensor_id}**: Update properties of a Sensor owned by the authenticated user.
- **DELETE /sensors/{sensor_id}**: Delete a Sensor. Authenticated user must be the primary owner.

### Units

- **GET /units**: Retrieve a list of public and owned Units.
- **POST /units**: Create a new Unit owned by the authenticated user.
- **GET /units/{unt_id}**: Retrieve details for a single Unit record using the given Unit ID.
- **PATCH /units/{unit_id}**: Update properties of a Unit owned by the authenticated user.
- **DELETE /units/{unit_id}**: Delete a Unit. Authenticated user must be the primary owner.

### Result Qualifiers

- **GET /result-qualifiers**: Retrieve a list of public and owned Result Qualifiers.
- **POST /result-qualifiers**: Create a new Result Qualifier owned by the authenticated user.
- **GET /result-qualifiers/{result_qualifier_id}**: Retrieve details for a single Result Qualifier record using the
  given Result Qualifier ID.
- **PATCH /result-qualifiers/{result_qualifier_id}**: Update properties of a Result Qualifier owned by the authenticated
  user.
- **DELETE /result-qualifiers/{result_qualifier_id}**: Delete a Result Qualifier. Authenticated user must be the primary
  owner.

### Data Loaders

- **GET /data-loaders**: Retrieve a list of public and owned Data Loaders.
- **POST /data-loaders**: Create a new Data Loader owned by the authenticated user.
- **GET /data-loaders/{data_loader_id}**: Retrieve details for a single Data Loader record using the given Data Loader
  ID.
- **PATCH /data-loaders/{data_loader_id}**: Update properties of a Data Loaders owned by the authenticated user.
- **DELETE /data-loaders/{data_loader_id}**: Delete a Data Loader. Authenticated user must be the primary owner.

### Data Sources

- **GET /data-sources**: Retrieve a list of public and owned Data Sources.
- **POST /data-sources**: Create a new Data Source owned by the authenticated user.
- **GET /data-sources/{data_source_id}**: Retrieve details for a single Data Source record using the given Data Source
  ID.
- **PATCH /data-sources/{data_source_id}**: Update properties of a Data Source owned by the authenticated user.
- **DELETE /data-sources/{data_source_id}**: Delete a Data Source. Authenticated user must be the primary owner.
