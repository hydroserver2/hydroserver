# Automated Job Orchestration System

_Functional Specifications_

## 1 Introduction


Utah Division of Water Rights (DWRi) maintains a data system that requires running several different types of automated data extract, transform, and load (ETL) tasks. These ETL tasks include regularly scraping data from partner data sources - i.e., extracting time series data from designated data sources, transforming the data from whatever format is provided by the remote data source to a format that can easily be worked with and loaded, and then loading the data into DWRi’s operational database. Tasks also include aggregating data from its original temporal resolution (if sub-daily) to daily resolution, performing units conversions (e.g., converting from a measured value to a different quantity using a lookup table), calculating values for “virtual” stations representing some arithmetic combination of data from two or more stations, performing automated rules-based quality control on incoming data, and potentially others. This document describes requirements and functional specifications for an ETL task orchestration system/tool (referred to as ‘the Orchestrator’ for the rest of this document) that automatically executes scheduled ETL tasks, consistently logs ETL task-related information (e.g., events and errors associated with those ETL tasks), sends automated notifications associated with ETL tasks, and enables DWRi employees to track the status of configured ETL tasks.

## 2 Definitions


Data Source A file path, API endpoint, or IP address from which the Orchestrator must extract data for one or more monitoring stations/datastreams. A data source can be the equivalent of a DWRi “Collection System”, but it can also be as simple as the path to a single comma separated values (CSV) file containing data. Simply put - a data source is what the Orchestrator is connecting to for retrieving one or more payloads.

Data Connection: A reusable user-defined configuration that specifies what an ETL task will do. It defines where the data is coming from (the data source), how the data will be transformed, and where the data will be loaded.

Datastream: A time series of data values for an observed property collected at a monitoring site.

Destination Datastream: A datastream in HydroServer into which data is being loaded by an ETL task.

Orchestration System: A software or software system that executes scheduled ETL tasks. For this functional specifications document, this is primarily Django’s Celery Task Queue, but also includes the HydroServer Streaming Data Loader software. An orchestration system that is bundled with a HydroServer instance and is available upon server start is called an internal orchestration system. An orchestration system that runs outside of the main server is called an external orchestration system.

Extractor: A piece of software that interprets a data connection’s extractor configurations and connects with a data source (including authentication where required) and extracts a payload from the data source (i.e., retrieves a CSV file, XML string, JSON string, or bytestream as the payload). The extractor is run once per payload retrieved within a scheduled ETL task.

Loader: A piece of software interprets a data connection’s loader configurations and loads data to HydroServer from a Python Pandas DataFrame object. The Loader loops through the datastream columns in the Pandas DataFrame and loads data for all datastreams within the DataFrame. The DataFrame object has one timestamp column and has one or more data columns each of which represents data for a datastream. The loader is run once for each payload retrieved within a scheduled ETL task.

Monitoring Station: A location at which data are collected. A monitoring station may have data for multiple datastreams (e.g., stage and flow or elevation and storage).

Payload: A CSV file, JSON string, XML string, or bytestream extracted from a data source containing data for one or more datastreams. A payload has a single timestamp “column” containing date/time information for data values and contains one or more data “columns” containing numeric data values for a corresponding datastream in HydroServer. All data “columns” in a payload must share the same timestamp “column”.

Scheduled ETL Task: A scheduled task that is run by the Orchestrator on a user-defined schedule. The scheduled ETL task executes a script that extracts a payload from a data source defined by a data connection, transforms the retrieved payload to a Pandas DataFrame object, and loads data from the Pandas DataFrame to the HydroServer instance.

Script: A script is the equivalent of one of DWRi’s data scraping scripts. All scripts are written in Python and define the code that is executed by a scheduled ETL task. A script contains the code to extract payload(s) from a data connection using an extractor, transform the payload to a Pandas DataFrame using a transformer, and load data from the Pandas DataFrame object into HydroServer. A scheduled ETL task executes one script. The same script may be used by multiple scheduled ETL tasks that inject different settings to configure the script.

Transformer: A piece of software that interprets a data connection’s transformer configuration to take a payload (i.e., a CSV file, XML string, JSON string or bytestream) extracted from a data connection and converts it to a Pandas DataFrame object. A transformer is run once for each payload retrieved within a scheduled ETL task. Transformers are split into two categories:
- StructureTransformer: Handles structural tasks such as reading headers, identifying timestamp columns, parsing the payload into a corresponding Pandas DataFrame.
- DataTransformer: Performs arithmetic operations, units conversions, or lookups on the DataFrame’s data values. Can be chained after a StructureTransformer to refine or modify the parsed DataFrame before it is loaded into HydroServer.
Workspace: A structure within HydroServer within which “resources” can be organized for purposes of access control. Resources include monitoring sites, datastreams, metadata elements, and orchestration systems.

