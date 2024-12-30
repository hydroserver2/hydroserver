# Overview of the `hydroserverpy.core` Package

The `hydroserverpy.core` Python package allows HydroServer users to retrieve, create, update, and delete their HydroServer data and metadata. This guide will provide examples on how to manage various types of HydroServer data.

## Data Management Guide with Examples

To perform data management operations, you must connect to HydroServer.

```python
from hydroserverpy import HydroServer

# Initialize HydroServer connection with credentials.
hs_api = HydroServer(
    host='https://playground.hydroserver.org',
    username='user@example.com',
    password='******'
)
```

The hydroserverpy connection instance exposes the following types of core data and metadata you can retrieve or create, either as a list or by ID using the `list`, `get`, or `create` methods of the associated property:

* things
* datastreams
* sensors
* units
* processinglevels
* observedproperties
* resultqualifiers

### Things

Things (or sites) are one of the core data elements managed in HydroServer. Things represent a location or site at which one or more datastreams of observations are collected. All datastreams in HydroServer must be associated with a thing/site. The examples below demonstrate the actions you can take to manage things in HydroServer.

#### Example: Get Things
```python
# Get all Things
things = hs_api.things.list()

# Get owned Things
owned_things = hs_api.things.list(owned_only=True)

# Get primary owned Things
primary_owned_things = hs_api.things.list(primary_owned_only=True)

# Get Thing with a given ID
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')
```

#### Example: Create Thing
```python
# Create a new Thing on HydroServer
new_thing = hs_api.things.create(
    name='My Site',
    description='This is a site that records environmental observations.',
    sampling_feature_type='Site',
    sampling_feature_code='OBSERVATION_SITE',
    site_type='Atmosphere',
    latitude='41.7390',
    longitude='-111.7957',
    elevation_m='1414.0',
    elevation_datum='EGM96',
    state='UT',
    county='Cache',
    country='US',
    data_disclaimer='WARNING: These data may be provisional and subject to revision.'
)
```

Each of the methods above will return one or more Thing objects. The examples below show the main properties and methods available to a Thing object.

#### Example: Modify a Thing
```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Thing.
thing.name = 'Updated Site Name'
thing.description = 'This site metadata has been modified.'

# Save the changes back to HydroServer.
thing.save()
```

#### Example: Manage Thing Tags
```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Get Thing Tags
tags = thing.tags

# Add a Tag to a Thing
thing.add_tag(
    key='Region',
    value='A'
)

# Modify a Thing Tag
thing.update_tag(
    key='Region',
    value='B'
)

# Delete a Thing Tag
thing.delete_tag(key='Region')
```

#### Example: Manage Thing Photos
```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Get Thing Photos
photos = thing.photos

# Add a Photo to a Thing
with open('/path/to/my/photo.png', 'rb') as photo_file:
    thing.add_photo(photo=photo_file)

# Delete a Thing Photo
thing.delete_photo(link='https://link/to/my/photo.png')
```

#### Example: Get Datastreams of a Thing
```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Fetch Datastreams of the Thing
datastreams = thing.datastreams
```

#### Example: Get Thing Archive
```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Fetch Archive information of a Thing
archive = thing.archive
```

#### Example: Refresh Thing data from HydroServer
```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh Thing data from HydroServer
thing.refresh()
```

#### Example: Delete Thing from HydroServer
```python
# Get a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the Thing from HydroServer
thing.delete()
```

### Observed Properties

Observed properties are used in HydroServer to represent the physical property being observed and stored in a datastream. The examples below demonstrate the actions you can take to manage observed properties in HydroServer.

#### Example: Get Observed Properties
```python
# Get all Observed Properties
observed_properties = hs_api.observedproperties.list()

# Get all Observed Properties excluding templates
owned_and_unowned_observed_properties = hs_api.observedproperties.list(include_templates=False)

# Get owned Observed Properties including templates
owned_and_template_observed_properties = hs_api.observedproperties.list(include_unowned=False)

# Get owned Observed Properties
owned_observed_properties = hs_api.observedproperties.list(include_templates=False, include_unowned=False)

# Get Observed Property templates
template_observed_properties = hs_api.observedproperties.list(include_owned=False, include_templates=True)

# Get Observed Property with a given ID
observed_property = hs_api.observedproperty.get(uid='00000000-0000-0000-0000-000000000000')
```

