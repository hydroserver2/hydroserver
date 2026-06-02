# Using the Python Client

HydroServer's Python client library `hydroserverpy` allows you to programmatically interact with HydroServer in a Python environment.

To install hydroserverpy from PyPI, run the following command:

```bash
pip install hydroserverpy
```

To perform data management operations, you must connect to HydroServer.

```python
from hydroserverpy import HydroServer

# Initialize HydroServer connection with credentials.
hs_api = HydroServer(
    host='https://playground.hydroserver.org',
    email='user@example.com',
    password='******'
)
```

The hydroserverpy connection instance exposes the following types of core data and metadata you can retrieve or create, either as a collection or by ID using the `list`, `get`, or `create` methods of the associated property:

- workspaces
- things
- datastreams
- sensors
- units
- processinglevels
- observedproperties
- resultqualifiers
- dataconnections
- etltasks
- monitoringtasks
- monitoringrules
- ratingcurves
- dataproducttasks
- dataproducttransformations

## Collections

Many HydroServer endpoints return _collections_ of resources. These collections provide access to paginated lists of objects along with convenience methods for navigating and retrieving data.

All resource types listed below have a `list` method that accepts:

- `page`: page number (1-indexed)
- `page_size`: number of items per page
- `order_by`: list of fields to order by (prefix with `-` for descending order)
- `fetch_all`: if `True`, retrieves all items across all pages using a given page size.
- Additional resource-specific filters

By default, HydroServer returns up to 100 items per page. Most endpoints allow up to 1,000.

Collection data is accessible through the `.items` property on the returned collection object.

---

### Example: Access Collection Items

```python
workspaces = hs_api.workspaces.list()

for workspace in workspaces.items:
    print(workspace.name)
```

### Example: Collection Pagination

```python
# Fetch all workspaces
all_workspaces = hs_api.workspaces.list(fetch_all=True)

# Retrieve page 2 of workspaces, 5 per page
paginated = hs_api.workspaces.list(page_size=5, page=2)

# Navigate between pages
next_page = paginated.next_page()
previous_page = paginated.previous_page()

# Fetch all remaining pages for an existing collection
full_collection = paginated.fetch_all()
```

### Example: Collection Ordering

```python
# Order by name ascending
ordered = hs_api.workspaces.list(order_by=["name"])

# Order by name descending, then by privacy
multi_ordered = hs_api.workspaces.list(order_by=["-name", "is_private"])
```

### Example: Collection Filtering

```python
# Filter for public workspaces
public = hs_api.workspaces.list(is_private=False)

# Filter for private workspaces you're associated with
private_yours = hs_api.workspaces.list(is_private=True, is_associated=True)
```

## Workspaces

Workspaces in HydroServer are used to organize and manage access to your data. All user-managed resources in HydroServer are created within the context of a workspace. Each workspace has one owner and can have any number of collaborators with varying levels of access to resources within the workspace. The examples below demonstrate how to use hydroserverpy to manage workspaces.

---

### Example: Get Workspaces

```python
# Get all available workspaces
public_workspaces = hs_api.workspaces.list()

# Get all workspaces you are associated with
your_workspaces = hs_api.workspaces.list(is_associated=True)

# Get a workspace by ID
workspace = hs_api.workspaces.get(uid="00000000-0000-0000-0000-000000000000")
```

### Example: Get Workspace Resources

```python
workspace = hs_api.workspaces.get(uid="00000000-0000-0000-0000-000000000000")

# Get all collaborators for a workspace
workspace_collaborators = workspace.collaborators

# Get all API keys for a workspace
workspace_api_keys = workspace.apikeys

# Get all roles within a workspace
workspace_roles = workspace.roles

# Get all things within a workspace
workspace_things = workspace.things

# Get all observed properties within a workspace
workspace_observed_properties = workspace.observedproperties

# Get all units within a workspace
workspace_units = workspace.units

# Get all processing levels within a workspace
workspace_processing_levels = workspace.processinglevels

# Get all sensors within a workspace
workspace_sensors = workspace.sensors

# Get all data connections within a workspace
workspace_data_connections = workspace.dataconnections

# Get all tasks within a workspace
workspace_tasks = workspace.tasks
```

### Example: Create a Workspace

```python
# Create a new workspace in HydroServer
new_workspace = hs_api.workspaces.create(
    name="New Workspace",
    is_private=False
)
```

### Example: Modify a Workspace

```python
workspace = hs_api.workspaces.get(uid="00000000-0000-0000-0000-000000000000")

# Update the name and privacy settings of a workspace
workspace.name = "New Workspace Name"
workspace.is_private = True
workspace.save()
```

### Example: Manage Workspace Collaborators and Ownership

```python
workspace = hs_api.workspaces.get(uid="00000000-0000-0000-0000-000000000000")

# Get roles that can be assigned to workspace collaborators
roles = hs_api.roles.list(is_user_role=True)

# Add a collaborator to a workspace
workspace.add_collaborator(
    email="user@example.com",                    # Must be the email of an active HydroServer user.
    role="00000000-0000-0000-0000-000000000000"  # You can use either the UUID of the role, or the role object.
)

# Modify a collaborator's role
workspace.edit_collaborator_role(
    email="user@example.com",
    role="00000000-0000-0000-0000-000000000000"
)

# Remove a collaborator
workspace.remove_collaborator(
    email="user@example.com"
)

# Initiate transfer of workspace ownership to another user
workspace.transfer_ownership(
    email="user@example.com"
)

# Accept pending ownership transfer (Must be accepted by the user receiving the workspace)
workspace.accept_ownership_transfer()

# Cancel pending ownership transfer
workspace.cancel_ownership_transfer()
```

