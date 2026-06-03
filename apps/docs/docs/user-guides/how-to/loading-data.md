# Loading Data

You can use several different methods to get data into HydroServer. Which option you choose depends on how you are collecting data, how up to date you need your data to be, and whether you need to integrate with commercial or third-party software systems. HydroServer provides the following options for loading data.

## Direct Streaming through HydroServer's API

Internet-connected dataloggers can be programmed to make HTTP POST requests to insert data directly into HydroServer's database through HydroServer's SensorThings API. For more information about this option, consult the following guides:
* [Loading Data with the SensorThings API](/user-guides/how-to/loading-data-with-sensorthings.md): This is a generic article about how to use the SensorThings API to load data.
* [Loading Data from an Internet connected datalogger](/user-guides/how-to/loading-data-with-datalogger.md): Learn how to send data to HydroServer directly from an Internet connected datalogger, including example code.

## Load Data Via HydroServer's Job Orchestration System

HydroServer provides a built-in Job Orchestration System for setting up scheduled extract, transform, and load (ETL) tasks. The Orchestration System uses the Django Celery integration to run scheduled tasks offline so they don't impact your main HydroServer web applications, but the setup of tasks is managed through the Job Orchestration Page in the HydroServer Data Management Web App. The Job Orchestration system uses "data connections" and "tasks" to define how data is extracted, transformed into a standard format, and loaded automatically through the HydroServer API. Data connections and tasks can be configured from the Data Management App's Job Orchestration page or via the API.

## Via HydroServer's Streaming Data Loader

The HydroServer Streaming Data Loader (SDL) is a desktop software app that can be installed on Windows, Mac, or Linux computers. It is designed to connect to CSV data files that are either stored locally or in a web-accessible folder to load data into a HydroServer instance. This is a push-based data loader – the SDL pushes data into HydroServer.

The SDL provides a user interface for configuring connections to CSV file, specifying which data columns to load, and mapping those data columns to datastreams in HydroServer. 

[Download the SDL](/references/streaming-data-loader.md)

## Via a Script or Client Program

You can write your own scripts or full on job orchestration systems that use HydroServer's API directly to load data. To make this significantly easier, HydroServer provides client applications such as hydroserverpy: a Python client package that wraps the API so it can be used in straightforward Python one liners: `hydroserver.login()`, `hydroserver.load_data()`, etc. 

[Learn how to use hydroserverpy](/user-guides/how-to/using-the-python-client.md)

## Via the API

If you are using a programming language other than Python (or even if you are using Python), you can always call the API directly to load data. [Go to the API reference page for more information](/references/hydroserver-apis.md).

## Quick Guidance on Which Data Loading Method to Use

If you don't want to write code to load data, the following guidance may be helpful.

Choose **Streaming Data Loader (SDL)** if you want:

- A simple, stand-alone desktop app
- Minimal infrastructure and ops overhead
- Local file or small API sources
- A quick way to get started for a single team or workstation

Choose **HydroServer's Job Orchestration System** if you want:

- A server-side, always-on scheduler
- Centralized logs and monitoring
- Multiple users and many data connections
- A production deployment that should run without a desktop app

## Compare at a glance

| Decision factor      | Streaming Data Loader (SDL)            | Job Orchestration System               |
| -------------------- | -------------------------------------- | -------------------------------------- |
| Runs on              | A desktop or workstation               | Your HydroServer server                |
| Best for             | Small deployments, pilots, single team | Production, multi-team, high volume    |
| Ops overhead         | Low                                    | Medium                                 |
| Availability         | Depends on computer it runs on         | 24/7 with server uptime                |
| Scaling              | Limited to one machine                 | Scales with server resources           |
| Typical data sources | Local files, lightweight APIs          | Network-accessible APIs, hosted stores |
| Admin experience     | Desktop UI                             | Managed from HydroServer               |

## When SDL is the right fit

SDL is ideal if you want a lightweight scheduler without additional infrastructure. It shines when data is pulled from local files, you have a small number of data connections, or you want to keep the orchestration layer off the server. It's also a good fit for pilots, training, or field deployments where a desktop app is acceptable.

## When the Job Orchestration System is the right fit

The Job Orchestration System is the right choice when you need an always-on orchestration system that lives with HydroServer. If your deployment supports multiple users, has many data connections, or requires centralized scheduling and monitoring, Celery is the better long-term option. It also fits well when data sources are network-accessible and your HydroServer instance is already running in a server environment.