#### Example: Create Observed Property
```python
# Create a new Observed Property in HydroServer
new_observed_property = hs_api.observedproperties.create(
    name='Temperature',
    definition='Air Temperature',
    description='Air temperature',
    type='Climate',
    code='AirTemp',
)
```

Each of the methods above will return one or more ObservedProperty objects. The examples below show the main properties and methods available to an ObservedProperty object.

#### Example: Modify an Observed Property
```python
# Get an Observed Property
observed_property = hs_api.observedproperties.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Observed Property.
observed_property.name = 'Updated Observed Property Name'

# Save the changes back to HydroServer.
observed_property.save()
```

#### Example: Refresh Observed Property data from HydroServer
```python
# Get an Observed Property
observed_property = hs_api.observedproperties.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh Observed Property data from HydroServer
observed_property.refresh()
```

#### Example: Delete Observed Property from HydroServer
```python
# Get an Observed Property
observed_property = hs_api.observedproperties.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the Observed Property from HydroServer
observed_property.delete()
```

### Units

Units are used in HydroServer to describe the physical quantity represented by the result of an observation in a datastream. The examples below demonstrate the actions you can take to manage units in HydroServer.

#### Example: Get Units
```python
# Get all Units
units = hs_api.units.list()

# Get all Units excluding templates
owned_and_unowned_units = hs_api.units.list(include_templates=False)

# Get owned Units including templates
owned_and_template_units = hs_api.units.list(include_unowned=False)

# Get owned Units
owned_units = hs_api.units.list(include_templates=False, include_unowned=False)

# Get Units templates
template_units = hs_api.units.list(include_owned=False, include_templates=True)

# Get Unit with a given ID
unit = hs_api.units.get(uid='00000000-0000-0000-0000-000000000000')
```

#### Example: Create Unit
```python
# Create a new Unit on HydroServer
new_unit = hs_api.units.create(
    name='Degree Celsius',
    symbol='C',
    definition='Degree Celsius',
    type='Temperature'
)
```

Each of the methods above will return one or more Unit objects. The examples below show the main properties and methods available to a Unit object.

#### Example: Modify a Unit
```python
# Get a Unit
unit = hs_api.units.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Unit.
unit.name = 'Updated Unit Name'

# Save the changes back to HydroServer.
unit.save()
```

#### Example: Refresh Unit data from HydroServer
```python
# Get a Unit
unit = hs_api.units.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh Unit data from HydroServer
unit.refresh()
```

#### Example: Delete Unit from HydroServer
```python
# Get a Unit
unit = hs_api.units.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the Unit from HydroServer
unit.delete()
```

### Sensors

Sensors are used in HydroServer to describe the sensor/method used to make an environmental observation. The examples below demonstrate the actions you can take to manage sensors in HydroServer.

#### Example: Get Sensors
```python
# Get all Sensors
sensors = hs_api.sensors.list()

# Get all Sensors excluding templates
owned_and_unowned_sensors = hs_api.sensors.list(include_templates=False)

# Get owned Sensors including templates
owned_and_template_sensors = hs_api.sensors.list(include_unowned=False)

# Get owned Sensors
owned_sensors = hs_api.sensors.list(include_templates=False, include_unowned=False)

# Get Sensors templates
template_sensors = hs_api.sensors.list(include_owned=False, include_templates=True)

# Get Sensor with a given ID
sensor = hs_api.sensors.get(uid='00000000-0000-0000-0000-000000000000')
```

#### Example: Create Sensor
```python
# Create a new Sensor on HydroServer
new_sensor = hs_api.sensors.create(
    name='Environmental Sensor',
    description='An environmental sensor.',
    encoding_type='json',
    manufacturer='Campbell Scientific',
    model='A',
    model_link='https://link/to/sensor/model/info',
    method_type='Sensor',
    method_link='https://link/to/method/info',
    method_code='SENSOR_A'
)
```