## Things

Things (or sites) are one of the core data elements managed in HydroServer. Things represent a location or site at which one or more datastreams of observations are collected. All datastreams in HydroServer must be associated with a thing/site. The examples below demonstrate how to use hydroserverpy to manage things in HydroServer.

---

### Example: Get Things

```python
# Get all visible things
public_things = hs_api.things.list()

# Get things belonging to a workspace
workspace_things = hs_api.things.list(workspace="00000000-0000-0000-0000-000000000000")

# Fetch things within a bounding box
bounded_things = hs_api.things.list(bbox=(-112.166,41.369,-111.402,42.999))

# Filter things by custom tag
filtered_things = hs_api.things.list(tag=("TagKey", "TagValue"))

# Get thing with a given ID
thing = hs_api.things.get(uid="00000000-0000-0000-0000-000000000000")
```

### Example: Create Thing

```python
# Create a new thing in HydroServer
new_thing = hs_api.things.create(
    name="My Site",
    description="This is a site that records environmental observations.",
    sampling_feature_type="Site",
    sampling_feature_code="OBSERVATION_SITE",
    site_type="Atmosphere",
    latitude=41.7390,
    longitude=-111.7957,
    elevation_m=1414.0,
    elevation_datum="EGM96",
    state="UT",
    county="Cache",
    country="US",
    data_disclaimer="WARNING: These data may be provisional and subject to revision.",
    is_private=False,
    workspace="00000000-0000-0000-0000-000000000000"
)
```

Each of the methods above will return one or more Thing objects. The examples below show the main properties and methods available to a Thing object.

### Example: Modify a Thing

```python
# Get a thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the thing.
thing.name = 'Updated Site Name'
thing.description = 'This site metadata has been modified.'
thing.is_private = True

# Save the changes back to HydroServer.
thing.save()
```

### Example: Manage Thing Tags

```python
# Get a thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Get thing tags
tags = thing.tags

# Add a tag to a thing
thing.add_tag(
    key='Region',
    value='A'
)

# Modify a thing's tag
thing.update_tag(
    key='Region',
    value='B'
)

# Delete a thing's tag
thing.delete_tag(key='Region')
```

### Example: Manage Thing File Attachments

```python
# Get a thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Get thing photos
file_attachments = thing.file_attachments

# Add a file attachment to a thing
with open('/path/to/my/myfile.png', 'rb') as file_attachment:
    thing.add_file_attachment(
        file=file_attachment,
        file_attachment_type='Photo'
    )

# Delete a thing's file attachment
thing.delete_file_attachment(name='myfile.png')
```

### Example: Get Datastreams of a Thing

```python
# Get a thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Fetch datastreams of the thing
datastreams = thing.datastreams
```

### Example: Refresh Thing data from HydroServer

```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh thing data from HydroServer
thing.refresh()
```

### Example: Delete Thing from HydroServer

```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the thing from HydroServer
thing.delete()
```

## Observed Properties

Observed properties are used in HydroServer to represent the physical property being observed and stored in a datastream. The examples below demonstrate the actions you can take to manage observed properties in HydroServer.

---

### Example: Get Observed Properties

```python
# Get all observed properties
observed_properties = hs_api.observedproperties.list()

# Get observed properties belonging to a workspace
workspace_observed_properties = hs_api.observedproperties.list(workspace="00000000-0000-0000-0000-000000000000")

# Get observed property with a given ID
observed_property = hs_api.observedproperties.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Observed Property

```python
# Create a new observed property in HydroServer
new_observed_property = hs_api.observedproperties.create(
    name='Temperature',
    definition='Air Temperature',
    description='Air temperature',
    observed_property_type='Climate',
    code='AirTemp',
    workspace='00000000-0000-0000-0000-000000000000'
)
```

Each of the methods above will return one or more ObservedProperty objects. The examples below show the main properties and methods available to an ObservedProperty object.

### Example: Modify an Observed Property

```python
# Get an observed property
observed_property = hs_api.observedproperties.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Observed Property.
observed_property.name = 'Updated Observed Property Name'

# Save the changes back to HydroServer.
observed_property.save()
```

### Example: Refresh Observed Property data from HydroServer

```python
# Get an observed property
observed_property = hs_api.observedproperties.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh observed property data from HydroServer
observed_property.refresh()
```

### Example: Delete Observed Property from HydroServer

```python
# Get an observed property
observed_property = hs_api.observedproperties.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the observed property from HydroServer
observed_property.delete()
```

## Units

Units are used in HydroServer to describe the physical quantity represented by the result of an observation in a datastream. The examples below demonstrate the actions you can take to manage units in HydroServer.

---

### Example: Get Units

```python
# Get all units
units = hs_api.units.list()

# Get units belonging to a workspace
workspace_units = hs_api.units.list(workspace="00000000-0000-0000-0000-000000000000")

