# HydroServer SensorThings API

The HydroServer SensorThings API is a Django implementation of the Open Geospatial Consortium
SensorThings specification. We recommend reading the [SensorThings overview](/guide/sensor-things.md)
before reading this.

## Endpoints

The list of endpoints for this API can be found on our interactive docs page at:

https://playground.hydroserver.org/api/sensorthings/v1.1/docs

<!-- ## SensorThings Base URL

HydroServer supports version 1.1 of the SensorThings specification. The base URL for HydroServer
SensorThings is:

```
https://playground.hydroserver.org/api/sensorthings/v1.1/
```

This URL will return a list of capabilities currently supported by this SensorThings implementation. -->

<!-- This section provides an overview of all endpoints provided by the HydroServer SensorThings API. Portions of URLs
enclosed in angle brackets, such as {thing_id}, represent user provided parameters; these are typically UUIDs associated
with the record that will be returned by the endpoint.

The HydroServer SensorThings API provides the following endpoints:

### Things

- **GET /Things**: Retrieve a list of Things.
- **GET /Things('{thing_id}')**: Retrieve details for a single Thing record using the given Thing ID.

**Note:** In HydroServer, "Things" typically refers to monitoring sites where
one or more sensors have been set up to record observations.

### Locations

- **GET /Locations**: Retrieve a list of Locations.
- **GET /Locations('{location_id}')**: Retrieve details for a single Location record using the given Location ID.

**Note:** In HydroServer, each Location will be associated with only one Thing, but they can still be queried separately
if needed.

### Historical Locations

- **GET /HistoricalLocations**: Retrieve a list of Historical Locations.
- **GET /HistoricalLocations('{historical_location_id}')**: Retrieve details for a single Historical Locations using the
  given Historical Location ID.

**Note:** HydroServer does not currently support the creation of historical locations of things. These endpoints have
not been disabled, but be aware that the responses of these endpoints will always be empty.

### Sensors

- **GET /Sensors**: Retrieve a list of Sensors.
- **GET /Sensors('{sensor_id}')**: Retrieve details for a single Sensor record using the given Sensor ID.

### Observed Properties

- **GET /ObservedProperties**: Retrieve a list of Sensors.
- **GET /ObservedProperties('{observed_property_id}')**: Retrieve details for a single Observed Property record using the
  given Observed Property ID.

### Datastreams

- **GET /Datastreams**: Retrieve a list of Datastreams.
- **GET /Datastreams('{datastream_id}')**: Retrieve details for a single Datastream record using the given Datastream ID.

### Observations

- **GET /Observations**: Retrieve a list of Observations.
- **POST /Observations**: Create one or more new Observations.
- **GET /Observations('{observation_id}')**: Retrieve details for a single Observation record using the given Observation
  ID.
- **PATCH /Observations('{observation_id}')**: Update an existing Observation record with the given Observation ID.
- **DELETE /Observations('{observation_id}')**: Delete an existing Observation record with the given Observation ID.

### Features of Interest

- **GET /FeaturesOfInterest**: Retrieve a list of Features of Interest.
- **GET /FeaturesOfInterest('{feature_of_interest_id}')**: Retrieve details for a single Feature of Interest record using
  the given Feature of Interest ID.

**Note:** HydroServer does not currently support the creation of features of interest of observations. These endpoints
have not been disabled, but be aware that the responses of these endpoints will always be empty. -->

## Retrieving Data

The HydroServer SensorThings API allows you to access various sensor-related data via HTTP GET requests. SensorThings
provides several patterns for retrieving subsets of monitoring data which will be covered here.

### Expansion

By default, each endpoint returns only fields associated with itself and links to related records. You can expand
related record details in a response using the **$expand** parameter. This parameter can be used to expand multiple
related records or even nested related records. Multiple related component names should be separated by a comma, and
nested components should use a forward slash. For example, the following endpoint will return a list of Thing records
with related Locations, Datastreams, and Sensor records nested into the response:

```
/Things?$expand=Locations,Datastreams/Sensor
```

### Filtering

SensorThings supports a wide array of filtering options. Filters can be applied to a request using the **$filter**
query parameter. Filter values are generally constructed using a field, operator, and value separated by spaces, or
by using a filter function. For example, the following endpoint will return all Observation records with a
phenomenonTime between July 1, 2023, and August 1, 2023.