## 3 Requirements


The following are requirements that must be met by the Orchestrator:

- The Orchestrator must replace all key functionalities of DWRi’s legacy data scraping scripts using HydroServer as the destination for all data, including:
- Scraping raw data into HydroServer’s database.
- Calculating data values from scraped data via a station/variable specific lookup table.
- Calculating daily mean values by aggregating sub-daily data.
- Calculating virtual data values by combining data values from multiple stations.
- The Orchestrator must provide a user interface in HydroServer’s Data Management Web App for creating and managing data connections, including:
- Ability to define specific variables/parameters needed to make the data connection (e.g., URLs/paths, transformation approach, etc).
- Ability to create a new data connection.
- Ability to edit or delete an existing data connection.
- Ability to display a list of all data connections for a workspace.
- The Orchestrator must provide a user interface in HydroServer’s Data Management Web App for creating and monitoring scheduled ETL tasks, including:
- A list of scheduled ETL tasks and all configured destination datastreams within a task.
- Ability to create a new scheduled ETL task.
- Ability to edit or delete an existing ETL task.
- Ability to visually display the status of an existing ETL task - e.g., successfully run ETL tasks are green, and failed ETL tasks are red.
- Ability to interrogate the log information for a scheduled ETL task.
- Ability to create a new destination datastream within a task.
- Ability to edit and delete existing destination datastream(s) within a task.
- Ability to define specific variables/parameters needed to perform a scheduled ETL task for the data connection (e.g., parameters for URLs/paths, authentication information, mapping of data to datastream IDs, etc.).
- Ability to specify a schedule on which the ETL task is run.
- Ability to view useful statistics or metrics about a scheduled ETL task - e.g., number of runs, number of successful runs, number of errors, execution time, etc. Metrics may be specific to scheduled ETL task types.
- Users must log in to view and configure data connections and configured tasks.
- Users who are not logged in will not be able to access data connections or tasks.
- Access control must be handled at the HydroServer workspace level - i.e., users who create or have been given edit access to a HydroServer workspace by a workspace owner will have access to all configuration options for all data connections and tasks within the workspace.
- Users with different roles (e.g., owner, editor, viewer) will have access to view and/or manage data connections and tasks within a workspace.
- The Orchestrator must automatically and efficiently run scheduled ETL tasks within a process queue according to the schedule that has been set for each task.
- Scheduled ETL tasks for data connections must be capable of doing the following:
- Extracting data and loading it into HydroServer.
- Aggregating raw, sub-daily data to daily average values and loading aggregated data values into HydroServer.
- Transforming raw data (e.g., voltage or amperage measurement) to derived values (e.g., flow) using a site/variable specific lookup table prior and loading data values into HydroServer.
- Extracting data for multiple source datastreams, calculating values for a “virtual” datastream as some arithmetic combination of values from source datastreams, and then loading calculated values into HydroServer.
- Individual scheduled ETL tasks must be independent.
- The code for scheduled ETL tasks must be contained within a script written in Python.
- The Orchestrator must gracefully handle errors when executing scheduled ETL tasks. It must be capable of recovering and continuing other ETL tasks when a task fails.
- The Orchestrator must write status information (i.e., success, failure) to HydroServer’s database after each attempt to run a scheduled ETL task.
- Status information will be displayed within HydroServer’s user interface for creating and managing tasks.
- Status information will be created at the task level.
- The Orchestrator must store in the configuration for a scheduled ETL task the date on which they were last updated and by whom. This information will be displayed when the configuration for a scheduled ETL task is accessed.
- The Orchestrator must be capable of sending notifications via email to a designated set of workspace collaborators when a scheduled ETL task fails or requires intervention.
- The designated list of workspace collaborators who will receive notifications must be a configurable setting of the data connection.
- Emails must contain sufficient information for those receiving the notifications to isolate the task for examining log information.
- The Orchestrator must keep a detailed log of success information and errors encountered for each task for the owners’ reference during debugging.
- A formal information model (a definition of the information required to create, configure, and execute ETL tasks for data connections) and schema (an encoding of the information model) must be defined and enforced for how data connections and scheduled ETL tasks are defined and stored by the Orchestrator.
- The Orchestrator must load data for all tasks to a HydroServer instance through HydroServer’s APIs.
- The Orchestrator must run scheduled ETL task(s) to aggregate sub-daily data for a user-defined set of source datastreams to daily average (or end of interval) values that are written to separate, time aggregated destination datastreams.
- A standardized, scheduled ETL task must be available to load data into DWRi’s HydroServer instance from any data connection that shares data in DWRi’s standardized data format(s).
- The Orchestrator must follow HydroServer’s dev, test, and production deployments to enable DWRi employees to test changes to develop and test existing ETL tasks or the addition of new ETL tasks prior to implementing them in the production instance.