Each of the methods above will return one or more Sensor objects. The examples below show the main properties and methods available to a Sensor object.

#### Example: Modify a Sensor
```python
# Get a Sensor
sensor = hs_api.sensors.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Sensor.
sensor.name = 'Updated Sensor Name'

# Save the changes back to HydroServer.
sensor.save()
```

#### Example: Refresh Sensor data from HydroServer
```python
# Get a Sensor
sensor = hs_api.sensors.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh Sensor data from HydroServer
sensor.refresh()
```

#### Example: Delete Sensor from HydroServer
```python
# Get a Sensor
sensor = hs_api.sensors.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the Sensor from HydroServer
sensor.delete()
```

### Processing Levels

Processing levels are used in HydroServer to describe the level of processing observations of a datastream have been subject to. The examples below demonstrate the actions you can take to manage processing levels in HydroServer.

#### Example: Get Processing Levels
```python
# Get all Processing Levels
processing_levels = hs_api.processinglevels.list()

# Get all Processing Levels excluding templates
owned_and_unowned_processing_levels = hs_api.processinglevels.list(include_templates=False)

# Get owned Processing Levels including templates
owned_and_template_processing_levels = hs_api.processinglevels.list(include_unowned=False)

# Get owned Processing Levels
owned_processing_levels = hs_api.processinglevels.list(include_templates=False, include_unowned=False)

# Get Processing Levels templates
template_processing_levels = hs_api.processinglevels.list(include_owned=False, include_templates=True)

# Get Processing Level with a given ID
processing_level = hs_api.processinglevels.get(uid='00000000-0000-0000-0000-000000000000')
```

#### Example: Create Processing Level
```python
# Create a new Processing Level on HydroServer
new_processing_level = hs_api.processinglevels.create(
    code='0',
    definition='Raw',
    explanation='Data have not been processed or quality controlled.'
)
```

Each of the methods above will return one or more ProcessingLevel objects. The examples below show the main properties and methods available to a ProcessingLevel object.

#### Example: Modify a Processing Level
```python
# Get a Processing Level
processing_level = hs_api.processinglevels.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Processing Level.
processing_level.code = 'Updated Processing Level Code'

# Save the changes back to HydroServer.
processing_level.save()
```

#### Example: Refresh Processing Level data from HydroServer
```python
# Get a Processing Level
processing_level = hs_api.processinglevels.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh Processing Level data from HydroServer
processing_level.refresh()
```

#### Example: Delete Processing Level from HydroServer
```python
# Get a Processing Level
processing_level = hs_api.processinglevels.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the Processing Level from HydroServer
processing_level.delete()
```

### Result Qualifiers

Result qualifiers are used in HydroServer to annotate observations during quality control or other processing steps. The examples below demonstrate the actions you can take to manage result qualifiers in HydroServer.

#### Example: Get Result Qualifiers
```python
# Get all Result Qualifiers
result_qualifiers = hs_api.resultqualifiers.list()

# Get all Result Qualifiers excluding templates
owned_and_unowned_result_qualifiers = hs_api.resultqualifiers.list(include_templates=False)

# Get owned Result Qualifiers including templates
owned_and_template_result_qualifiers = hs_api.resultqualifiers.list(include_unowned=False)

# Get owned Result Qualifiers
owned_result_qualifiers = hs_api.resultqualifiers.list(include_templates=False, include_unowned=False)

# Get Result Qualifiers templates
template_result_qualifiers = hs_api.resultqualifiers.list(include_owned=False, include_templates=True)

# Get Result Qualifier with a given ID
result_qualifier = hs_api.resultqualifiers.get(uid='00000000-0000-0000-0000-000000000000')
```

#### Example: Create Result Qualifier
```python
# Create a new Result Qualifier on HydroServer
new_result_qualifier = hs_api.resultqualifiers.create(
    code='PF',
    description='Power Failure'
)
```

Each of the methods above will return one or more ResultQualifier objects. The examples below show the main properties and methods available to a ResultQualifier object.

