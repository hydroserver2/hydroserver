# Exporting and Downloading Data

The Data Management Web App provides quick links to export observation values for datastreams in comma-separated values (CSV) format.

## Download from the Site Landing Page

On the landing page for a monitoring site, you can scroll the list of datastreams to find the one you want and then click on the Actions button (the three vertical dots) and select 'Download data'

<img src="/data-management-app/download-data.png" alt="Download data" class="img-white-bg">

Selecting this option will generate and download a CSV file with the observation values and metadata for the datastream.

## Download from the Visualize Data Page

On the 'Visualize data' page, you can select one or more datastreams in the table at the bottom of the page and then click the 'Download selected' button at the top of the table. HydroServer downloads a ZIP file (`datastreams.zip`) containing one CSV file per selected datastream. Or, you can click the **Details** button on a datastream's row to display its metadata and then click on the 'Download' button at the top right of that form.

## Download File Format

**NOTE**: HydroServer exports timestamps for data values in UTC. Users should localize the date/time values as needed for their analysis after downloading the data.

The CSV download file is named with the UUID of the datastream (`datastream_<UUID>.csv`). It is formatted with a descriptive header at the top of the file containing the datastream's metadata. Each header line is prefixed with '#' as a quote character.

<img src="/data-management-app/downloaded-data-header.png" alt="Downloaded data header" class="img-white-bg">

Observation values are exported as a simple CSV table with columns for the timestamp, numeric observation values, and any data qualifying comments:

<img src="/data-management-app/downloaded-data-table.png" alt="Downloaded data table" class="img-white-bg">

## Automated or Scripted Data Download

If you want to automate data retrieval or code data download, use HydroServer's Python client, hydroserverpy — see [retrieving observations](/user-guides/how-to/using-the-python-client.md#observation-methods) in the client reference — or call [HydroServer's APIs](/references/hydroserver-apis.md) directly from other programming languages.