## 4 Information Model


The following statements define the information model for the Orchestrator:
- A person is the owner for one or more workspaces.
- A workspace must have one owner but may also have multiple collaborators with editor or viewer roles.
- A workspace may contain one or more data connections.
- One or more workspace collaborators receive notifications for a data connection.
- An ETL task provides data for one or more destination datastreams.
- A datastream is as defined in HydroServer’s data model (a time series of values for an observed property measured at a monitoring station) and has a single datastream ID.
- A data connection has a type with type-specific attributes required for retrieving and parsing payload(s) containing data for the destination datastreams belonging to that data connection.
- ETL tasks may require specific attributes required for retrieving and parsing a payload containing source data retrieved from a data connection and then loaded into one or more more destination datastreams.
- A payload is dynamically retrieved from a data connection by an ETL task based on information specified for that data connection and destination datastreams belonging to that data connection.
- A payload contains data for one or more destination datastreams.
- A payload generally has one datetime “column”, but may contain multiple data “columns” where each “column” contains data values for a single datastream. There are some exceptions to this rule.
- A data connection may have one or more scheduled ETL tasks.
- An orchestration system handles scheduled ETL tasks for one or more data connections.

The following shows the data model used to encode this information model:

Figure 1. Orchestration system data model. Blue entities represent HydroServer’s database tables. Green boxes represent tables provided by Django Celery. To facilitate control, all orchestration tables will be scoped by workspace. Since extractor, transformer, and loader schemas will differ to accept a variety of data sources, the ETL settings of a Data Connection will be stored as JSON. The HydroServer API will expose only the blue entities to developers and users, while the green entities will be encapsulated away and are reserved for internal task scheduling.

## 5 Supported Functionality


The following sections describe specific functionalities that will be provided by the Orchestrator:

### 5.1 User Management and Access Control


User management for Orchestrator functionality will be handled by HydroServer at the workspace level as follows:
- Users will log into HydroServer using their UtahID account provided by the State of Utah DTS.
- Admin HydroServer user(s) will be assigned by developers.
- Admin HydroServer users will have the ability to set roles for other users within any workspace.
- Admin HydroServer users will have full permissions on all HydroServer resources (all data connections and ETL tasks) and can act for and on behalf of HydroServer users where necessary (e.g., if a user is no longer able to perform a necessary function).
- The creator of a workspace will be the original owner of that workspace.
- A workspace has one owner, but may have multiple collaborators with edit or view access.
- Collaborators within a workspace can add other collaborators with a role less than or equal to their own role:
- The owner can add collaborators with edit or view access.
- An editor can add collaborators with edit or view access.
- A viewer can add other viewers.
- Users with owner or editor access on a workspace can create new data connections and ETL tasks, edit existing data connections and ETL tasks including modifying schedules or pausing and resuming tasks, and delete existing data connections and ETL tasks within that workspace.
- Users with view access on a workspace will be able to view data connections and ETL tasks within that workspace.

### 5.2 User Interface for Creating and Managing Data Connections and ETL Tasks


