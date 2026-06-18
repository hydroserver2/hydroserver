# How to Use the HydroServer Streaming Data Loader

This guide explains how to use the **HydroServer Streaming Data Loader** to upload data from a comma separated values (CSV) file into HydroServer.  

Many dataloggers and proprietary sensor/datalogger communication software programs download data to CSV files. The Streaming Data Loader is a desktop software application that helps you load time-series data, such as discharge, streamflow, temperature, or other sensor data, from a CSV file on your computer into a HydroServer datastream.  

Before using the Streaming Data Loader, make sure you already have:

- A HydroServer workspace set up in a HydroServer instance. You can do this via the HydroServer Data Management App.
- A monitoring site created in HydroServer
- One or more datastreams created in HydroServer for the data you want to upload from a CSV file

---

## 1. Download and Install the Streaming Data Loader

Go to the Streaming Data Loader release page: [https://github.com/hydroserver2/streaming-data-loader/releases](https://github.com/hydroserver2/streaming-data-loader/releases)

<img src="/sdl/Figure1.png" alt="Download page" class="img-white-bg" width="750">

Download the correct installer marked as "Latest" for your operating system:
- Windows
- macOS
- Linux

After downloading the file, follow the install instructions at the following link to
[Install the Streaming Data Loader](/references/streaming-data-loader.md).

---
## 2. If You Get a Warning

On Windows, you may see a warning message that says:

> Windows protected your PC

<img src="/sdl/Figure2.1.png" alt="Windows Protection" class="img-white-bg" width="550">

If this happens:

1. Click **More info**.
2. Click **Run anyway**.

<img src="/sdl/Figure2.2.png" alt="Windows Protection Run Anyway" class="img-white-bg" width="550">

3. Continue installing the application.

After installation, you can right-click the app and choose **Pin to Taskbar** if you want to open it more easily later.

On Mac, you may get a warning when you try to run the app that says:

> Streaming Data Loader.app Not Opened. Apple could not verify "Streaming Data Loader.app" is free of malware that may harm your mac or compromise your privacy.

If this happens, you will need to do the following:

1. Open System Settings
2. Click Privacy & Security
3. Scroll down and click the "Open Anyway" button next to the message that says the Steaming Data Loader application was blocked. 
4. On the window that pops up, click the "Open Anyway" button.

---
## 3. Install the Background Process

After the Streaming Data Loader is installed, open the application. The app may ask you to install a background service.

Click:
**Install Background Service**

<img src="/sdl/Figure2.3.png" alt="Install Background Service" class="img-white-bg" width="750">

The background process allows the Streaming Data Loader to keep checking your CSV file and automatically upload new data rows when they are added to the CSV file. The Streaming Data Loader doesn't run on a schedule. It continuously monitors whatever CSV files you set up, and any time there are changes to those files, it parses the file, looks for new data to load, and uploads it to HydroServer.

---

## 4. Connect the App to HydroServer

Before uploading data, you need to connect the Streaming Data Loader to HydroServer.

You can connect by using either:

- Your HydroServer username and password
- An API key

<img src="/sdl/Figure2.4.png" alt="Connect to HydroServer" class="img-white-bg" width="750">

Using an **API key** is recommended because it gives the app only the permissions it needs to upload data.

You will need:
- The HydroServer website address
- An API key created for your workspace in the Data Managment App

Example HydroServer address:

```text
https://playground.hydroserver.org
```

Paste the website address into the **Host URL** box. Then paste your API key into the **API Key** box. Click: **Connect to HydroServer**

---

## 5. Create an API Key in HydroServer

An API key works like a secure password that allows the Streaming Data Loader to upload data to your HydroServer workspace. It can limit access to loading data only, whereas your username and password could be used to edit many other things. This is why we recommend using an API key with the Streaming Data Loader.

To create an API key for the Streaming Data Loader:
1. Open the HydroServer Data Managment App website.
2. Go to **Your sites**.
3. Click **Manage workspaces**.
4. Find your workspace in the table.
5. Click the lock icon.

<img src="/sdl/API1.png" alt="Workspace Access Control" class="img-white-bg" width="750">

6. Click **API keys**.
7. Click **Create API key**.
8. Give the API key a name (something like 'Streaming Data Loader').
9. Add a short description (something like 'API Key for Streaming Data Loader').
10. Select the role as **Data Loader**.

<img src="/sdl/API2.png" alt="Create API Key" class="img-white-bg" width="750">

11. Click **Save**.
12. Copy the API key.

**IMPORTANT:** Save the API key somewhere safe. After you close the window, HydroServer will not show the value for the API key again. If you lose the API key, you can create a new one.

---

## 6. Prepare the CSV File to Be Loaded

Before selecting the CSV file, make sure the file is saved in a location on your computer that the Streaming Data Loader can access. A good folder location is important because the Streaming Data Loader may run as a background service.

Examples of good places to store the CSV files to be loaded include:

### Windows

```text
C:\sdl\data\
```

or

```text
C:\ProgramData\sdl\data\
```

### macOS

```text
/Users/Shared/sdl/data
```

### Linux

```text
/var/sdl/data
```
<div style="
  background-color: #fff3f3;
  border-left: 6px solid #ff4d4d;
  padding: 14px 18px;
  margin: 20px 0;
  border-radius: 6px;
  color: #000000;
  width: fit-content;
  max-width: 600px;
">

<h3 style="color: #000000; margin-top: 0;">⚠️ Avoid These File Locations</h3>

<p style="color: #000000;">
Do <strong>NOT</strong> save your CSV files in:
</p>
<ul style="color: #000000;">
  <li>Desktop</li>
  <li>Downloads</li>
  <li>Documents</li>
  <li>Temporary folders</li>
  <li>Program Files</li>
  <li>Cloud folders such as OneDrive, Dropbox, or Google Drive</li>
</ul>

<p style="color: #000000; margin-bottom: 0;">
These locations may cause <strong>permission issues</strong> or make it harder for the Streaming Data Loader to detect file updates correctly.
</p>

</div>

---

## 7. Choose the CSV File

In the Streaming Data Loader, click: **Choose CSV File**

<img src="/sdl/Figure2.png" alt="Choose CSV File" class="img-white-bg" width="750">
Then select the CSV file you want to configure from your computer. A typical CSV file may look like this:

```csv
timestamp,max_temp_c,min_temp_c
2025-03-23T00:00:00Z,11.7,-1.5
2025-03-24T00:00:00Z,8.4,-2.0
2025-03-25T00:00:00Z,10.9,-2.2
```

Your CSV file should usually include:

- A singel column containing the timestamp for each reo
- One or more data value columns representing datastreams to be loaded

For example, if you are uploading discharge data, your CSV file should include a timestamp column and a discharge value column.

---

## 8. Set Up the CSV File

After selecting the CSV file, the app will show a setup page. This page tells the Streaming Data Loader how to read your CSV file. Check each of the following settings carefully.

<img src="/sdl/Figure3.png" alt="Configure CSV File" class="img-white-bg" width="750">

### Delimiter

The delimiter is the symbol that separates the columns in the file.

For most CSV files, choose:
```text
Comma (,)
```
Other possible options include: Semicolon, Tab, Pipe or Space, but this depends on your file.

### Column Identifiers

If your CSV file has column names, choose: **Header names**. This indicates that there is a row in your CSV file that contains the column headers and allows the app to use the names in that row to identify the columns in the table.

### Header Row Number

The header row number is the row where the column names start. Move/Drag the **HEADER** marker to the row where the column names are located. Or, you can set the header row number in the settings on the left.

### Data Start Row

The data start row is the first row where the actual data begins. Move/Drag the **DATA START** marker to the first row of real data. Or, you can set the number of the row on which the data starts on the left.

### Timestamp Column Name

Choose the name of the column that contains the date and time values for your data. The SDL assumes that your datetime values are in a single column. You can use different formats for the timestamps, but they must be in a single column in the file.

### Timestamp Format

Choose the timestamp format that matches the timestamps in your CSV file. If the timestamp format is different, choose the closest option or use a custom format. On you can define a custom format that matches your timestamp values.

<img src="/sdl/Figure4.png" alt="CSV Settings" class="img-white-bg" width="750">

### Timezone

HydroServer stores all data values within its database using UTC datatime. If you do not specify a timezone associated with your data, HydroServer will assume that the values you are providing are UTC datetime values. In the Timestamp format you can choose the following options:

* **Timezone naive (YYYY-MM-DD hh:mm:ss):** You should use this option if your timestamps are UTC but do not encode the UTC offset information in the timestamp OR if your timestamps are recorded in some other time zone that is not encoded in the timestamp values. In both cases, you would select the correct timezone corresponding to your timestamp values.
* **Full ISO 8601 (YYYY-MM-DD hh:mm:ss.ssss+hh:mm):** You should use this option if your timestamp vaues include the UTC offset information within the timestamp values (e.g., "+hh:mm")
* **Custom Format:** You should use this option if your timestamp values do not conform to the ISO 8601 standard format. You will need to specify the specific format of your timestamp values so they can be parsed, and you also need to specify the time zone associated with your timestamps.

**NOTE:** When using the Timezone naive option, you will also have to specify whether your timestamps have a fixed offeset (e.g., your datalogger was programmed to always record timestamps using Mountain Standard Time) or or whether they are daylight savings time aware and switch with daylight savings time.

When everything looks correct in the setup for your file, click:
**Validate and Continue**

---

## 9. Match CSV Columns to HydroServer Datastreams

After the CSV file is validated, the app will show a mapping page. This step connects the columns in your CSV file to the correct HydroServer datastreams into which those columns will be loaded.

<img src="/sdl/Figure5.png" alt="CSV Column Mapping" class="img-white-bg" width="750">

You need to select:
1. The CSV column that contains the data values you want to load
2. The correct HydroServer datastream into which you want to load data

**IMPORTANT NOTE:** You must set up the metadata for the datastream in the HydroServer Data Management App or using HydroServer's API before you can load data into it. To help you isolate the correct datastream when there are many available monitoring sites, you can use the Site and Datastream filters at the top of the form to narrow the list of datastreams for selection.

<img src="/sdl/Figure6.png" alt="Column Mapping Example" class="img-white-bg" width="750">

Example:
- CSV column: `max_temp_c`
- Site: `Logan River at the Utah Water Research Laboratory`
- Datastream: `Temperature`

If you are uploading discharge data, the setup may look like this:

- CSV column: `Discharge`
- Site: `Logan River at the Utah Water Research Laboratory`
- Datastream: `Discharge`

Make sure the selected CSV column matches the correct datastream. For example, do not connect temperature data to a discharge datastream.

**NOTE:** You can create as many mappings as you need within your data file. You can load data for one or many columns.

---

## 10. Create the Data Source

After selecting the correct CSV column, site, and datastream nmapping(s), click: **Create**

This creates the data source and starts the upload process. After this, the Streaming Data Loader will begin sending the CSV data to HydroServer.

**NOTE:** If you need to modify the file location, CSV Setup, or column/datastream mappings, you can click on the buttons for those items under the name of the data source to edit the settings.

---

## 11. Check the Upload Status

After clicking **Create**, the app will take you to the dashboard. The dashboard shows the data sources you have created.
If the status says:
```text
Running
```

the data is still being uploaded.

<img src="/sdl/Figure7.png" alt="Check Upload Status" class="img-white-bg" width="750">

You can click: **View Logs** to check whether the upload is working correctly. If something is wrong, the logs usually show a message explaining what needs to be fixed.

---

## 12. Check the Data in HydroServer

While the Streaming Data Loader is uploading the data, open the HydroServer Data Management App in your web browser. Go to the site details page for your monitoring site and refresh the page. If the upload is working, the number of observations in the datastream should **increase**. This means the data is being loaded successfully.

<img src="/sdl/Figure8.png" alt="Loading Data" class="img-white-bg" width="750">
<img src="/sdl/Figure9.png" alt="Loading Data New Observations" class="img-white-bg" width="750">

---

## 13. When the Upload Is Finished

When the upload is complete, the Streaming Data Loader will show:

```text
UP TO DATE
```
<img src="/sdl/Figure10.png" alt="Finished Loading Status" class="img-white-bg" width="750">

This means the CSV file has been uploaded to HydroServer. If new rows are added to the CSV file later, the Streaming Data Loader can detect them and upload the new data automatically. If you want to force running of a data source, you can click the "Run Now" button.

---

## 14. Visualize the Data in HydroServer

After the data is uploaded, you can view it in HydroServer.

To visualize the data:

1. Open the HydroServer Data Management App website.
2. Go to the Visualize Data page.
3. Use the workspace filter to find your workspace.
4. If needed, use the sites filter to narrow the list of datastreams to the site you are interested in
5. Select your datastream from the datastream table.
6. View the uploaded data as a time-series plot.

<img src="/sdl/Figure 11.png" alt="Visualize Data" class="img-white-bg" width="750">

You should now be able to see your uploaded data in the HydroServer Data Management App.

---

## 15. Change the API Key

If you need to upload the data in a different workspace:

1. Open the Streaming Data Loader.
2. Click the account icon in the top right corner.
3. Click the "Change API key" option.
4. Enter the new API key.
5. Reconnect to HydroServer.

<img src="/sdl/Figure12.png" alt="Account Settings" class="img-white-bg" width="750">

---

## 16. Disconnecting from HydroServer

If you want to disconnect the Streaming Data Loader from HydroServer, do the following:

1. Open the Streaming Data Loader
2. Click the account icon in the top right corner
3. Click the "Disconnect" option

---

## 17. Uninstalling the Background Service

If you are done with the Streaming Data Loader and no longer want the background service to run on your computer, do the following to uninstall it:

1. Open the Streaming Data Loader
2. Click the Settings icon in the top right corner
3. Select "Uninstall Background Service

If you want to use the Streaming Data Loader again on your conmputer, you will need to reinstall the background service.