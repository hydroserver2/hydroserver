# HydroServer Streaming Data Loader

_Functional Specifications_

## 1 Introduction


The HydroServer Streaming Data Loader (SDL) is a client software application for automating the upload of observational data from comma separated values (CSV) data files to the HydroServer Operational Observations Data Store (database). It retrieves configuration information from the HydroServer Data Management application programming interface (API) and loads data into the HydroServer database via the HydroServer SensorThings API. Its primary purpose is to automate loading of data into a HydroServer instance for streaming sensor data stored in comma separated values (CSV) files such as those produced by Campbell Scientific’s Loggernet software.

## 2 Requirements


The following are requirements that must be met by the SDL:

- It must load data into the HydroServer database using HTTP POST requests through the HydroServer SensorThings API.
- It must run on machines running the latest versions of Windows, MacOS, and Debian-based Linux operating systems.
- It will provide a graphical user interface (GUI) that enables a user to connect to a HydroServer instance into which data will be loaded.
- Configuration of which files to load data from and which data will be loaded into the HydroServer database will be done via the HydroServer Data Management web application.
- The SDL must be capable of loading data from any CSV file that is:
- Stored locally on the machine on which the SDL is installed
- Available via a shared folder available on the same network as the machine on which the SDL is installed.
- Any file available to the SDL via HTTP or FTP protocols.
- The SDL must include a data loading component that is separate from the GUI and that can be executed without any user interaction - e.g., as a scheduled job that runs without user intervention.
- Data loading job(s) must be capable of being scheduled to run on a user-defined schedule. Setting the schedule on which jobs will run will be done via the HydroServer Data Management web application.

## 3 Supported Functionality


The following describe specific functionality that will be provided by the SDL:

- The SDL GUI will enable a user to log into an instance of HydroServer to connect the SDL to that instance.
- The GUI available in the HydroServer Data Management web application will enable managing data loading at a CSV file level. Each CSV file will be considered a “data source” that may contain data for multiple “Datastreams.”
- Within the HydroServer Data Management web application, users will create a new data source by specifying the following:
- A name for the data source.
- The SDL instance that will load data from the data source.
- The path to a CSV file containing data they want to load.
- The file delimiter (comma as default).
- The row on which the column headers appear for the CSV file.
- The row on which data begin in the CSV file.
- A schedule for loading data from the CSV file (begin time, end time, interval - or Crontab).
- The column containing the date/time values.
- An format for the timestamp.
- The UTC Offset for the date/time values.
- To map individual columns in the data source file, users will do the following in the HydroServer Data Management web application:
- They will select the site at which data were collected.
- They will select a Datastream from that site.
- They will select a data source in which the data for the selected Datastream resides.
- They will select the column in the data source (by name or by index) that contains data for the selected Datastream.
- They will designate a numeric “NoData” value for the Datastream (e.g., -9999). This value will be inserted wherever the SDL finds invalid numeric values in the data file column (e.g., a value of “NaN” or “NAN” in the data file will be replaced by the designated NoData value).
- They will repeat the preceding steps until all of the columns of data in the data source CSV file that they want to load have been mapped to a Datastream.
- These steps assume that Site and Datastream metadata have been created first through the HydroServer data management web application or using the HydroServer data management API.
- These steps assume that Sensor, ObservedProperty, ProcessingLevel, Units, and ResultQualifier metadata is created through a separate process in the HydroServer Data Management web application or data management API so they can be used in the metadata for Sites/Datastreams.
- The SDL will store all of the data source CSV mappings to Datastreams (all metadata mapping and configuration settings from Step 2) in tables within the HydroServer database.
- Mapping information stored in the HydroServer database will be used for formulating functions in the HydroServer data management API that can be used by the SDL software to retrieve the necessary configuration settings telling it which data to load and on what schedule.
- The SDL software will POST data to the HydroServer database through the SensorThings API using the hydroserverpy Python client package.
- The SDL software will include a “silent updater” that runs unattended to load data. It will do the following:
- Get configuration information from the HydroServer database through HydroServer’s data management API.
- For each mapped data source, determine from the configuration whether it needs to run for that file at the current time. If yes:
- Check database for the last date/time for which data were loaded.
- Open the CSV file.
- Get any new data since the last time at which data were loaded.
- Load new data into the database.
- Write log information to an output log file for diagnostic purposes.
- The SDL software will write descriptive log data to a file accessible through the SDL software GUI with log data describing successful operations and errors useful for diagnosing how to fix broken jobs.

## 4 Supported CSV File Format


The SDL will support loading data from any ASCII text CSV file that meets the following specifications:

