# Part 5: Setting Up Monitoring

> **Note:** Like Parts 3 and 4, this part requires HydroServer's orchestration system to be installed and running. The playground instance does not currently support monitoring tasks.

The last piece of our pipeline is monitoring. A monitoring task runs on a schedule and checks one or more datastreams against rules you define. When a rule is violated — a value goes out of range, data stops arriving, or a sensor reading gets stuck — HydroServer sends an email alert to whoever you designate.

In this part we'll create a monitoring task for the Logan River stage datastream and attach two rules to it: a range check that flags abnormally high or low water levels, and a missing data check that alerts us if the USGS feed goes quiet.

## Create a monitoring task

Monitoring tasks are associated with a site, not a specific datastream — the datastream is specified when you define each individual rule. The `recipients` list is where alert emails get sent.

```python
stage_monitor = hs_api.monitoringtasks.create(
    name='Logan River Stage Monitor',
    thing=logan_river_site,
    description='Monitors gage height for out-of-range values and data gaps.',
    recipients=['your@email.com'],
    interval=15,
    interval_period='minutes',
    enabled=True,
)

print(f"{stage_monitor.name}: {stage_monitor.uid}")
```

Running every 15 minutes keeps the monitoring in step with the incoming USGS data.

## Add a range rule

The range rule triggers an alert whenever the most recent observation falls outside the bounds you set. For Logan River, we'll flag anything below 0.5 feet — which could indicate a sensor problem or extremely low flow — or above 5.0 feet, which would be approaching flood stage.

```python
range_rule = hs_api.monitoringrules.create(
    task_id=stage_monitor.uid,
    datastream=stage_datastream,
    rule_type='range',
    min_value=0.5,
    max_value=5.0,
)
```

You can update the thresholds at any time by modifying the rule object and calling `save()`:

```python
range_rule.max_value = 4.5
range_rule.save()
```

## Add a missing data rule

The missing data rule triggers when no new observations have arrived within a given window. Since USGS publishes data every 15 minutes, two hours without a new reading is a reliable signal that something is wrong — either the sensor is offline or the automated fetch is failing.

```python
missing_data_rule = hs_api.monitoringrules.create(
    task_id=stage_monitor.uid,
    datastream=stage_datastream,
    rule_type='missing_data',
    window_interval=2,
    window_interval_units='hours',
)
```

## Trigger and verify

Let's trigger the task manually to confirm both rules are being evaluated.

```python
import time

task_run = stage_monitor.trigger()
print(f"Task triggered. Run ID: {task_run.id}")

time.sleep(10)

runs = stage_monitor.list_runs()
latest = runs[0]
print(f"Status:  {latest.status}")
print(f"Message: {latest.message}")
```

A `SUCCESS` status means the task ran and evaluated your rules — not necessarily that everything is fine with the data. If a rule was violated, the recipients will have received an email. You can verify which rules are attached to the task with:

```python
for rule in stage_monitor.rules:
    print(rule.rule_type, rule.datastream_name)
```

## What we've built

Over the course of this tutorial series, we've used `hydroserverpy` to build a complete end-to-end monitoring pipeline entirely in Python:

- **Part 1** — Created a workspace, monitoring site, linked metadata, and a discharge datastream for the Blacksmith Fork River.
- **Part 2** — Loaded a month of synthetic discharge observations and visualized them as a time series plot.
- **Part 3** — Created a second site mirroring a real USGS gauging station on the Logan River and set up an automated ETL task that pulls live gage height readings from the USGS API every 15 minutes.
- **Part 4** — Defined two data product tasks that run on the raw USGS data: one aggregating to daily mean values, and one converting units from feet to meters.
- **Part 5** — Set up a monitoring task with a range check and a missing data check, so you get an email if the Logan River stage goes out of bounds or the data feed goes silent.

From here, you might explore adding more monitoring rules (try `rate_of_change` to catch sudden spikes), connecting additional USGS sites by reusing the data connection you built in Part 3, or looking at the [hydroserverpy API reference](/user-guides/how-to/using-the-python-client) for the full list of available methods.