The Orchestrator will implement a user interface for creating and managing workspaces, data connections, and ETL tasks within workspaces. This will be done within the HydroServer Data Management Web Application and will allow the following:
- Create, view, edit, and delete data connections within a selected workspace. Configuration options for data connections must include:
- Data connection name.
- General settings necessary for the extractor to retrieve payload(s) from the data connection, which may include:
- A file path, URL,  or URL pattern to retrieve a payload.
- Credentials or authentication parameters for data connections requiring secure access.
- Attributes specifying specific variables/parameters that can be modified at runtime when retrieving a payload from the data connection - e.g., parameters to be specified in URL query strings.
- NOTE: Data connection settings take the place of any script-level settings that existed in DWRi’s data scraping scripts. Any settings that existed for an entire script (e.g., an IP address that is reused many times, a template URL, or a template file path) must be specified at the data connection level or must be repeated within every ETL task that uses a data connection.
- Parameters required for a transformer to parse a payload retrieved from the data connection into a Pandas DataFrame. For example, for CSV file payloads:
- The row on which the column headers appear.
- The row on which data values begin.
- The file delimiter (default is comma).
- The name of the timestamp column.
- The format of the timestamp values.
- Time zone and/or offset information, etc.
- Create, view, edit, and delete the list of ETL tasks to be executed. Configuration options for ETL tasks include: destination datastreams within a selected data connection. Configuration options for a destination datastream must include:
- Task name.
- The data connection from which the source data will be retrieved.
- The schedule on which the ETL task will run.
- Specific parameters/settings required at run time to retrieve a payload from a data connection.
- NOTE: This may include settings inherited from the data connection with which the destination datastream is associated.
- Information mapping data “columns” in the payload retrieved from the data connection to destination datastreams in HydroServer.
- NOTE: Destination datastream settings take the place of any settings that were previously stored in DWRi’s DIVRT database. Where previously there was a record in the DIVRT database for each time series of data to be written to the DIVRT database, that information is now stored within the configuration for the destination datastream.
- View the status of scheduled ETL tasks for data connections within a selected workspace. Status information will include:
- When the scheduled ETL task for the data connection was last run.
- When the scheduled ETL task for the data connection is next scheduled to run.
- An indicator of whether the scheduled ETL task is behind schedule or on schedule.
- An indicator of the status of the last run of the scheduled ETL task (overall success or failure for the whole scheduled ETL task).
- Visual cues to the user about ETL task status - e.g., ETL tasks that have successfully run are colored green, ETL tasks that ran with errors are colored yellow, and ETL tasks that failed entirely are shown in red.
- NOTE: Failure conditions or exceptions for consideration may include:
- No new data returned for a datastream.
- The data connection was not accessible due to a network issue (API unavailable or returned an error).
- The data connection format has changed from what was expected.
- The URL parameters do not match what was expected - e.g., the partner has changed the location or URL for retrieving the payload.
- The station is no longer active and does not exist any more in the data connection. DWRi’s internal policy defines “active” as a station that has data for the last two calendar years.
- Pause a scheduled ETL task.

### 5.3 Supported Data Connections


The following data connections must be supported:
- Single CSV files - a single CSV file available either via a local file path or via HTTP or FTP protocols. This includes CSV files conforming to DWRi’s standard CSV data encoding format.
- Metridyne and Exactrac APIs - These APIs are used by many of DWRi’s data connections.
- DWRi Telemetry - legacy, pull based data connections retrieved from an IP address. There will be multiple of these, one data connection per IP address.
- DWRi Dataloggers - comma separated values files produced by DWRi’s Loggernet instance.
- HydroServer - data retrieved from HydroServer’s APIs.
- USGS - Daily or sub-daily data from USGS Water Data for the Nation.
- Other APIs - other APIs that provide data either using SensorThings or using DWRi’s standard CSV or JSON data encoding format.

### 5.4 ETL Task Scheduling


Users with edit access to a workspace will be able to schedule ETL tasks for data connections within a workspace according to their needs. The following options will be supported:
- Set a start time - this will be the base date/time on which the ETL task will start running.
- Set an end time - this will be the date/time on which the ETL task will no longer be run. The end time must be optional for ETL tasks that are intended to run indefinitely.
- Set an interval - this will be the time interval on which the ETL task will be run. Options will include 15 minutes, 30 minutes, 1 hour, 1 day, 1 week, and 1 month.
- Select an option to run a scheduled ETL task on demand - i.e., a “run now” menu option or button that immediately runs the ETL task. This option should be placed on the page showing status for each data connection for convenient access after a scheduled ETL task has been configured for a data connection.

### 5.5 Error Handling, Logging, and Messaging


The Orchestrator will implement logging for scheduled ETL tasks along with error handling to manage and retry failed operations. Logging will include:
- Successful runs.
- Amount of data or number of data values loaded for each datastream.
- Number of retries.
- Errors with adequate trace information for debugging purposes.
- Failed executions - the whole scheduled ETL task did not run.
- Failed datastreams - a datastream was not extracted because of an error.