```
/Observations?$filter=phenomenonTime gt 2023-07-01T00:00:00 and phenomenonTime lt 2023-08-01T00:00:00
```

**Note:** Filters for HydroServer SensorThings are still under development and are not currently all supported. At the
moment, only comparison operators and logical operators are supported.

### Selection

You can limit the number of fields included in a SensorThings response using the **$select** query parameter. The
following endpoint will return a list of Things with only the Thing name included in the response.

```
/Things?&select=name
```

### Ordering

Responses can be ordered using the **$orderby** query parameter. Multiple fields can be passed to this parameter
separated by a comma, and the direction can be specified by adding **asc** or **desc** after the field name separated
by a space. Fields in expanded records can also be referenced using a forward slash. Ordering will be applied in the
order the fields are entered. For example the following endpoint will return a list of Datastreams ordered first by
Datastream name, then by Sensor name.

```
/Datastrams?&expand=Sensor&$orderby=name asc,Sensor/name asc
```

### Pagination

You can paginate responses using the **$top**, **$skip**, and **$count** query parameters on entity collection requests.
Pagination will be applied after filtering and ordering. The **$top** parameter is an integer that tells the server how
many entities to include in the response. The **$skip** parameter is an integer that tells the server to skip entities
from the beginning of the query. The **$count** parameter returns the total number of matched entities before **$top**
and **$skip** are applied.

Additionally, GET collection responses will automatically generate an attribute called "@iot.nextLink"
which includes the **$skip** and **$top** parameters needed for the next page of data if it exists. Subsequent page
sizes will be based on your initial value for **$top**, which is set to 100 by default for all endpoints except
Observations, which is 1000 by default.

The following endpoint would return up to five Datastream entities, starting at the 11th entity stored in the
HydroServer database, and also include the count of all Datastreams available:

```
/Datastreams?$top=5&$skip=10&$count=true
```

### Nested Resource Paths

Records can be filtered using nested resource paths to query related records. For example, the following endpoint would
get all Datastream records associated with the given Thing ID.

```
/Things('00000000-0000-0000-0000-000000000000')/Datastreams
```

### Observation Data Arrays

The GET Observations endpoint has a special query parameter called **resultFormat** which you can use to request a less
verbose response from the server. This is especially useful when querying large sets of observation data. The following
endpoint would return a data array response:

```
/Observations?$resultFormat=dataArray
```

Data array responses can return observations for one or more datastreams, but only define the field names and
Datastream identifier once in the response. The "components" attribute can be thought of as the data headers while
the "dataArray" attribute contains a matrix of the time/value pairs.

The following is an example of a data array response:

```json
{
  "values": [
    {
      "Datastream@iot.navigationLink": "https://www.hydroserver.org/api/sensorthings/v1.1/Datastreams('00000000-0000-0000-0000-000000000000')",
      "components": ["resultTime", "result"],
      "dataArray": [
        ["2022-02-01T10:10:10Z", 32.2],
        ["2022-03-01T10:10:10Z", 33.8]
      ]
    }
  ],
  "@iot.nextLink": "https://www.hydroserver.org/api/sensorthings/v1.1/Observations?$top=2&$skip=2"
}
```

### Python Data Retrieval Examples

This section contains several examples showing how to retrieve data from the SensorThings API using the Python
"requests" module.

#### Retrieve a list of Things using server-side pagination, ordering, and filtering.

```python
import requests
import json

hydroserver_sensorthings_api_url = 'https://www.hydroserver.com/api/sensorthings/v1.1'
request_url = f'{hydroserver_sensorthings_api_url}/Things'

page_length = 50
page = 1

query_parameters = {
   '$top': page_length,
   '$skip': page_length * (page - 1),
   '$count': True,
   '$filter': None,
   '$orderby': None
}

response = requests.get(
   request_url,
   params=query_parameters
)

if response.status_code == 200:
   things = json.loads(response.content)
```

#### Retrieve a Datastream entity with related entities expanded.

```python
import requests
import json

hydroserver_sensorthings_api_url = 'https://www.hydroserver.com/api/sensorthings/v1.1'
request_url = f'{hydroserver_sensorthings_api_url}/Datastreams'

query_parameters = {
   '$expand': 'ObservedProperty,Sensor,Thing/Locations'
}

response = requests.get(
   request_url,
   params=query_parameters
)

if response.status_code == 200:
   datastreams = json.loads(response.content)
```