- Contains a single consistent delimiter (e.g., comma, tab, pipe, etc.).
- Contains a single row with a unique name/label for each column. There may be additional header rows in the file that can be skipped.
- Contains a single column with date/time values. Preferred format for Date/Time values is ISO 8601 date/time values (e.g., “YYYY-MM-DD hh:mm:ss” or “2022-12-14T00:55:57+00:00” - where ISO 8601 allows the “T” to be omitted). There may be some variants of this format that a user should be able to specify a format for.
- Contains any number of data columns with numeric values, with each column representing data values for a particular Datastream.
- Not all columns in the file have to be loaded - only those selected by the user and mapped to an existing Datastream in HydroServer.

## 5 Technical Implementation and Development Notes


The SDL software will consist of the following major components:

- hydroserverpy Python package: This will be a Python package installable via PyPi that will handle the core tasks that the SDL software application will perform. These include:
- Retrieve configuration information for the SDL instance from the HydroServer data management API.
- Using configuration information, parse data files and bundle data into SensorThings POST requests for streaming.
- Streaming Scheduler: This will be a background process that runs when the desktop app is installed and will handle running the streaming jobs based on the configuration set up by the user.
- Command Line Interface: This will allow users to use the SDL on the command line. Users should be able to configure SDL settings, generate YAML configuration files, and view the status of streaming jobs.
- Graphical User Interface: This will be how most users interact with the SDL and should include all of the functionality listed above. Possible GUI frameworks include tkinter, qt, electron, and flutter.

Screen shots from the HydroServer Legacy Streaming Data Loader

## 1 Main GUI window for the SDL.


Main interface of the GUI tool. Each line in the table represents a datalogger file that has been configured. Buttons at the top allow the user to add a new file, edit an existing file, remove a file, run a selected file on demand, and refresh the view (reload from config file). The file menu only has one option to exit the application.

## 2 Add new file form


Form that shows when the user clicks the button to add a new file mapping. The form allows the user to specify a file on the local disk or a web accessible file available via http/ftp/etc. Settings include:
- Delimiter for the file
- Schedule for running this file. This is independent of the schedule on which the SDL is scheduled to run. The SDL checks to see if the run period has passed and, if so, runs this file.
- Database connection - the ODM database into which the data in the file will be loaded
- Row number on which the column headers are located
- Row number on which the data begin
- There is an option to include data previous to data values that are already in the database. This is an attempt to fill holes/gaps in the data if those gaps have data in the data file.

## 3 Map data series form


On this form, the user specifies which column contains the time stamp (bottom left). The user can either specify the Local Date/Time and a UTC Offset, or that the data file contains timestamps that use UTC Date/Time. There is an option to select whether the data file contains daylight saving time shifts (DST) if local date/time values are used. Mapped columns are shown in the table at the bottom. The preview of the structure of the file is shown in the table at the top. The user can map only a subset of the columns - not all columns have to be mapped.

## 4 Add/Edit data series form


The user selects a column name from the drop down list. Then they choose options for how to handle the time interval. I suggest that we do not use these time interval adjustment options for now. I don’t remember why we added them, and I don’t think we use them at all.

Example SensorThings POST request:

[
  {
    "Datastream": {
      "@iot.id": "2cc58343-27a8-4a77-9fbd-22d414f7c358"
    },
    "components": ["resultTime", "result"],
    "dataArray": [
      ["2023-01-01 01:00:00+0000", 14],
      ["2023-01-01 02:00:00+0000", 13],
      ["2023-01-01 03:00:00+0000", 15],
      ["2023-01-01 04:00:00+0000", 17]
    ]
  },
  {
    "Datastream": {
      "@iot.id": "62264006-cb7f-4b40-ac4a-169ebc217551"
    },
    "components": ["resultTime", "result"],
    "dataArray": [
      ["2023-01-01 01:00:00+0000", 32],
      ["2023-01-01 02:00:00+0000", 30],
      ["2023-01-01 03:00:00+0000", 41],
      ["2023-01-01 04:00:00+0000", 37]
    ]
  },
]

Example with single data point:

[
  {
    "Datastream": {
      "@iot.id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    },
    "components": ["resultTime", "result"],
    "dataArray": [
      ["2023-04-20 08:22:54", 23.81]
    ]
  }
]

Minified/compact JSON also works:

[{"Datastream":{"@iot.id":"c9953e59-ccac-4950-9dc6-4e959de70562"},"components":["resultTime","result"],"dataArray":[["2023-04-21 11:53:55",29.20952]]}]

Example YAML configuration file:

name: LoganRiverObservatory1
crontab: 0 12 * * *
directory: /data/
file: *.csv
timestamp:
  column: 1
  format: %Y-%m-%d %H:%M:%S
observations:
  - datastream: '2cc58343-27a8-4a77-9fbd-22d414f7c358'
    column: 2
  - datastream: '62264006-cb7f-4b40-ac4a-169ebc217551'
    column: 3