# Get unit with a given ID
unit = hs_api.units.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Unit

```python
# Create a new unit in HydroServer
new_unit = hs_api.units.create(
    name='Degree Celsius',
    symbol='C',
    definition='Degree Celsius',
    unit_type='Temperature',
    workspace='00000000-0000-0000-0000-000000000000'
)
```

Each of the methods above will return one or more Unit objects. The examples below show the main properties and methods available to a Unit object.

### Example: Modify a Unit

```python
# Get a unit
unit = hs_api.units.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Unit.
unit.name = 'Updated Unit Name'

# Save the changes back to HydroServer.
unit.save()
```

### Example: Refresh Unit data from HydroServer

```python
# Get a unit
unit = hs_api.units.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh unit data from HydroServer
unit.refresh()
```

### Example: Delete Unit from HydroServer

```python
# Get a unit
unit = hs_api.units.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the unit from HydroServer
unit.delete()
```

## Sensors

Sensors are used in HydroServer to describe the sensor/method used to make an environmental observation. The examples below demonstrate the actions you can take to manage sensors in HydroServer.

---

### Example: Get Sensors

```python
# Get all sensors
sensors = hs_api.sensors.list()

# Get sensors belonging to a workspace
workspace_sensors = hs_api.sensors.list(workspace="00000000-0000-0000-0000-000000000000")

# Get sensor with a given ID
sensor = hs_api.sensors.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Sensor

```python
# Create a new sensor in HydroServer
new_sensor = hs_api.sensors.create(
    name='Environmental Sensor',
    description='An environmental sensor.',
    encoding_type='application/json',
    manufacturer='Campbell Scientific',
    sensor_model='A',
    sensor_model_link='https://link/to/sensor/model/info',
    method_type='Sensor',
    method_link='https://link/to/method/info',
    method_code='SENSOR_A',
    workspace='00000000-0000-0000-0000-000000000000'
)
```

Each of the methods above will return one or more sensor objects. The examples below show the main properties and methods available to a sensor object.

### Example: Modify a Sensor

```python
# Get a sensor
sensor = hs_api.sensors.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Sensor.
sensor.name = 'Updated Sensor Name'

# Save the changes back to HydroServer.
sensor.save()
```

### Example: Refresh Sensor data from HydroServer

```python
# Get a sensor
sensor = hs_api.sensors.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh sensor data from HydroServer
sensor.refresh()
```

### Example: Delete Sensor from HydroServer

```python
# Get a sensor
sensor = hs_api.sensors.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the sensor from HydroServer
sensor.delete()
```

## Processing Levels

Processing levels are used in HydroServer to describe the level of processing observations of a datastream have been subject to. The examples below demonstrate the actions you can take to manage processing levels in HydroServer.

---

### Example: Get Processing Levels

```python
# Get all processing levels
processing_levels = hs_api.processinglevels.list()

# Get processing levels belonging to a workspace
workspace_processing_levels = hs_api.processinglevels.list(workspace="00000000-0000-0000-0000-000000000000")

# Get processing level with a given ID
processing_level = hs_api.processinglevels.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Processing Level

```python
# Create a new processing level in HydroServer
new_processing_level = hs_api.processinglevels.create(
    code='0',
    definition='Raw',
    explanation='Data have not been processed or quality controlled.',
    workspace='00000000-0000-0000-0000-000000000000'
)
```

Each of the methods above will return one or more processing level objects. The examples below show the main properties and methods available to a processing level object.

### Example: Modify a Processing Level

```python
# Get a processing level
processing_level = hs_api.processinglevels.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the processing level.
processing_level.code = 'Updated Processing Level Code'

# Save the changes back to HydroServer.
processing_level.save()
```

### Example: Refresh Processing Level data from HydroServer

```python
# Get a processing level
processing_level = hs_api.processinglevels.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh processing level data from HydroServer
processing_level.refresh()
```

### Example: Delete Processing Level from HydroServer

```python
# Get a processing level
processing_level = hs_api.processinglevels.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the processing level from HydroServer
processing_level.delete()
```

## Result Qualifiers

Result qualifiers are used in HydroServer to annotate observations during quality control or other processing steps. The examples below demonstrate the actions you can take to manage result qualifiers in HydroServer.

---

### Example: Get Result Qualifiers

```python
# Get all result qualifiers
result_qualifiers = hs_api.resultqualifiers.list()

# Get result qualifiers belonging to a workspace
workspace_result_qualifiers = hs_api.resultqualifiers.list(workspace="00000000-0000-0000-0000-000000000000")

# Get result qualifier with a given ID
result_qualifier = hs_api.resultqualifiers.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Result Qualifier

```python
# Create a new result qualifier on HydroServer
new_result_qualifier = hs_api.resultqualifiers.create(
    code='PF',
    description='Power Failure',
    workspace='00000000-0000-0000-0000-000000000000'
)
```

Each of the methods above will return one or more ResultQualifier objects. The examples below show the main properties and methods available to a ResultQualifier object.

### Example: Modify a Result Qualifier

```python
# Get a result qualifier
result_qualifier = hs_api.resultqualifiers.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the result qualifier.
result_qualifier.code = 'Updated Result Qualifier Code'

