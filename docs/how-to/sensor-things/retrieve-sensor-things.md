# How to Retrieve Data Using the SensorThings API

The HydroServer SensorThings API allows you to access various sensor-related data via HTTP GET requests. SensorThings
provides several patterns for retrieving subsets of monitoring data which will be covered here.

## Expansion

By default, each endpoint returns only fields associated with itself and links to related records. You can expand
related record details in a response using the **$expand** parameter. This parameter can be used to expand multiple
related records or even nested related records. Multiple related component names should be separated by a comma, and
nested components should use a forward slash. For example, the following endpoint will return a list of Thing records
with related Locations, Datastreams, and Sensor records nested into the response:

```
/Things?$expand=Locations,Datastreams/Sensor
```

## Filtering

SensorThings supports a wide array of filtering options. Filters can be applied to a request using the **$filter**
query parameter. Filter values are generally constructed using a field, operator, and value separated by spaces, or
by using a filter function. For example, the following endpoint will return all Observation records with a
phenomenonTime between July 1, 2023, and August 1, 2023.

```
/Observations?$filter=phenomenonTime gt 2023-07-01T00:00:00 and phenomenonTime lt 2023-08-01T00:00:00
```

**Note:** Filters for HydroServer SensorThings are still under development and are not currently all supported. At the
moment, only comparison operators and logical operators are supported.

## Selection

You can limit the number of fields included in a SensorThings response using the **$select** query parameter. The
following endpoint will return a list of Things with only the Thing name included in the response.

```
/Things?&select=name
```

## Ordering

Responses can be ordered using the **$orderby** query parameter. Multiple fields can be passed to this parameter
separated by a comma, and the direction can be specified by adding **asc** or **desc** after the field name separated
by a space. Fields in expanded records can also be referenced using a forward slash. Ordering will be applied in the
order the fields are entered. For example the following endpoint will return a list of Datastreams ordered first by
Datastream name, then by Sensor name.

```
/Datastrams?&expand=Sensor&$orderby=name asc,Sensor/name asc
```

## Pagination

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

## Nested Resource Paths

Records can be filtered using nested resource paths to query related records. For example, the following endpoint would
get all Datastream records associated with the given Thing ID.

```
/Things('00000000-0000-0000-0000-000000000000')/Datastreams
```

## Observation Data Arrays

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

# Python Data Retrieval Examples

This section contains several examples showing how to retrieve data from the SensorThings API using the Python
"requests" module.

## Retrieve a list of Things using server-side pagination, ordering, and filtering.

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

## Retrieve a Datastream entity with related entities expanded.

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

### Retrieve a set of Observations belonging to a Datastream in the dataArray format.

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
