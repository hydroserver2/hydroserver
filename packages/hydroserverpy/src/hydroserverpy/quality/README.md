# HydroServer Python Client - Quality Control

The hydroserverpy quality control package provides several methods for performing quality control operations on observations datasets. This guide will provide examples explaining how to retrieve data for quality control and run quality control operations. Quality controlled data can be uploaded back to HydroServer as a new datastream with an appropriate processing level.

## Quality Control Guide with Examples

To perform quality control operations, you must connect to HydroServer.

```python
from hydroserverpy import HydroServer

# Initialize HydroServer connection with credentials.
hs_api = HydroServer(
    host='https://playground.hydroserver.org',
    username='user@example.com',
    password='******'
)
```

Select a datastream you want to perform quality control on and fetch its observations. You can optionally include result qualifier information with the fetched observations.

```python
from datetime import datetime

...

# Get a Datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get Observations of a Datastream between two timestamps
observations_df = datastream.get_observations(
    include_quality=True,
    start_time=datetime(year=2023, month=1, day=1),
    end_time=datetime(year=2023, month=12, day=31)
)
```

Once you have a DataFrame of observations, you will need to initialize a quality control session.

```python
from hydroserverpy import HydroServerQualityControl

...

# Initialize quality control session.
hs_quality_control = HydroServerQualityControl(
    datastream_id=datastream.uid,
    observations=observations_df
)
```

You are now ready to begin performing quality control operations on the dataset. You can access the modified observations using the `observations` property. Your work will not be saved back to HydroServer until you upload the quality controlled observations to a new datastream.

```python
# Get quality controlled observations DataFrame.
quality_controlled_observations = hs_quality_control.observations
```

### Example: Find Gaps

```python
# Find gaps in observations given an expected 15 minute interval.
hs_quality_control.find_gaps(
    time_value=15,
    time_unit='m'
)
```

