# Loading Data

## Streaming Data Loader Application

`The Streaming Data Loader Desktop App` (SDL App) is a tool used to automatically load data into HydroServer from local time series data files (such as CSV datalogger output files for example). A file containing data to be loaded to HydroServer is called a [`Data Source.`](terminology.md#2-linked-metadata) The app is composed of a `user interface` for signing in with your HydroServer credentials and logging information back to the user, and a `scheduler` which will routinely check if there's any new data in your data files and push updates to HydroServer via the [`Data Management API.`](../api/data-management-api.md)

You can download the SDL app from [this page.](http://ciroh-his-dev.us-east-1.elasticbeanstalk.com/hydroloader/download)

::: info
If you're looking for more control over your data loading than the Streaming Data Loader provides, you can download just the Python scheduler from our [`GitHub repository`](https://github.com/hydroserver2/hydroloader) and implement your own custom solution. Or for even more control, you can directly use the the `Data Management API`. This can be nice for cases where you have hundreds or thousands of datastreams that you'd like to define programmatically rather than manually.
:::

## Setup a Data Loader

When you install the SDL App, it will ask for the same account credentials you specified when creating your HydroServer account and a name for the computer running the SDL instance. A computer running the SDL application is called a [`Data Loader.`](terminology.md#2-linked-metadata) You'll link your `Data Loaders` to your `Datastreams` by the name you specify so it's recommended you give a unique, descriptive name to each instance so you can easily identify them.

After providing the `Data Loader` name and your credentials, the remaining data loading configuration will be done through the HydroServer website. You can verify the Data Loader was successfully connected to your HydroServer account by navigating to the [`Manage Data Loaders`](https://playground.hydroserver.org/data-loaders) page where you'll see it listed on in the table. If you ever uninstall an SDL instance, you can also delete the record of that Data Loader from this dashboard.

If you need detailed logs from the SDL app, you can access them by clicking on the app icon in your computer's system tray and selecting `View Log Output`.

## Define a Data Source for your Data loader

From the [`Manage Data Sources`](http://playground.hydroserver.org/data-sources) page of the HydroServer website, a user can define the expected structure of their `Data Source`, which will include information like which computer(Data Loader) to find the Data Source CSV file on, the local file path to that CSV, which column contains the timestamps, which row contains the headers, which row marks the start of data points, etc.

::: tip **Made by programmers for non-programmers**
HydroServer uses 1-based indexing for Data Sources and Loaders. So, if your headers are found on the first row of your CSV file, the header row index would be `1`. If the column holding your timestamps is the second column in the file, the column index would be `2`.
:::

### Link your Data Loader and Data Source to a Datastream

Below is an example of what a `StreamFlowData.csv` file might look like. This CSV file represents a typical `Data Source` used by a `Data Loader` to push data into HydroServer.

```txt
DateTime,FlowRate,Temperature
2024-01-01T08:00Z,120,15.5
2024-01-01T08:15Z,125,15.7
2024-01-01T08:30Z,123,15.6
2024-01-01T08:45Z,122,15.8
```

After a Data Source is created, the user can link it to multiple datastreams (one datastream per column). In the case of `StreamFlowData.csv`, we'd want to link one datastream to column 2 (FlowRate) and different datastream to column 3 (Temperature).

Navigate to the `Site Details` page of the site containing the datastream you'd like to upload data to. On the `Datastreams Table`, Click the `actions` button for the desired datastream and select the `Link Data Source` button. There you'll select your Data Loader's name from the drop down and specify the column number of your `Data Source` for the data you'd like to be uploaded (index 1 for Datastream1 and index 2 for Datastream2). Alternatively, you can input the name of the column header for the desired data (FlowRate and Temperature).

Click save for each and you're all set up! Your data loader will now upload data to HydroServer on a regular basis.

## Managing Data Sources

You can monitor the status of all your data sources from the [`Data Sources Dashboard`](http://hydroserver-dev.ciroh.org/data-sources). Your Data Loaders will push status updates to HydroServer whenever they try to load data to HydroServer.

You can pause a Data Loader from uploading new data and resume on-demand from the `pause` and `play` icons on the `Manage Data Sources Table`. This table is also where you can edit/delete a Data Source or view their details.
