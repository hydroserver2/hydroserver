# Loading Data

HydroServer offers four ways to load data:

1. **Direct API calls**

   Send observations straight to HydroServer’s SensorThings API using HTTP requests.

2. **hydroserverpy Python client**

   A lightweight wrapper around the API that simplifies authentication, request batching, and error handling.

3. **Streaming Data Loader (SDL) Orchestration System**

   A cross-platform desktop app (Windows, macOS, Ubuntu) that reads one or more datasource JSON files, invokes hydroserverpy under the hood, and runs ETL jobs on a schedule. Perfect for simple, stand-alone deployments.

4. **Airflow Orchestration System**

   A Docker-deployable extension to Apache Airflow and hydroserverpy that provides advanced scheduling, dependency management, and monitoring.

## Orchestration Systems

The APIs and Python Client are discussed in detail in other sections, so here we'll focus on the Streaming Data Loader and Airflow Orchestration System. At their core, both a simply wrappers around the hydroserverpy Client app with the added functionality of scheduling for automated continuous data loading.

## main concepts

HydroServer has two main concepts for loading data with an orchestration system:

1. A datasource JSON configuration file defines how data will move from source to target.
2. An orchestration system reads one or more datasources and creates and runs the appropriate jobs.

## Getting started with orchestration systems

The workflow for getting setup with any orchestration system will be the same:

1. Download the orchestration system.

2. Provide credentials for the workspace you're pushing data to (username and password or API key) and point it at the URL of your HydroServer instance.

3. Once credentials are provided, the system will register itself as an orchestration system in HydroServer, and you'll then be able to view your registered orchestration systems on the 'Job Orchestration' page of the Data Management App.

4. There, you'll be able to create new data sources for your orchestration system by clicking the 'create new data source' button. This will walk you through a form in which you'll define the schedule, the source URI where you're extracting data fromm, and expected format of the returned data.

5. On submission of the data source form, a table row will be created for your orchestration system with that data source. Clicking the row will take you to the details page for that data source. There, you'll define the mapping of your source data identifiers to their associated datastreams. The data source details page provides a 'Payloads' table which represents the mappings for one extracted data file (a CSV file or JSON file).

For example, consider the following CSV file:

```CSV
timestamp,waterlevel_ft,discharge_cfs
2023-10-26T01:00:00-07:00,20.5,35.0
2023-10-26T01:15:00-07:00,21.2,33.1
2023-10-26T01:30:00-07:00,21.8,37.2
. . .
```

Hydroserver needs to know that the data from column 'waterlevel_ft' will be loaded to the datastream with ID 1 and the data from column 'discharge_cfs' will be loaded into the datastream with ID 2. From the payloads form you'll click 'add new payload', then 'add new mapping'. There you'll set you 'source identifier' to 'waterlevel_ft' and 'target identifier to the datastream with ID 1.

6. Once your data source is defined and payloads are mapped, the orchestration system will manage the rest.