# Save the changes back to HydroServer.
result_qualifier.save()
```

### Example: Refresh Result Qualifier data from HydroServer

```python
# Get a result qualifier
result_qualifier = hs_api.resultqualifiers.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh result qualifier data from HydroServer
result_qualifier.refresh()
```

### Example: Delete Result Qualifier from HydroServer

```python
# Get a result qualifier
result_qualifier = hs_api.resultqualifiers.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the result qualifier from HydroServer
result_qualifier.delete()
```

## Datastreams

Datastreams are used in HydroServer to represent a group of environmental observations of an observed property made by a sensor at a location and having a specific processing level. The examples below demonstrate the actions you can take to manage datastreams in HydroServer.

---

### Example: Get Datastreams

```python
# Get all datastreams
datastreams = hs_api.datastreams.list()

# Get datastreams belonging to a workspace
workspace_datastreams = hs_api.datastreams.list(workspace="00000000-0000-0000-0000-000000000000")

# Get datastreams belonging to a thing
thing_datastreams = hs_api.datastreams.list(thing="00000000-0000-0000-0000-000000000000")

# Get datastream with a given ID
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Datastream

```python
from datetime import datetime

...

# Create a new datastream on HydroServer
new_datastream = hs_api.datastreams.create(
    name='Datastream A',
    description='A datastream containing environmental observations.',
    observation_type='Field Observation',
    sampled_medium='Air',
    no_data_value=-9999,
    aggregation_statistic='Continuous',
    time_aggregation_interval=1,
    status='Ongoing',
    result_type='Timeseries',
    value_count=0,
    phenomenon_begin_time=datetime(year=2024, month=1, day=1),
    phenomenon_end_time=None,
    result_begin_time=datetime(year=2024, month=1, day=1),
    result_end_time=None,
    is_visible=True,
    is_private=False,
    thing='00000000-0000-0000-0000-000000000000',
    sensor='00000000-0000-0000-0000-000000000000',
    observed_property='00000000-0000-0000-0000-000000000000',
    processing_level='00000000-0000-0000-0000-000000000000',
    unit='00000000-0000-0000-0000-000000000000',
    time_aggregation_interval_unit='hours',
    intended_time_spacing=1,
    intended_time_spacing_unit='hours'
)
```

Each of the methods above will return one or more Datastream objects. The examples below show the main properties and methods available to a Datastream object.

### Example: Modify a Datastream

```python
# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the datastream.
datastream.name = 'Updated Datastream Name'

# Save the changes back to HydroServer.
datastream.save()
```

### Example: Manage Datastream Tags

```python
# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get datastream tags
tags = datastream.tags

# Add a tag to a datastream
datastream.add_tag(
    key='MaxAllowableResult',
    value=100
)

# Modify a datastream's tag
datastream.update_tag(
    key='MaxAllowableResult',
    value=120
)

# Delete a datastream's tag
datastream.delete_tag(key='MaxAllowableResult')
```

### Example: Manage Datastream File Attachments

```python
# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get datastream file attachments
file_attachments = datastream.file_attachments

# Add a file attachment to a datastream
with open('/path/to/my/myfile.png', 'rb') as file_attachment:
    datastream.add_file_attachment(
        file=file_attachment,
        file_attachment_type='Photo'
    )

# Delete a datastream's file attachment
datastream.delete_file_attachment(name='myfile.png')
```

### Example: Get related properties of a Datastream

```python
# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get the datastream's Thing/Site
thing = datastream.thing

# Get the datastream's Sensor
sensor = datastream.sensor

# Get the datastream's Observed Property
observed_property = datastream.observed_property

# Get the datastream's Unit
unit = datastream.unit

# Get the datastream's Processing Level
processing_level = datastream.processing_level
```

### Example: Get Observations of a Datastream

```python
from datetime import datetime

...

# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get observations of a datastream between two timestamps
observations_df = datastream.get_observations(
    phenomenon_time_min=datetime(year=2023, month=1, day=1),
    phenomenon_time_max=datetime(year=2023, month=12, day=31)
).dataframe

# Get observations all observations of a datastream
full_observations_df = datastream.get_observations(
    fetch_all=True
).dataframe
```

### Example: Upload Observations to a Datastream

```python
import pandas as pd

...

# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Create a DataFrame of observations
new_observations = pd.DataFrame(
    [
        ['2023-01-26 00:00:00+00:00', 40.0],
        ['2023-01-27 00:00:00+00:00', 41.0],
        ['2023-01-28 00:00:00+00:00', 42.0],
    ],
    columns=['phenomenon_time', 'result']
)
new_observations['phenomenon_time'] = pd.to_datetime(new_observations['phenomenon_time'])

# Upload the observations to HydroServer
datastream.load_observations(new_observations)
```

### Example: Replace Observations in a Datastream

```python
import pandas as pd

...

# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Create a DataFrame of observations
new_observations = pd.DataFrame(
    [
        ['2023-01-26 00:00:00+00:00', 40.0],
        ['2023-01-27 00:00:00+00:00', 41.0],
        ['2023-01-28 00:00:00+00:00', 42.0],
    ],
    columns=['phenomenon_time', 'result']
)
new_observations['phenomenon_time'] = pd.to_datetime(new_observations['phenomenon_time'])

# Upload the observations to HydroServer using replace mode
datastream.load_observations(new_observations, mode="replace")
```

