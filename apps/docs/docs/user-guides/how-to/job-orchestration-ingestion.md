# Job Orchestration System
## Loading Data/ Data Ingestion 
This explains how to use the **HydroServer Job Orchestration System** to load data from a remote CSV, LoggerNet `.dat` file, or API-like data source into HydroServer datastreams. This type of task is an **ingestion task**, also called an **ETL data loading task**.

ETL means:

```text
Extract → Transform → Load
```

In HydroServer, this means:

```text
Remote source file or API
    ↓
Job Orchestration reads the source
    ↓
Source columns are mapped to HydroServer datastreams
    ↓
Observation values are loaded into HydroServer
```

---

## 1. Before You Begin

Before creating an ingestion task, make sure the following items already exist in HydroServer:

- A **workspace** where you have permission to create and manage content
- A **site** where the observations will be stored

<img src="Ingestion/1Workspace.png" alt="Download page" width="750">

- One or more **datastreams** where the imported data values will be loaded

<img src="Ingestion/2Datastream.png" alt="Download page" width="750">

- A remote source file or URL that HydroServer can access

The Job Orchestration System does **not** upload a file from your local computer. Instead, it reads data from a source URL. The source URL must point to data that HydroServer can access online, such as a remote CSV file, LoggerNet `.dat` file, or web-accessible data endpoint.

Example source URL:

```text
http://example-server.org/data/station_data.csv
```

For a LoggerNet file, the source may look like this:

```text
http://example-server.org/data/CR800_Station_Data.dat
```

---

## 2. Open the Job Orchestration Page

In HydroServer, go to the top navigation menu and select: Data management → Job orchestration

<img src="Ingestion/3JobOrchestration.png" alt="Download page" width="750">

This opens the Job Orchestration page. On the left side of the page, select **Ingestion**.

---

## 3. Create a New Data Connection

A **data connection** tells HydroServer where the source data are located and how the source file should be read.
On the **Ingestion** page, click the blue **plus** button next to **Connections**. A window titled **Create a new data connection** will open.

<img src="Ingestion/4.0CreateDataConnection.png" alt="Download page" width="750">

To create a data connection, first enter a clear name that helps identify the source file or station. Then paste the remote source URL into the **Source URL** field. The source URL should point directly to the raw data file, not to a preview webpage. When opened in a browser, the URL should show the data as text with rows and columns.

<img src="/Ingestion/4DataConnection.png" alt="Create a new data connection form" width="750">


In the **Payload** section, choose the payload type based on the source file format. For most CSV-style files and LoggerNet `.dat` files, select `CSV`. If the file has column names in a header row, select **Identify columns by name**. Then enter the correct **file header row number** and **data start row number**. The header row is the row that contains the column names, and the data start row is the first row that contains actual observation values. 

<img src="/Ingestion/5csvfile.png" alt="Create a new data connection form" width="750">

Next, select the file delimiter. Use `Comma` for comma-separated files and `Tab` for tab-delimited files. 

In the **Timestamp** section, enter the exact name of the timestamp column as it appears in the source file, such as `TIMESTAMP`, `ResultTime`, or `timestamp`. The capitalization must match the source file. Select `ISO 8601` if the timestamps use a standard date/time format. In the **Timezone** section, use `UTC (Default)` if the source file already uses UTC timestamps or includes a UTC offset. If the source file uses local time without a timezone offset, the correct timezone or offset should be selected if available so HydroServer can store the values correctly in UTC.

After all settings are filled in, click **Save**. The data connection will appear in the left-side **Connections** list. 

At this point, HydroServer knows:

- Where the source file is located
- How to read the file
- Which row contains the column names
- Which row contains the first data value
- Which column contains the timestamps

However, the data connection alone does not load data into a datastream. You must create an ingestion task and define the column-to-datastream mapping.

---

## 4. Add an Ingestion Task

Click the data connection you created. Then click **Add task**. The **Add task** window will open.

<img src="/Ingestion/6AddTask.png" alt="Add a new ingestion task under a data connection" width="750">

