# Loading Data

You can use several different methods to get data into HydroServer. Which option you choose depends on how you are collecting data, how up-to-date you need your data to be, and whether you need to integrate with commercial or third-party software systems. HydroServer provides the following options for loading data.

## Direct Streaming through HydroServer's API

Internet connected dataloggers can be programmed to make HTTP POST requests to insert data directly into HydroServer's database through HydroServer's SensorThings API. For more information about this option, consult [HydroServer's API documentation](/how-to/sensor-things/post-sensor-things.md).

## Load Data Via HydroServer's Job Orchestration System

HydroServer provides a built-in Job Orchestratio System for setting up scheduled extract, transform, and load (ETL) tasks. The Orchestration System uses the Django Celery integration to run scheduled tasks offline so they don't ipact your main HydroServer web applications, but the setup of tasks is managed through the HydroServer Data Management Web App. The Job Orchestration system uses "data connections" and "tasks" to define how data is extracted, transformed into a standard format, and loaded automatically through the HydroServer API. Data connections and tasks can be configured from the Data Management App's Job Orchestration page or via the API.

## Via HyddroServer's Streaming Data Loader

The HydroServer Streaming Data Loader (SDL) is a desktop software app that that can be installed on Windows, Mac, or Linux computers. It is designed to connect to CSV data files that are either stored locally or in a web accessible folder to load data into a HydroServer instance. This is a push-based data loader - the SDL pushes data into HydroServer.

The SDL provides a user interface for configuring connections to CSV file, specifying which data columns to load, and mapping those data columns to datastreams in HydroServer. 

[Download the SDL](/references/orchestration/sdl-download.md)

## Via a Client Program

You can write your own scripts or full on orchestration systems that use HydroServer's API directly to load data. To make this significantly easier, HydroServer provides client applications such as hydroserverpy: a Python client package that wraps the API so it can be used in straightforward Python one liners: `hydroserver.login()`, h`ydroserver.load_data()`, etc. 

[Learn how to use hydroserverpy](/how-to/hydroserverpy/hydroserverpy-examples.md)

## Via the API

If you are using a programming language other than Python (or even if you are using Python), you can always call the API directly. [Go to the API section for more information](/references/api/data-management-api).
