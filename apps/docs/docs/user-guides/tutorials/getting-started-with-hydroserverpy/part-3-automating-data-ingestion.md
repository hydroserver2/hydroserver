# Part 3: Automating Data Ingestion

> **Note:** This part requires HydroServer's orchestration system to be installed and running alongside your HydroServer instance. The public playground at `https://playground.hydroserver.org` does not currently have the orchestration system enabled. You can read through this part on playground, but ETL tasks won't execute until you're working with a self-hosted instance that has the orchestration system set up.

So far we've been loading data manually. That works fine for historical data, but for an ongoing monitoring station you want new observations to flow in automatically. In this part we'll set up an ETL pipeline that pulls gage height readings from a USGS gauging station on the Logan River and loads them into HydroServer on a 15-minute schedule.

The real station we're mirroring is [USGS 10109000 — Logan River Above State Dam, Near Logan, UT](https://waterdata.usgs.gov/monitoring-location/10109000/). We'll create a corresponding site in HydroServer and configure a data connection that knows how to talk to the USGS Instantaneous Values API.

## Create the Logan River site and datastream

This should feel familiar from Part 1. We're creating a new site and stage datastream — this time for the USGS Logan River Above State Dam monitoring location.

Note that USGS reports gage height in feet, so we'll use feet as the unit for this datastream.

```python
# Site
logan_river_site = hs_api.monitoring_sites.create(
    workspace=workspace,
    name='Logan River Above State Dam',
    description='USGS gauging station 10109000 on the Logan River near Logan, Utah.',
    code='USGS-10109000',
    type='Stream',
    is_private=False,
    latitude=41.7444,
    longitude=-111.8358,
    elevation_m=1380.0,
    elevation_datum='EGM96',
    admin_area_1='UT',
    admin_area_2='Cache',
    country='US',
)

# Method
usgs_method = hs_api.methods.create(
    workspace=workspace,
    name='USGS Pressure Transducer',
    description='Continuous water level sensor deployed by USGS.',
    type='Instrument Deployment',
    code='USGS_PRESSURE_TRANSDUCER',
    sensor_model='Pressure Transducer',
    sensor_model_manufacturer='USGS',
)

# Observed property
gage_height_property = hs_api.observedproperties.create(
    workspace=workspace,
    name='Gage Height',
    definition='http://vocabulary.odm2.org/variablename/gageHeight/',
    description='Height of the water surface above a local datum.',
    type='Hydrology',
    code='GAGE_HEIGHT',
)

# Unit
feet_unit = hs_api.units.create(
    workspace=workspace,
    name='Foot',
    symbol='ft',
    definition='https://qudt.org/vocab/unit/FT',
    type='Length',
)

# Processing level (reuse the one we created in Part 1, or recreate it)
raw_processing_level = hs_api.processinglevels.create(
    workspace=workspace,
    code='0',
    name='Raw',
    description='Data have not been processed or quality controlled.',
)

# Datastream
stage_datastream = hs_api.datastreams.create(
    name=f'{gage_height_property.name} at {logan_river_site.name}',
    description=f'{gage_height_property.name} from USGS station {logan_river_site.code}.',
    monitoring_site=logan_river_site,
    method=usgs_method,
    observed_property=gage_height_property,
    processing_level=raw_processing_level,
    unit=feet_unit,
    observation_type='Field Observation',
    result_type='Timeseries',
    sampled_medium='Surface water',
    no_data_value=-9999.0,
    aggregation_statistic='Instantaneous',
    time_aggregation_interval=1,
    time_aggregation_interval_unit='minutes',
    intended_time_spacing=15,
    intended_time_spacing_unit='minutes',
    status='Ongoing',
    is_private=False,
)

print(f"{stage_datastream.name}: {stage_datastream.uid}")
```

## Create a data connection

A data connection describes where your data comes from and how to read it. Our source is the USGS Instantaneous Values API, which returns JSON. Each run asks USGS for the last seven days of readings (`period=P7D`). That window overlaps with data we've already loaded, but HydroServer only loads observations newer than the most recent one already in the datastream, so each run adds just the new readings. The `{site_code}` and `{param_code}` placeholders in the URL are filled in by each task that uses this connection.

```python
usgs_data_connection = hs_api.dataconnections.create(
    name='USGS Instantaneous Values',
    workspace=workspace,
    source_url=(
        'https://waterservices.usgs.gov/nwis/iv/'
        '?format=json'
        '&sites={site_code}'
        '&parameterCd={param_code}'
        '&period=P7D'
    ),
    payload_type='JSON',
    timestamp_key='dateTime',
    jmespath='value.timeSeries[].values[].value[]',
    placeholder_variables=[
        {'name': 'site_code', 'variable_type': 'per_task'},
        {'name': 'param_code', 'variable_type': 'per_task'},
    ],
)

print(f"{usgs_data_connection.name}: {usgs_data_connection.uid}")
```

The `site_code` and `param_code` variables are marked `per_task`, which means each task using this connection can supply its own values. That makes the data connection reusable — you could point other tasks at different USGS sites or parameters without creating a new connection for each one.

## Create an ETL task

Now we tie everything together. The task supplies values for the `per_task` placeholder variables and the schedule it runs on. A mapping, created right after the task, tells it which field in the source data goes to which datastream.

```python
usgs_etl_task = hs_api.etltasks.create(
    name='Logan River Gage Height from USGS',
    data_connection=usgs_data_connection,
    task_variables={
        'site_code': '10109000',
        'param_code': '00065',
    },
    interval=15,
    interval_period='minutes',
    enabled=True,
)

hs_api.etlmappings.create(
    task_id=usgs_etl_task.uid,
    source_identifier='value',
    target_datastream=stage_datastream,
)

print(f"{usgs_etl_task.name}: {usgs_etl_task.uid}")
```

The mapping's `source_identifier` names the field in each extracted record that holds the value. The JMESPath expression on the data connection turns the USGS response into records like `{"value": "2.57", "qualifiers": ["P"], "dateTime": "..."}`, so the identifier is `'value'`. Which USGS parameter you get — here gage height, `00065` — is chosen by the task's `param_code` variable.

## Trigger the task manually

Rather than waiting for the scheduler to fire, let's trigger a run immediately to make sure everything is wired up correctly.

```python
import time

task_run = usgs_etl_task.trigger()
print(f"Task triggered. Run ID: {task_run.id}")

# Give it a few seconds to complete
time.sleep(10)

runs = usgs_etl_task.list_runs()
latest = runs[0]
print(f"Status:  {latest.status}")
print(f"Message: {latest.message}")
```

If the status comes back as `SUCCESS`, your stage datastream should now have real observations in it from USGS. If it stays `PENDING`, no orchestration worker has picked up the run yet — check that your instance's workers are running. You can verify the data by fetching it the same way we did in Part 2:

```python
result = stage_datastream.get_observations(fetch_all=True)
print(f"Observations in datastream: {len(result.dataframe)}")
print(result.dataframe.tail())
```

If the status is `FAILURE`, the message field will tell you what went wrong — usually a network issue or a misconfigured URL or parameter code.

## Scheduling

With `interval=15` and `interval_period='minutes'`, the orchestration system will keep re-running this task every 15 minutes automatically. Each run fetches the last seven days from USGS and loads only the readings newer than what's already in the datastream, so you don't need to do anything else to keep the data flowing.

In Part 4, we'll take these raw stage readings and use a data product task to automatically convert them into discharge values using a rating curve.