Where errors are encountered and a scheduled ETL task is aborted because it cannot be run, a message will be sent to a designated set of workspace collaborators for the data connection with a message stating that the scheduled ETL task was not able to run and with enough information that the designated collaborators can attempt troubleshooting via the user interface. The Orchestrator will handle errors in a scheduled ETL task gracefully without impacting other ETL tasks, which may include:
- Logging failures.
- Retrying failed operations as defined by the ETL task.
- Killing long-running ETL tasks.
- Sending notifications to DWRi employees about errors or killed ETL tasks.

### 5.6 Standardized Data Format and Data Scraping Script/Task


A standardized data format will be defined that enables data providers to share data in a way that it can be automatically read by a standardized data scraping script/task. The purpose of this standardized data format is to provide a single format that developers of new data sources can use for providing data or to which existing data providers could switch to help standardize data scraped by Water Rights.

A standardized data scraping script will be developed that can be implemented as a scheduled ETL task to load data from any source that provides data in DWRi’s standardized format into DWRi’s HydroServer instance.

## 6 Notes about DWRi’s Existing Data Connections


The following sections describe how each of DWRi’s existing data connections fit within the Orchestrator described in this document.

### 6.1 DWRi Telemetry: Legacy Pull-Based TCP/IP Stations


DWRi previously used a set of Fortran scripts to retrieve data from these stations. Each Fortran script included an IP address from which data was to be retrieved. Each script extracted information about which stations to retrieve data for by querying DWRi’s DIVRT database. Each script then looped through its stations, retrieved a new measurement from each station, and wrote that new measurement to the DIVRT database. Stations had to be run in series because the cellular modems used to provide the TCP/IP connections to individual stations can only support one connection at a time (many stations may communicate through the IP address of a single repeater).

In the new system, new data for these stations will be retrieved as follows:
- All collection system and station variables that currently exist in the FORTRAN scripts (IP addresses, SDI-12/analog protocol commands, sleep times, retry attempts) will be scraped from the FORTRAN scripts and put into a single JSON config file.
- All TCP stations will be organized into a single ‘DWRi TCP Telemetry Network’ workspace to allow access control for related HydroServer things and datastreams.
- A faithful Python port will be written to do exactly what the FORTRAN code does, except the Python code will store station variables in a JSON file rather than as hardcoded values in the code. The ported Python script will initialize connections to TCP collection systems concurrently, while keeping calls to stations within the same collection system serial to efficiently pull data while meeting the hardware constraints of the collection system sensors (IP addresses do not support simultaneous connections).
- Rating curve and aggregation of data from sub-daily to daily will be performed exactly as the FORTRAN scripts define them. The Rating curve files will be stored in the same directory as the Python script and configuration file.
- IP address changes or other edits to the scraping system will be applied by making changes to the JSON config file stored in a GitHub repository.
- A CI/CD pipeline will be put in place so changes in the source code stored in GitHub will automatically update the copy of the files running in the DWRi production instance as a Google Cloud Function or equivalent.

### 6.2 DWRi DataLoggers and Other CSV Files


DWRi retrieves data from remote data connections via CSV files and also loads data from CSV files generated by the Campbell Scientific Loggernet software (Loggernet’s “.dat” files) that manages many of the measurement stations operated by DWRi.

In the Orchestrator, new data from data connections providing data via individual CSV files (posted via HTTP or FTP) will be retrieved as follows:
- Each CSV file will have a single data connection.
- Each CSV file from which data are to be retrieved will be scheduled as a single ETL task.
- Settings required to retrieve data from CSV files (including the URL retrieving the file and information about the column header row, data start row, delimiter, quote character, timestamp column, timestamp format, and timestamp offset) will be specified at the data connection level.
- Settings required at the ETL task level include the task schedule and a mapping of data columns in the CSV file to destination datastreams in HydroServer.
- Scheduled ETL tasks can run in parallel because each CSV file is independent.

New data from stations providing data through DWRi’s Loggernet instance will be retrieved as follows:
- DWRi’s daily datalogger files will be treated as a data connection and DWRi’s hourly datalogger files will be treated as a separate data connection.
- Each CSV file from which data are to be retrieved will be scheduled as a single ETL task.
- Settings required to retrieve data from CSV files (including a URL template for retrieving a file and information about the column header row, data start row, delimiter, quote character, timestamp column, timestamp format, and timestamp offset) will be specified at the data connection level.
- Settings required at the ETL task level include runtime variables required to complete the URL template, the task schedule, and a mapping of data columns in the CSV file to destination datastreams in HydroServer.
- Scheduled ETL tasks can run in parallel because each CSV file is independent.