### Example: Upload Observations with Result Qualifiers in a Datastream

```python
import pandas as pd

...

# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get result qualifiers
result_qualifier_1 = hs_api.resultqualifiers.get("00000000-0000-0000-0000-000000000000")
result_qualifier_2 = hs_api.resultqualifiers.get("11111111-1111-1111-1111-111111111111")

# Create a DataFrame of observations
new_observations = pd.DataFrame(
    [
        ['2023-01-26 00:00:00+00:00', 40.0, [result_qualifier_1.code]],
        ['2023-01-27 00:00:00+00:00', 41.0, [result_qualifier_1.code, result_qualifier_2.code]],
        ['2023-01-28 00:00:00+00:00', 42.0, []],
    ],
    columns=['phenomenon_time', 'result', 'result_qualifier_codes']  # Note: Result qualifiers are referenced by their code in the DataFrame, not their ID.
)
new_observations['phenomenon_time'] = pd.to_datetime(new_observations['phenomenon_time'])

# Upload the observations to HydroServer
datastream.load_observations(new_observations)
```

### Example: Delete Observations from a Datastream

```python
from datetime import datetime

...

# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Delete Observations in a time range
datastream.delete_observations(phenomenon_time_start=datetime(year=2023, month=1, day=1), phenomenon_time_end=datetime(year=2023, month=12, day=31))

# Delete all Observations in the datastream
datastream.delete_observations()
```

### Example: Refresh Datastream data from HydroServer

```python
# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh datastream data from HydroServer
datastream.refresh()
```

### Example: Delete Datastream from HydroServer

```python
# Get a datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the datastream from HydroServer
datastream.delete()
```

---

## Data Connections

Data connections represent where datastream observations are loaded to or from in an ETL task. They can also contain settings, scheduling, and status information used by orchestration systems responsible for processing the data. Users can create their own data connections, and site administrators can configure global connections that can be used by any user.

---

### Example: Get Data Connections

```python
# Get all data connections
data_connections = hs_api.dataconnections.list()

# Get data connections belonging to a workspace
workspace_data_connections = hs_api.dataconnections.list(workspace="00000000-0000-0000-0000-000000000000")

# Get data connection with a given ID
data_connection = hs_api.dataconnections.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Data Connection

```python
# Create a new data connection in HydroServer
new_data_connection = hs_api.dataconnections.create(
    name='Example Data Connection',
    data_connection_type='ETL',
    workspace='00000000-0000-0000-0000-000000000000',
    extractor_type='HTTP',
    extractor_settings={
        'sourceUri': 'https://www.example.com/data.csv?site={site_code}',
        'placeholderVariables': [
            {'name': 'site_code', 'type': 'perTask'},
        ],
    },
    transformer_type='CSV',
    transformer_settings={
        'headerRow': 1,
        'dataStartRow': 2,
        'delimiter': ',',
        'identifierType': 'name',
        'timestamp': {
            'key': 'TIMESTAMP',
            'format': 'ISO8601',
            'timezoneMode': 'embeddedOffset',
        },
    },
    loader_type='HydroServer',
    loader_settings={}
)
```

### Example: Create Data Connection with JSON Transformer

```python
# Create a new HTTP + JSON data connection in HydroServer
new_json_data_connection = hs_api.dataconnections.create(
    name='USGS Instantaneous Values',
    data_connection_type='ETL',
    workspace='00000000-0000-0000-0000-000000000000',
    extractor_type='HTTP',
    extractor_settings={
        'sourceUri': (
            'https://waterservices.usgs.gov/nwis/iv/'
            '?format=json'
            '&sites={site_code}'
            '&parameterCd={param_code}'
            '&startDT={start_date}'
            '&endDT={end_date}'
        ),
        'placeholderVariables': [
            {'name': 'site_code', 'type': 'perTask'},
            {'name': 'param_code', 'type': 'perTask'},
            {
                'name': 'start_date',
                'type': 'runTime',
                'runTimeValue': 'latestObservationTimestamp',
                'timestamp': {
                    'format': 'ISO8601',
                    'timezoneMode': 'daylightSavings',
                    'timezone': 'America/Denver',
                },
            },
            {
                'name': 'end_date',
                'type': 'runTime',
                'runTimeValue': 'jobExecutionTime',
                'timestamp': {
                    'format': 'ISO8601',
                    'timezoneMode': 'daylightSavings',
                    'timezone': 'America/Denver',
                },
            },
        ],
    },
    transformer_type='JSON',
    transformer_settings={
        'JMESPath': 'value.timeSeries[].values[].value[]',
        'timestamp': {
            'key': 'dateTime',
            'format': 'ISO8601',
            'timezoneMode': 'embeddedOffset',
        },
    },
    loader_type='HydroServer',
    loader_settings={}
)
```

`extractor_settings`, `transformer_settings`, and `loader_settings` should use the same nested JSON shape used by the Data Management app and TypeScript client. For example, HTTP extractors use `sourceUri` and `placeholderVariables` in camelCase.

The USGS Instantaneous Values service accepts ISO-8601 datetimes and assumes site-local time when no offset is provided. This example uses a daylight-savings aware local timezone (`America/Denver`). If your sites are in a different timezone, replace that value with the appropriate IANA timezone for your tasks.

The JSON transformer timestamp configuration also stays on `ISO8601` with `timezoneMode: 'embeddedOffset'` because USGS response `dateTime` values include their timezone offset. In HydroServer, ISO timestamps with embedded offsets are parsed directly; fixed-offset or daylight-savings transformer timezone settings are for sources whose timestamps do not already include timezone information.

Each of the methods above will return one or more DataConnection objects. The examples below show the main properties and methods available to a DataConnection object.

### Example: Modify a Data Connection

```python
# Get a data connection
data_connection = hs_api.dataconnections.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the data connection.
data_connection.name = 'Updated Data Connection'

