# How to Post Data Using the SensorThings API

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