### 6.3 Metridyne and Exactrac APIs


DWRi retrieves data from several API instances provided by Metridyne and Exactrac using a series of scripts. Data are returned from these APIs in XML or JSON format. DWRi’s scripts for retrieving data from the Metridyne APIs include the URL for the API as a script-level setting. Each script extracts information about which stations to retrieve data for by first querying DWRi’s DIVRT database. Each script then loops through its stations, retrieves new measurements for each station from the API, and writes that new measurement data to the DIVRT database.

In the Orchestrator, new data from stations retrieved from Metridyne and Exactrac APIs will be retrieved as follows:
- Each instance of the Metridyne/Exactract API requiring a different auth code to retrieve data will be treated as a data connection (these are already separated into separate collection systems and we will keep the same organization).
- The data connections can each have their own workspace or could be grouped into workspace(s) according to DWRi’s convenience for access control.
- Settings for the data connection will include a template URL for retrieving a JSON payload from the API, the required auth code, and XML path or JSON query information for retrieving data values from the XML or JSON payload.
- Settings for each ETL task scheduled to use a Metridyne or Exactrack data connection will include the parameters that must be injected into the template URL to retrieve the JSON payload containing data for the destination datastream from the API, a schedule for the task, and a mapping of the payload retrieved to a destination datastream in HydroServer.
- A set of ETL tasks will be created for each data connection to retrieve the required datastreams (likely one task per datastream).
- The ETL tasks can run in parallel because each XML or JSON payload is assumed to be independent and the APIs should be able to handle simultaneous requests.

### 6.4 Calculating Time Aggregated Data


DWRi routinely calculates daily average values for flow or end of interval values for storage from sub-daily data values recorded by monitoring stations. These aggregation calculations are currently embedded within DWRi’s data scraping scripts. In order to provide more granular control and to provide additional logging and feedback, the Orchestrator will treat temporal aggregation as a separate scheduled ETL task as follows:
- A sub-daily source datastream in HydroServer will define the data values to be aggregated. Aggregated data values will be written to a daily destination datastream in HydroServer.
- Sub-daily data for the source datastream must be loaded to HydroServer prior to temporal aggregation.
- Temporal aggregation will:
- Extract sub-daily data for source datastreams from HydroServer’s API.
- Transform the sub-daily data to a daily time step according to the specified aggregation statistic to be calculated and using DWRi’s existing code logic for calculating daily values.
- Load the data back into HydroServer to a destination datastream that has a daily time aggregation interval.
- Within a workspace, a single HydroServer data connection will be defined for retrieving data from HydroServer.
- One or more ETL tasks (depending on the desired level of granularity) will be created and run to perform data aggregation for all source and destination datastreams within that workspace.
- HydroServer’s API will be the data connection.
- ETL task will include a list of source datastream IDs that need to be aggregated along with a corresponding list of destination datastream IDs to which time aggregated values will be written.
- The script can execute temporal aggregation for datastreams in parallel because each one is independent.
- An aggregation statistic (mean, end of interval value) will be defined for each destination datastream. The aggregation statistic defines the output data values that will be calculated for each time aggregation interval.
- A number of prior intervals (days) will be defined for each destination datastream defining the number of aggregation intervals in the past for which to retrieve sub-daily data from HydroServer to include in the aggregation. Newly aggregated data will replace existing data for prior interval days per DWRi’s current operating procedure.

### 6.5 Calculating Data for “Virtual” Stations