# Save the changes back to HydroServer.
data_connection.save()
```

### Example: Refresh Data Connection data from HydroServer

```python
# Get a data connection
data_connection = hs_api.dataconnections.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh data connection data from HydroServer
data_connection.refresh()
```

### Example: Delete Data Connection from HydroServer

```python
# Get a data connection
data_connection = hs_api.dataconnections.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the data connection from HydroServer
data_connection.delete()
```

## ETL Tasks

ETL tasks contain specific configuration settings that an orchestration system can use to perform ETL. Tasks can be scheduled to run at specific intervals or set up to be run manually.

---

### Example: Get ETL Tasks

```python
# Get all ETL tasks
tasks = hs_api.etltasks.list()

# Get ETL tasks belonging to a workspace
workspace_tasks = hs_api.etltasks.list(workspace="00000000-0000-0000-0000-000000000000")

# Get ETL task with a given ID
task = hs_api.etltasks.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create ETL Task

```python
# Create a new ETL task in HydroServer
new_task = hs_api.etltasks.create(
    name='Example Task',
    workspace='00000000-0000-0000-0000-000000000000',
    data_connection='00000000-0000-0000-0000-000000000000',
    interval=1,
    interval_period='days',
    mappings=[{
        'source_identifier': 'temperature',
        'target_datastream_id': '00000000-0000-0000-0000-000000000000'
    }]
)
```

Each of the methods above will return one or more EtlTask objects. The examples below show the main properties and methods available to an EtlTask object.

### Example: Modify an ETL Task

```python
# Get an ETL task
task = hs_api.etltasks.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the task.
task.name = 'Updated Task'

# Save the changes back to HydroServer.
task.save()
```

### Example: Refresh ETL Task data from HydroServer

```python
# Get an ETL task
task = hs_api.etltasks.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh task data from HydroServer
task.refresh()
```

### Example: Trigger an ETL Task

```python
# Get an ETL task
task = hs_api.etltasks.get(uid='00000000-0000-0000-0000-000000000000')

# Trigger an immediate run of the task
task_run = task.trigger()
```

### Example: Get ETL Task Runs

```python
# Get an ETL task
task = hs_api.etltasks.get(uid='00000000-0000-0000-0000-000000000000')

# List task runs
task_runs = task.list_runs()

# Get a specific task run by ID
task_run = task.get_run(run_id='00000000-0000-0000-0000-000000000000')
```

### Example: Delete ETL Task from HydroServer

```python
# Get an ETL task
task = hs_api.etltasks.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the task from HydroServer
task.delete()
```

## Monitoring Tasks

Monitoring tasks define scheduled checks on datastreams and alert recipients when rules are triggered. They can be scheduled to run at specific intervals or run manually.

---

### Example: Get Monitoring Tasks

```python
# Get all monitoring tasks
monitoring_tasks = hs_api.monitoringtasks.list()

# Get monitoring tasks belonging to a workspace
workspace_monitoring_tasks = hs_api.monitoringtasks.list(workspace="00000000-0000-0000-0000-000000000000")

# Get monitoring tasks for a specific thing
thing_monitoring_tasks = hs_api.monitoringtasks.list(thing="00000000-0000-0000-0000-000000000000")

# Get monitoring task with a given ID
monitoring_task = hs_api.monitoringtasks.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Monitoring Task

```python
# Create a new monitoring task in HydroServer
new_monitoring_task = hs_api.monitoringtasks.create(
    name='Example Monitoring Task',
    thing='00000000-0000-0000-0000-000000000000',
    description='Monitors datastreams for out-of-range values.',
    recipients=['user@example.com'],
    interval=1,
    interval_period='hours',
    enabled=True
)
```

Each of the methods above will return one or more MonitoringTask objects. The examples below show the main properties and methods available to a MonitoringTask object.

### Example: Modify a Monitoring Task

```python
# Get a monitoring task
monitoring_task = hs_api.monitoringtasks.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the monitoring task.
monitoring_task.name = 'Updated Monitoring Task'
monitoring_task.recipients = ['user@example.com', 'other@example.com']

# Save the changes back to HydroServer.
monitoring_task.save()
```

### Example: Trigger a Monitoring Task

```python
# Get a monitoring task
monitoring_task = hs_api.monitoringtasks.get(uid='00000000-0000-0000-0000-000000000000')

# Trigger an immediate run of the monitoring task
task_run = monitoring_task.trigger()
```

### Example: Get Monitoring Task Runs

```python
# Get a monitoring task
monitoring_task = hs_api.monitoringtasks.get(uid='00000000-0000-0000-0000-000000000000')