#### Example: Modify a Result Qualifier
```python
# Get a Result Qualifier
result_qualifier = hs_api.resultqualifiers.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Result Qualifier.
result_qualifier.code = 'Updated Result Qualifier Code'

# Save the changes back to HydroServer.
result_qualifier.save()
```

#### Example: Refresh Result Qualifier data from HydroServer
```python
# Get a Result Qualifier
result_qualifier = hs_api.resultqualifiers.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh Result Qualifier data from HydroServer
result_qualifier.refresh()
```

#### Example: Delete Result Qualifier from HydroServer
```python
# Get a Result Qualifier
result_qualifier = hs_api.resultqualifiers.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the Processing Level from HydroServer
result_qualifier.delete()
```

### Datastreams

Datastreams are used in HydroServer to represent a group of environmental observations of an observed property made by a sensor at a location and having a specific processing level. The examples below demonstrate the actions you can take to manage datastreams in HydroServer.

#### Example: Get Datastreams
```python
# Get all Datastreams
datastreams = hs_api.datastreams.list()

# Get owned Datastreams
owned_datastreams = hs_api.datastreams.list(owned_only=True)

# Get primary owned Datastreams
primary_owned_datastreams = hs_api.datastreams.list(primary_owned_only=True)

# Get Datastream with a given ID
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get Datastreams of a Thing
thing = hs_api.things.get(uid='00000000-0000-0000-0000-000000000000')
thing_datastreams = thing.datastreams
```

#### Example: Create Datastream
```python
from datetime import datetime

...

# Create a new Datastream on HydroServer
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
    is_data_visible=True,
    thing_id='00000000-0000-0000-0000-000000000000',
    sensor_id='00000000-0000-0000-0000-000000000000',
    observed_property_id='00000000-0000-0000-0000-000000000000',
    processing_level_id='00000000-0000-0000-0000-000000000000',
    unit_id='00000000-0000-0000-0000-000000000000',
    time_aggregation_interval_units='hours',
    intended_time_spacing=1,
    intended_time_spacing_units='hours'
)
```

Each of the methods above will return one or more Datastream objects. The examples below show the main properties and methods available to a Datastream object.

#### Example: Modify a Datastream
```python
# Get a Datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Update one or more properties of the Datastream.
datastream.name = 'Updated Datastream Name'

# Save the changes back to HydroServer.
datastream.save()
```

#### Example: Get related properties of a Datastream
```python
# Get a Datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get the Datastream's Thing/Site
thing = datastream.thing

# Get the Datastream's Sensor
sensor = datastream.sensor

# Get the Datastream's Observed Property
observed_property = datastream.observed_property

# Get the Datastream's Unit
unit = datastream.unit

# Get the Datastream's Processing Level
processing_level = datastream.processing_level
```

#### Example: Get Observations of a Datastream
```python
from datetime import datetime

...

# Get a Datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Get Observations of a Datastream between two timestamps
observations_df = datastream.get_observations(
    start_time=datetime(year=2023, month=1, day=1),
    end_time=datetime(year=2023, month=12, day=31)
)
```

#### Example: Upload Observations to a Datastream
```python
import pandas as pd

...

# Get a Datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Create a DataFrame of Observations
new_observations = pd.DataFrame(
    [
        ['2023-01-26 00:00:00+00:00', 40.0],
        ['2023-01-27 00:00:00+00:00', 41.0],
        ['2023-01-28 00:00:00+00:00', 42.0],
    ],
    columns=['timestamp', 'value']
)
new_observations['timestamp'] = pd.to_datetime(new_observations['timestamp'])

# Upload the Observations to HydroServer
datastream.load_observations(new_observations)
```

#### Example: Refresh Datastream data from HydroServer
```python
# Get a Datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Refresh Datastream data from HydroServer
datastream.refresh()
```

#### Example: Delete Datastream from HydroServer
```python
# Get a Datastream
datastream = hs_api.datastreams.get(uid='00000000-0000-0000-0000-000000000000')

# Delete the Datastream from HydroServer
datastream.delete()
```