#### Retrieve a set of Observations belonging to a Datastream in the dataArray format.

```python
import requests
import json

hydroserver_sensorthings_api_url = 'https://www.hydroserver.com/api/sensorthings/v1.1'
datastream_id = ''
request_url = f"{hydroserver_sensorthings_api_url}/Datastreams('{datastream_id}')/Observations"

query_parameters = {
   '$resultFormat': 'dataArray'
}

response = requests.get(
   request_url,
   params=query_parameters
)

if response.status_code == 200:
   observations = json.loads(response.content)
```

## Posting Data

The HydroServer SensorThings API currently only supports posting Observations data. Other metadata can be posted or
modified using the Data Management API.

### Observations

Observations can be posted to HydroServer via the SensorThings API using two different methods. The first uses a more
verbose body and can be used to post one Observation per request. The example POST body below shows how to format this
type of request.

```json
{
  "phenomenonTime": "2023-06-01T10:05:00Z",
  "result": 32.4,
  "Datastream": {
    "@iot.id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
}
```

The second posting option uses the dataArray format and can post multiple Observation records in a single request. The
body contains an array of Observation chunks for each datastream included in the request. Each Observation chunk will
include the Datastream ID, a "components" attribute containing an array of fields the chunk includes, and a "dataArray"
attribute containing the data values. The example POST body below shows how to format a dataArray request containing
Observations for two different Datastreams.

```json
[
  {
    "Datastream": {
      "@iot.id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    },
    "components": ["phenomenonTime", "result"],
    "dataArray": [
      ["2023-06-01T10:05:00Z", 32.4],
      ["2023-06-01T10:10:00Z", 33.8],
      ["2023-06-01T10:15:00Z", 31.9]
    ]
  },
  {
    "Datastream": {
      "@iot.id": "18239c87-2c46-4714-9046-2eaf995977a1"
    },
    "components": ["phenomenonTime", "result"],
    "dataArray": [
      ["2023-06-01T10:05:00Z", 102.3],
      ["2023-06-01T10:10:00Z", 133.4],
      ["2023-06-01T10:15:00Z", 120.5]
    ]
  }
]
```

### Python Data Posting Examples

This section contains several examples showing how to post data to the SensorThings API using the Python
"requests" module.

#### Post a single Observation to the SensorThings API

```python
import requests

hydroserver_sensorthings_api_url = 'https://www.hydroserver.com/api/sensorthings/v1.1'
request_url = f'{hydroserver_sensorthings_api_url}/Observations'
auth = ('john@example.com', '********')

post_body = {
   'Datastream': {
      '@iot.id': 'e361d5f7-f804-4016-9c33-430fa51d76be'
   },
   'phenomenonTime': '2023-07-01T00:00:00Z',
   'result': 98.3
}

response = requests.post(
   request_url,
   json=post_body,
   auth=auth
)

if response.status_code == 201:
   print('Observation was posted successfully.')
```

#### Post several Observations to the SensorThings API using the dataArray format

```python
import requests

hydroserver_sensorthings_api_url = 'https://www.hydroserver.com/api/sensorthings/v1.1'
request_url = f'{hydroserver_sensorthings_api_url}/CreateObservations'
auth = ('john@example.com', '********')

post_body = [
   {
      'Datastream': {
         '@iot.id': 'e361d5f7-f804-4016-9c33-430fa51d76be'
      },
      'components': ['phenomenonTime', 'result'],
      'dataArray': [
         ['2023-07-02T00:00:00Z', 99.1],
         ['2023-07-03T00:00:00Z', 87.3],
         ['2023-07-04T00:00:00Z', 88.0],
         ['2023-07-05T00:00:00Z', 95.8],
         ['2023-07-06T00:00:00Z', 93.3],
      ]
   }
]

response = requests.post(
   request_url,
   json=post_body,
   auth=auth
)

if response.status_code == 201:
   print('Observations were posted successfully.')
```

## Authentication

See the [Identity and Access Management API documentation](/api/identity-and-access-management-api.md) for instructions on how to send
authenticated requests.

This API supports requests over both HTTPS and HTTP connections due to limitations of some datalogger devices.
We highly recommend connecting via HTTPS whenever possible. It is also highly
recommended to use token based authentication rather than basic authentication, especially when using HTTP connections.
Using basic authentication over unencrypted HTTP connections makes your account highly vulnerable to security threats.