# List task runs
task_runs = monitoring_task.list_runs()

# Get a specific task run by ID
task_run = monitoring_task.get_run(run_id='00000000-0000-0000-0000-000000000000')
```

### Example: Get Monitoring Rules for a Task

```python
# Get a monitoring task
monitoring_task = hs_api.monitoringtasks.get(uid='00000000-0000-0000-0000-000000000000')

# Get all rules for the task (cached)
rules = monitoring_task.rules
```

### Example: Delete Monitoring Task from HydroServer

```python
# Get a monitoring task
monitoring_task = hs_api.monitoringtasks.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the monitoring task from HydroServer
monitoring_task.delete()
```

## Monitoring Rules

Monitoring rules define the conditions checked by a monitoring task on a specific datastream. Each rule is scoped to a task.

---

### Example: Get Monitoring Rules

```python
# Get all rules for a monitoring task
rules = hs_api.monitoringrules.list(task_id='00000000-0000-0000-0000-000000000000')

# Filter rules by datastream
datastream_rules = hs_api.monitoringrules.list(
    task_id='00000000-0000-0000-0000-000000000000',
    datastream='00000000-0000-0000-0000-000000000000'
)

# Get a specific monitoring rule by ID
rule = hs_api.monitoringrules.get(
    task_id='00000000-0000-0000-0000-000000000000',
    uid='00000000-0000-0000-0000-000000000000'
)
```

### Example: Create Monitoring Rule

```python
# Create a range rule on a monitoring task
new_rule = hs_api.monitoringrules.create(
    task_id='00000000-0000-0000-0000-000000000000',
    datastream='00000000-0000-0000-0000-000000000000',
    rule_type='range',
    min_value=0.0,
    max_value=100.0
)

# Create a missing data rule
missing_rule = hs_api.monitoringrules.create(
    task_id='00000000-0000-0000-0000-000000000000',
    datastream='00000000-0000-0000-0000-000000000000',
    rule_type='missing_data',
    window_interval=24,
    window_interval_units='hours'
)
```

Each of the methods above will return one or more MonitoringRule objects. The examples below show the main properties and methods available to a MonitoringRule object.

### Example: Modify a Monitoring Rule

```python
# Get a monitoring rule
rule = hs_api.monitoringrules.get(
    task_id='00000000-0000-0000-0000-000000000000',
    uid='00000000-0000-0000-0000-000000000000'
)

# Update the rule's thresholds
rule.min_value = -10.0
rule.max_value = 150.0

# Save the changes back to HydroServer.
rule.save()
```

### Example: Delete Monitoring Rule from HydroServer

```python
# Get a monitoring rule
rule = hs_api.monitoringrules.get(
    task_id='00000000-0000-0000-0000-000000000000',
    uid='00000000-0000-0000-0000-000000000000'
)

# Delete the rule from HydroServer
rule.delete()
```

## Rating Curves

Rating curves define a relationship between two variables (e.g., stage and discharge) associated with a thing. They can be used as transformations in data product tasks.

---

### Example: Get Rating Curves

```python
# Get all rating curves
rating_curves = hs_api.ratingcurves.list()

# Get rating curves belonging to a workspace
workspace_rating_curves = hs_api.ratingcurves.list(workspace="00000000-0000-0000-0000-000000000000")

# Get rating curves for a specific thing
thing_rating_curves = hs_api.ratingcurves.list(thing="00000000-0000-0000-0000-000000000000")

# Get rating curve with a given ID
rating_curve = hs_api.ratingcurves.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Rating Curve

```python
# Create a new rating curve in HydroServer
new_rating_curve = hs_api.ratingcurves.create(
    name='Stage-Discharge Curve',
    thing='00000000-0000-0000-0000-000000000000',
    fitting_method='power_law',
    description='Stage to discharge rating curve.',
    points=[(0.1, 0.5), (0.5, 5.0), (1.0, 15.0), (2.0, 50.0)]
)
```

Each of the methods above will return one or more RatingCurve objects. The examples below show the main properties and methods available to a RatingCurve object.

### Example: Modify a Rating Curve

```python
# Get a rating curve
rating_curve = hs_api.ratingcurves.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the rating curve.
rating_curve.name = 'Updated Rating Curve'
rating_curve.points = [(0.1, 0.4), (0.5, 4.8), (1.0, 14.5), (2.0, 49.0)]

# Save the changes back to HydroServer.
rating_curve.save()
```

### Example: Delete Rating Curve from HydroServer

```python
# Get a rating curve
rating_curve = hs_api.ratingcurves.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the rating curve from HydroServer
rating_curve.delete()
```

## Data Product Tasks

Data product tasks define scheduled computations that produce derived datastream observations from source datastreams using one or more transformations.

---

### Example: Get Data Product Tasks

```python
# Get all data product tasks
data_product_tasks = hs_api.dataproducttasks.list()

# Get data product tasks belonging to a workspace
workspace_data_product_tasks = hs_api.dataproducttasks.list(workspace="00000000-0000-0000-0000-000000000000")

# Get data product tasks for a specific thing
thing_data_product_tasks = hs_api.dataproducttasks.list(thing="00000000-0000-0000-0000-000000000000")

# Get data product task with a given ID
data_product_task = hs_api.dataproducttasks.get(uid='00000000-0000-0000-0000-000000000000')
```

