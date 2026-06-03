# Part 4: Creating Data Products

> **Note:** Like Part 3, this part requires HydroServer's orchestration system to be installed and running. The playground instance does not currently support data product tasks.

At this point we have 15-minute gage height readings in feet flowing into HydroServer from the USGS API. Data product tasks let you define computations that run automatically on that raw data and write the results to a new output datastream — without touching the original. In this part we'll set up two:

1. A **daily aggregation** that computes the mean gage height for each calendar day
2. An **expression transformation** that converts the readings from feet to meters

Both tasks read from the `stage_datastream` we created in Part 3.

## Set up output datastreams

Each transformation needs an output datastream to write its results into. We'll also need a derived processing level and a meters unit that we haven't created yet.

```python
# Processing level for computed/derived data
derived_processing_level = hs_api.processinglevels.create(
    workspace=workspace,
    code='1',
    definition='Derived',
    explanation='Data have been computed or derived from raw measurements.',
)

# Meters unit for the unit conversion output
meters_unit = hs_api.units.create(
    workspace=workspace,
    name='Meter',
    symbol='m',
    definition='https://qudt.org/vocab/unit/M',
    unit_type='Length',
)

# Output datastream for the daily aggregation
daily_stage_datastream = hs_api.datastreams.create(
    name=f'Daily Mean Gage Height at {logan_river_site.name}',
    description='Daily mean gage height computed from 15-minute USGS readings.',
    thing=logan_river_site,
    sensor=usgs_sensor,
    observed_property=gage_height_property,
    processing_level=derived_processing_level,
    unit=feet_unit,
    observation_type='Field Observation',
    result_type='Timeseries',
    sampled_medium='Surface Water',
    no_data_value=-9999.0,
    aggregation_statistic='Mean',
    time_aggregation_interval=1,
    time_aggregation_interval_unit='days',
    status='Ongoing',
    is_private=False,
)

# Output datastream for the feet-to-meters conversion
stage_meters_datastream = hs_api.datastreams.create(
    name=f'Gage Height (meters) at {logan_river_site.name}',
    description='Gage height converted from feet to meters.',
    thing=logan_river_site,
    sensor=usgs_sensor,
    observed_property=gage_height_property,
    processing_level=derived_processing_level,
    unit=meters_unit,
    observation_type='Field Observation',
    result_type='Timeseries',
    sampled_medium='Surface Water',
    no_data_value=-9999.0,
    aggregation_statistic='Instantaneous',
    time_aggregation_interval=1,
    time_aggregation_interval_unit='minutes',
    intended_time_spacing=15,
    intended_time_spacing_unit='minutes',
    status='Ongoing',
    is_private=False,
)
```

## Daily aggregation task

A data product task defines the schedule on which computations run. The actual computation is defined by the transformation we attach to it. For the daily aggregation, we'll run the task once a day.

```python
daily_aggregation_task = hs_api.dataproducttasks.create(
    name='Logan River Daily Mean Stage',
    thing=logan_river_site,
    description='Computes a daily mean gage height from 15-minute USGS readings.',
    interval=1,
    interval_period='days',
    enabled=True,
)
```

Now attach an aggregation transformation to it. The `timezone` here matters — setting it to Mountain Time means "daily" is computed as midnight-to-midnight in Utah rather than UTC. The `min_values` parameter is optional but useful: it prevents a daily value from being written unless at least that many input observations were available for that day. With 15-minute data there are 96 possible readings per day, so 72 requires at least 75% data availability.

```python
hs_api.dataproducttransformations.create_aggregation(
    task_id=daily_aggregation_task.uid,
    output_datastream=daily_stage_datastream,
    input_datastream=stage_datastream,
    aggregation_method='mean',
    output_interval=1,
    output_interval_units='days',
    timezone_type='iana',
    timezone='America/Denver',
    min_values=72,
)
```

Trigger it manually to verify:

```python
import time

task_run = daily_aggregation_task.trigger()
print(f"Task triggered. Run ID: {task_run.id}")

time.sleep(10)

runs = daily_aggregation_task.list_runs()
latest = runs[0]
print(f"Status:  {latest.status}")
print(f"Message: {latest.message}")
```

If it succeeds, the `daily_stage_datastream` will have one observation per calendar day.

## Expression transformation task

For the feet-to-meters conversion, we want the output to stay in sync with the input, so we'll run this task every 15 minutes — the same frequency as the incoming USGS data.

```python
meters_conversion_task = hs_api.dataproducttasks.create(
    name='Logan River Stage in Meters',
    thing=logan_river_site,
    description='Converts gage height from feet to meters.',
    interval=15,
    interval_period='minutes',
    enabled=True,
)
```

Attach an expression transformation. The formula is evaluated for each input observation, where `x` is the raw value. One foot equals 0.3048 meters.

```python
hs_api.dataproducttransformations.create_expression(
    task_id=meters_conversion_task.uid,
    output_datastream=stage_meters_datastream,
    input_datastream=stage_datastream,
    formula='x * 0.3048',
    variable_name='x',
)
```

Trigger it to verify:

```python
task_run = meters_conversion_task.trigger()
print(f"Task triggered. Run ID: {task_run.id}")

time.sleep(10)

runs = meters_conversion_task.list_runs()
latest = runs[0]
print(f"Status:  {latest.status}")
print(f"Message: {latest.message}")
```

You can do a quick sanity check on the conversion by comparing a few values from both datastreams:

```python
raw = stage_datastream.get_observations(fetch_all=True).dataframe
converted = stage_meters_datastream.get_observations(fetch_all=True).dataframe

comparison = raw.merge(converted, on='phenomenon_time', suffixes=('_ft', '_m'))
comparison['expected_m'] = comparison['result_ft'] * 0.3048
print(comparison[['phenomenon_time', 'result_ft', 'result_m', 'expected_m']].head(10))
```

## What we've built

We now have three datastreams for the Logan River site: the raw 15-minute gage height from USGS, a daily mean derived from it, and a meters-converted version of the raw data — all kept up to date automatically by the orchestration system.

In Part 5, we'll set up a monitoring task that watches one of these datastreams and sends an alert when values go outside an acceptable range.