DWRi’s data scraping scripts contain several instances where data values are calculated for “virtual” stations - e.g., stations for which one or more datastreams is defined as the sum of data values from multiple other stations. These stations are considered “virtual” because they are not a real physical measurement station, but are rather defined by some arithmetic calculation based on the data from two or more other stations. Within DWRi’s existing data scraping scripts, data values are retrieved for the source stations, aggregated to daily values, written to DWRi’s DIVRT database, and then retrieved and used at the end of the script to calculate data values for virtual stations. Similar to the approach above for calculating time aggregated data and to provide granular control and detailed logging and feedback, the Orchestrator will treat calculation of virtual stations as a separate scheduled ETL task as follows:
- Multiple source datastreams in HydroServer will define the data values to be used in calculating the destination virtual datastream. Resulting calculated data values will be written to a single destination datastream in HydroServer.
- The data for the source datastreams must be added to HydroServer prior to virtual station calculation - i.e., virtual datastream calculation must follow data scraping and aggregation.
- Calculation of a virtual datastream will:
- Extract data for required source datastreams from HydroServer’s API.
- Check to make sure data values exist for each source datastream to be combined for each time step. Only time steps with data for all input datastreams will be calculated (otherwise “no data” values will be inserted).
- Transform the data by applying the arithmetic operation (e.g., summing the values for the source datastreams).
- Load the calculated values into HydroServer to a destination “virtual” datastream.
- Within a workspace, a HydroServer data connection will be defined for retrieving data from HydroServer
- One or more scheduled ETL tasks will be defined (depending on desired granularity) to perform virtual data calculations.
- HydroServer’s API will be the data connection for all source datastreams.
- The ETL task will have one or more “virtual” destination datastreams that are to be calculated by the scheduled ETL task.
- Each “virtual” destination datastream will have a list of source datastreams that will be used in the calculations.
- The ETL Task can execute virtual data calculations in parallel because each destination datastream is independent.
- Each “virtual” destination datastream will have an equation/expression that defines how source datastreams will be combined to calculate the destination datastream.
- It is assumed that all source datastreams have the same time aggregation interval and timestamps and that a destination datastream will inherit these from its source datastreams.
- Per DWRi’s existing scripts, calculations will be performed for the prior 28 days, and calculated values will replace any data values already in the database.

### 6.6 Datastreams that Require Units Conversions


Some source flow data loaded by DWRi are supplied using units other than cubic feet per second. DWRi wants all data entered into their database to use units of cubic feet per second for flow, which requires units conversion prior to loading data. As a general solution to this problem, the Orchestrator will enable users to specify options on a destination datastream to indicate:
- That an adjustment/transformation to input data is required prior to loading data - this could be a checkbox.
- An expression to be applied to all of the data values for the the source data prior to being loaded into the destination datastream (e.g., "(x - 32) * (5.0/9.0))"

NOTE: Allowing a generic expression will enable units conversion, but would also allow adding or subtracting constant offsets, specifying a constant multiplier, etc.

### 6.7 Datastreams that Require Lookup Tables


Some source data loaded by DWRi require conversion from a native measurement like “voltage” or “elevation” to the actual desired value of “discharge” or “storage”. This is accomplished using predefined lookup tables that contain rating curves that are specific to a site/observed property. These lookup tables are currently stored in a table within DWRi’s DIVRT database. The Orchestrator will handle calculation of derived datastreams (datastreams calculated from logged data using a lookup table) as part of the ETL task that loads data to a destination datastream:
- The user will have the option of saving both the raw source data and the data converted/transformed using the lookup table in separate datastreams.
- If the user chooses to save both to HydroServer, they must supply a destination datastream ID for both the raw datastream and the converted datastream.
- Where a transformation requiring a lookup table is required for a destination datastream:
- The user must select an option that a transformation is required.
- The user must supply the path to a file containing the lookup table to be used. Lookup tables must be stored in a standardized format that can be easily read and in a location that is accessible to the HydroServer data management web app (e.g., an S3 storage bucket).
- The conversion/transformation of the source data will:
- Retrieve the raw data from the data connection.
- Retrieve the specified lookup table.
- Transform the raw source data to the destination quantity according to the rating curve stored in the lookup table.
- Load the transformed data into HydroServer to a destination datastream.
- Load the raw source data into HydroServer to a destination datastream if the user has selected this option.

NOTE: Lookup tables that now exist in DWRi’s DIVRT database will have to be exported to files that can be managed and accessed in shared storage (e.g., an S3 bucket). This shared storage may need to be accessed by multiple software applications (e.g., HydroServer, DWRi’s software that enables editing of lookup tables).

### 6.8 Loading Data from One-Off, Non-Standard Data Formats


There are a few non-standard and quirky data formats used by data suppliers. These include data formats where there are multiple headers/tables within a single file and other non-standard syntaxes that are difficult to code around. Rather than designing user interfaces around these individual data connections, USU will instead just port the existing scripts for these to Python scripts to be run as Google Cloud Functions. Scripts will be stored and managed in GitHub. These scripts will not be configurable in HydroServer, and there will not be a user interface for them. Only users who have access to the Google Cloud Functions will be able to view, manage, and debug these scripts.
