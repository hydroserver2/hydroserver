# Part 2: Loading and Visualizing Observations

Now that we have a datastream set up, let's put some data in it. In this part we'll generate a month of sample discharge observations, load them into HydroServer, fetch them back, and plot them.

Before we start, make sure you have `pandas`, `numpy`, and `matplotlib` installed in your environment:

```bash
pip install pandas numpy matplotlib
```

## Generate sample observations

Since we're working with a fictional monitoring station, we'll generate some synthetic discharge data rather than using a real dataset. The code below creates 30 days of 15-minute readings starting April 1, 2026, with a gentle rise-and-fall pattern typical of spring snowmelt.

```python
import pandas as pd
import numpy as np
from datetime import datetime, timezone

np.random.seed(42)

times = pd.date_range(
    start=datetime(2026, 4, 1, tzinfo=timezone.utc),
    periods=96 * 30,  # 96 readings per day, 30 days
    freq='15min'
)

base_discharge = 1.5 + 0.8 * np.sin(np.linspace(0, 2 * np.pi, len(times)))
noise = np.random.normal(0, 0.05, len(times))
discharge_values = np.clip(base_discharge + noise, 0.1, None)

observations = pd.DataFrame({
    'phenomenon_time': times,
    'result': discharge_values.round(3)
})

print(observations.head())
```

You should see a DataFrame with two columns — `phenomenon_time` and `result` — which is exactly the format HydroServer expects.

## Load observations into HydroServer

Loading the data is straightforward. Pass the DataFrame to `load_observations` on your datastream object. If you closed your session since Part 1, you can look up your datastream first:

```python
# If continuing from Part 1, you already have discharge_datastream in memory.
# If starting fresh, look it up by UID:
# discharge_datastream = hs_api.datastreams.get(uid='your-datastream-uid')

discharge_datastream.load_observations(observations)
print(f"Loaded {len(observations)} observations.")
```

By default, `load_observations` runs in `insert` mode, which adds new observations to the datastream if observations at those timestamps don't already exist. If you want to overwrite everything in the provided range, you can pass `mode='replace'` instead.

## Fetch observations back

Now let's retrieve the data we just loaded to confirm it made it in correctly.

```python
result = discharge_datastream.get_observations(
    phenomenon_time_min=datetime(2026, 4, 1, tzinfo=timezone.utc),
    phenomenon_time_max=datetime(2026, 5, 1, tzinfo=timezone.utc),
    fetch_all=True
)

df = result.dataframe
print(f"Retrieved {len(df)} observations.")
print(df.describe())
```

`get_observations` returns an `ObservationCollection` — a paginated result object. Calling `.dataframe` on it gives you a standard pandas DataFrame. We passed `fetch_all=True` here so that all pages are merged automatically; for large datasets with millions of rows you may want to work page by page instead.

## Plot the data

```python
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

fig, ax = plt.subplots(figsize=(12, 4))

ax.plot(df['phenomenon_time'], df['result'], linewidth=0.8, color='steelblue')

ax.set_xlabel('Date')
ax.set_ylabel('Discharge (m3/s)')
ax.set_title('Blacksmith Fork River Discharge — April 2024')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
fig.autofmt_xdate()
plt.tight_layout()
plt.show()
```

You should see a smooth curve that rises through mid-April and falls off toward the end of the month — our simulated snowmelt hydrograph.

## What we've built

We now have a month of discharge observations stored in HydroServer and know how to get them back out as a pandas DataFrame. From here, you have everything you need to start doing your own analysis on real data.

In Part 3, we'll stop loading data manually and instead set up an automated ETL pipeline that pulls discharge readings from a web API on a schedule.