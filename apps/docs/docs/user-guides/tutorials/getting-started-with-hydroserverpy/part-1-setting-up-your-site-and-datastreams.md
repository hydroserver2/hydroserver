# Part 1: Setting Up Your Site and Datastreams

In this first part, we'll connect to HydroServer and create everything needed to represent a monitoring site: a workspace, a site, linked metadata (sensor, observed property, unit, and processing level), and a datastream. By the end you'll have a fully described datastream ready to receive observations in the next part.

The site we'll be building throughout this tutorial is a fictional stream gauge station on the Cache River in northern Utah. We'll use it to measure water surface elevation (stage) — a common measurement at stream monitoring stations.

## Connect to HydroServer

Create a new Python script (or Jupyter notebook) and add the following to connect to the playground instance:

```python
from hydroserverpy import HydroServer

hs_api = HydroServer(
    host='https://playground.hydroserver.org',
    email='your@email.com',
    password='yourpassword'
)
```

## Create a workspace

All resources in HydroServer — sites, datastreams, sensors, and so on — belong to a workspace. Let's create one for this tutorial.

```python
workspace = hs_api.workspaces.create(
    name='Logan River Monitoring',
    is_private=False
)

print(f"{workspace.name}: {workspace.uid}")
```

Keep the workspace UID handy — we'll pass it to everything we create next. If you're running this in a notebook you won't need to save it separately, but if you close your session and come back later, you can look it up with:

```python
for ws in hs_api.workspaces.list(is_associated=True).items:
    print(ws.uid, ws.name)
```

## Create your monitoring site

Now let's create the site itself. We need a few pieces of information: basic metadata about what kind of site this is, and its location.

```python
blacksmith_fork_site = hs_api.things.create(
    workspace=workspace,
    name='Blacksmith Fork River above confluence with Logan River',
    description='Logan River Observatory monitoring site for Blacksmith Fork River above the confluence with Logan River',
    sampling_feature_type='Site',
    sampling_feature_code='BSF_CONF_BA',
    site_type='Stream',
    latitude=41.704431,
    longitude=-111.850800,
    elevation_m=1366.0,
    elevation_datum='EGM96',
    admin_area_1='UT',
    admin_area_2='Cache',
    country='US',
    data_disclaimer='WARNING: These data may be provisional and subject to revision.',
    is_private=False
)

print(f"{blacksmith_fork_site.name}: {blacksmith_fork_site.uid}")
```

The `sampling_feature_code` is a short identifier for your site — something you'd use to reference it in a dataset or filename. Make it unique within your workspace.

## Create linked metadata

Before we can create a datastream, we need to define what's being measured and how. In HydroServer, that means creating four linked metadata records: a **sensor**, an **observed property**, a **unit**, and a **processing level**. These can be reused across multiple datastreams, so you only have to create them once.

### Sensor

The sensor describes the instrument or method used to make the measurement.

```python
discharge_sensor = hs_api.sensors.create(
    workspace=workspace,
    name='In-Situ Rugged TROLL 200',
    description='Submersible pressure transducer for water level measurement.',
    encoding_type='application/json',
    manufacturer='In-Situ',
    sensor_model='Rugged TROLL 200',
    sensor_model_link='https://in-situ.com/us/rugged-troll-200',
    method_type='Instrument deployment',
    method_code='PRESSURE_TRANSDUCER',
    method_link='https://in-situ.com/us/rugged-troll-200',
)
```

### Observed property

The observed property describes the physical quantity being measured.

```python
discharge_observed_property = hs_api.observedproperties.create(
    workspace=workspace,
    name='Discharge',
    definition='http://vocabulary.odm2.org/variablename/discharge/',
    description='Discharge is the flow rate of water per unit time.',
    observed_property_type='Hydrology',
    code='discharge'
)
```

### Unit

```python
discharge_unit = hs_api.units.create(
    workspace=workspace,
    name='Cubic meters per second',
    symbol='m3^s',
    definition='https://qudt.org/vocab/unit/M3-PER-SEC',
    unit_type='Flow rate'
)
```

### Processing level

Processing levels describe how much quality control or processing the data has been through. Since we're working with raw sensor readings, we'll use level 0.

```python
raw_processing_level = hs_api.processinglevels.create(
    workspace=workspace,
    code='0',
    definition='Raw',
    explanation='Data have not been processed or quality controlled.',
)
```

## Create a datastream

Now we have everything we need to define our datastream. A datastream ties together a site, sensor, observed property, unit, and processing level, and also describes how observations are structured — their type, medium, aggregation, and time spacing.

Our gauge records instantaneous discharge measurements every 15 minutes.

```python
discharge_datastream = hs_api.datastreams.create(
    name=f"{discharge_observed_property.name} measured in the {blacksmith_fork_site.name}",
    description=f'{discharge_observed_property.name} created using a {discharge_sensor.name}',
    thing=blacksmith_fork_site,
    sensor=discharge_sensor,
    observed_property=discharge_observed_property,
    processing_level=raw_processing_level,
    unit=discharge_unit,
    observation_type='Field Observation',
    result_type='Timeseries',
    sampled_medium='Surface water',
    no_data_value=-9999,
    aggregation_statistic='Instantaneous',
    time_aggregation_interval=1,
    time_aggregation_interval_unit='minutes',
    intended_time_spacing=15,
    intended_time_spacing_unit='minutes',
    status='Ongoing',
    is_private=False,
    is_visible=True
)

print(f"{discharge_datastream.name}: {discharge_datastream.uid}")
```

We'll use `discharge_datastream` directly in the next part to load observations.

## What we've built

In a few dozen lines of Python, we've created a fully described monitoring site in HydroServer with a datastream ready to receive data. If you open the web interface and navigate to your workspace, you should see the Blacksmith Fork River above confluence with Logan River on the map and the discharge datastream listed in its detail page.

In Part 2, we'll load some sample stage observations into that datastream and visualize them.