### Example: Create Data Product Task

```python
# Create a new data product task in HydroServer
new_data_product_task = hs_api.dataproducttasks.create(
    name='Example Data Product Task',
    thing='00000000-0000-0000-0000-000000000000',
    description='Produces a derived datastream from source observations.',
    interval=1,
    interval_period='hours',
    enabled=True
)
```

Each of the methods above will return one or more DataProductTask objects. The examples below show the main properties and methods available to a DataProductTask object.

### Example: Modify a Data Product Task

```python
# Get a data product task
data_product_task = hs_api.dataproducttasks.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the task.
data_product_task.name = 'Updated Data Product Task'

# Save the changes back to HydroServer.
data_product_task.save()
```

### Example: Trigger a Data Product Task

```python
# Get a data product task
data_product_task = hs_api.dataproducttasks.get(uid='00000000-0000-0000-0000-000000000000')

# Trigger an immediate run of the data product task
task_run = data_product_task.trigger()
```

### Example: Get Data Product Task Runs

```python
# Get a data product task
data_product_task = hs_api.dataproducttasks.get(uid='00000000-0000-0000-0000-000000000000')

# List task runs
task_runs = data_product_task.list_runs()

# Get a specific task run by ID
task_run = data_product_task.get_run(run_id='00000000-0000-0000-0000-000000000000')
```

### Example: Delete Data Product Task from HydroServer

```python
# Get a data product task
data_product_task = hs_api.dataproducttasks.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the data product task from HydroServer
data_product_task.delete()
```

## Data Product Transformations

Data product transformations define how source datastream observations are converted into output observations within a data product task. Four transformation types are supported: rating curve, expression, composite expression, and aggregation.

---

### Example: Manage Rating Curve Transformations

```python
# List rating curve transformations for a task
rating_curve_transformations = hs_api.dataproducttransformations.list_rating_curve(
    task_id='00000000-0000-0000-0000-000000000000'
)

# Create a rating curve transformation
new_rating_curve_transformation = hs_api.dataproducttransformations.create_rating_curve(
    task_id='00000000-0000-0000-0000-000000000000',
    output_datastream='00000000-0000-0000-0000-000000000000',
    input_datastream='11111111-1111-1111-1111-111111111111',
    rating_curve='22222222-2222-2222-2222-222222222222'
)

# Update a rating curve transformation
updated_rating_curve_transformation = hs_api.dataproducttransformations.update_rating_curve(
    task_id='00000000-0000-0000-0000-000000000000',
    uid=new_rating_curve_transformation.uid,
    input_datastream='33333333-3333-3333-3333-333333333333',
    rating_curve='22222222-2222-2222-2222-222222222222'
)

# Delete a rating curve transformation
hs_api.dataproducttransformations.delete_rating_curve(
    task_id='00000000-0000-0000-0000-000000000000',
    uid=new_rating_curve_transformation.uid
)
```

### Example: Manage Expression Transformations

```python
# List expression transformations for a task
expression_transformations = hs_api.dataproducttransformations.list_expression(
    task_id='00000000-0000-0000-0000-000000000000'
)

# Create an expression transformation
new_expression_transformation = hs_api.dataproducttransformations.create_expression(
    task_id='00000000-0000-0000-0000-000000000000',
    output_datastream='00000000-0000-0000-0000-000000000000',
    input_datastream='11111111-1111-1111-1111-111111111111',
    formula='x * 0.3048',  # feet to meters
    variable_name='x'
)

# Delete an expression transformation
hs_api.dataproducttransformations.delete_expression(
    task_id='00000000-0000-0000-0000-000000000000',
    uid=new_expression_transformation.uid
)
```

### Example: Manage Composite Expression Transformations

```python
# Create a composite expression transformation combining multiple input datastreams
new_composite_expression_transformation = hs_api.dataproducttransformations.create_composite_expression(
    task_id='00000000-0000-0000-0000-000000000000',
    output_datastream='00000000-0000-0000-0000-000000000000',
    input_datastreams=[
        {'datastream_id': '11111111-1111-1111-1111-111111111111', 'variable_name': 'a'},
        {'datastream_id': '22222222-2222-2222-2222-222222222222', 'variable_name': 'b'},
    ],
    formula='(a + b) / 2',
    output_interval=1,
    output_interval_units='hours'
)

# Delete a composite expression transformation
hs_api.dataproducttransformations.delete_composite_expression(
    task_id='00000000-0000-0000-0000-000000000000',
    uid=new_composite_expression_transformation.uid
)
```

### Example: Manage Aggregation Transformations

```python
# Create an aggregation transformation
new_aggregation_transformation = hs_api.dataproducttransformations.create_aggregation(
    task_id='00000000-0000-0000-0000-000000000000',
    output_datastream='00000000-0000-0000-0000-000000000000',
    input_datastream='11111111-1111-1111-1111-111111111111',
    aggregation_method='mean',
    output_interval=1,
    output_interval_units='hours',
    timezone_type='iana',
    timezone='America/Denver',
    min_values=3
)

# Delete an aggregation transformation
hs_api.dataproducttransformations.delete_aggregation(
    task_id='00000000-0000-0000-0000-000000000000',
    uid=new_aggregation_transformation.uid
)
```