Enter a clear task name that describes what data will be loaded, such as `Load Snow Depth Data` or `Load Discharge Data for BC_CONF_A`. The task name should be specific enough that users can understand its purpose later, especially when there are multiple ingestion tasks in the same workspace.

In the schedule section, the task can either be run manually or on a repeating schedule. For initial testing, it is usually better to turn the schedule off and run the task manually first. This allows you to confirm that the source URL, timestamp settings, and data mappings are correct before the task starts running automatically. After the task has been tested successfully, a schedule can be enabled, such as running every day, every hour, or using a crontab expression.

One ingestion task can load more than one source column into HydroServer. To add another mapping, click **Add mapping**.

For example, one source file may contain multiple variables:

```text
Stage
Discharge_cfs
WaterTemp_PT
Cond
```

These can be mapped to different datastreams:

```text
Stage → Test Stage (cm) - Raw data
Discharge_cfs → Test Discharge (cfs) - Provisional data
WaterTemp_PT → Test Water Temperature (C) - Raw data
Cond → Test Conductivity (ms/cm) - Raw data
```

This is useful when one remote logger file contains many sensor columns from the same station.

After entering the task name, schedule, and mappings, click **Save task**. The task will appear under the selected data connection.

---
## Ingesting Data from USGS

HydroServer can ingest data directly from the United States Geological Survey (USGS) using a USGS Water Services URL. This is useful for loading USGS streamflow, gage height, water temperature, or other time-series data into a HydroServer datastream.

For daily values, enter the following generic URL in the **Source URL** field when creating a new data connection, as described in Section 3:

```text
https://waterservices.usgs.gov/nwis/dv/?format=rdb&sites={USGS_SITE_ID}&parameterCd={PARAMETER_CODE}&startDT={START_DATE}&endDT={END_DATE}&siteStatus=all
```

Replace the placeholders with the correct values:

| Placeholder | Description |
|---|---|
| `{USGS_SITE_ID}` | USGS monitoring site ID |
| `{PARAMETER_CODE}` | USGS variable or parameter code |
| `{START_DATE}` | First date of data to load |
| `{END_DATE}` | Last date of data to load |

Example:

```text
https://waterservices.usgs.gov/nwis/dv/?format=rdb&sites=10109001&parameterCd=00060&startDT=2024-01-01&endDT=2024-01-31&siteStatus=all
```

This example loads one month of daily discharge data for USGS site `10109001`.

---

### Common USGS Parameter Codes

| Parameter Code | Variable | Unit |
|---|---|---|
| `00060` | Discharge / streamflow | cubic feet per second, cfs |
| `00065` | Gage height / stage | feet |
| `00010` | Water temperature | degrees Celsius |
| `00095` | Specific conductance | microsiemens per centimeter |
| `00300` | Dissolved oxygen | milligrams per liter |
| `00400` | pH | standard units |

For example:

```text
parameterCd=00060
```

means the requested data are discharge values.

---

## 5. Run the Task

To test the ingestion task, click **Run now**.

<img src="/Ingestion/7RunTask.png" alt="Run the task" width="750">

HydroServer will read the source file, parse the configured timestamp and source columns, and load the mapped values into the selected target datastreams. If the task succeeds, you will see a green status indicator and a message showing how many observations were loaded.

<img src="/Ingestion/8GreenTick.png" alt="Successful ingestion run showing loaded observations and green status" width="750">

If the task does not succeed, the task status may show **Needs attention** or another warning. You can use the Status Filter to review the status of task failure.

---

## 6. View Run Details

Click **Details** for a task run to view more information.

The run details includes:

- Number of observations loaded
- Runtime source URL
- Start time
- Duration
- Run status

---

## 7. Verify the Loaded Data

After the task runs successfully, go back to the site page and check the target datastream.

Confirm that:
- The datastream has observations
- The latest observation looks reasonable
- The units match the source column
- The timestamps are correct
- The number of observations is reasonable for the source file
---
