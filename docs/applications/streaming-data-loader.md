# Streaming Data Loader

The `Streaming Data Loader` desktop app (SDL) is a tool used to automatically perform ETL (Extract, Transform, Load) tasks to transfer data into HydroServer from local time series data files (such as CSV datalogger output files for example). A file containing data to be loaded to HydroServer is called a [`Data Source.`](/guide/terminology.md#_2-linked-metadata) The app is composed of a user interface for signing in with your HydroServer credentials and logging information back to the user, and a `scheduler` which will routinely check if there's any new data in your data files and push updates to HydroServer via the [`Data Management API.`](../api/data-management-api.md)

You can download the SDL app from [this page.](https://github.com/hydroserver2/streaming-data-loader/releases)

::: info Python Client
If you're looking for more control over your data loading than the Streaming Data Loader provides, you can script custom data loading jobs using [`hydroserverpy`](https://github.com/hydroserver2/hydroserverpy). Or for even more control, you can directly use the the `Data Management API`. This can be useful for cases where you have hundreds or thousands of datastreams that you'd like to define programmatically rather than manually.
:::

## Setup a Data Loader

When you install the SDL App, it will ask for the same account credentials you specified when creating your HydroServer account, a name for the computer running the SDL instance, and a workspace containing the datastreams you want to load data into. An instance of the SDL application is a type of [`Orchestration System.`](/guide/terminology.md#_2-linked-metadata) You'll need to identify your SDL instance by this name in HydroServer so it's recommended you give a unique, descriptive name to each instance so you can easily identify them.

After providing the SDL name, workspace to use, and your credentials, the remaining ETL configuration will be done through the HydroServer website. You can verify the SDL was successfully connected to your HydroServer account by navigating to the [`Job Orchestration`](https://playground.hydroserver.org/orchestration) page where you'll see it listed on the table. If you ever uninstall an SDL instance, you can also delete the record of that Data Loader from this dashboard.

If you need detailed logs from the SDL app, you can access them by clicking on the app icon in your computer's system tray and selecting `View Log Output`.

## Define a Data Source for your Streaming Data loader

From the [`Job Orchestration`](http://playground.hydroserver.org/orchestration) page of the HydroServer website, a user can define the expected structure of their `Data Source`, which will include information like where to find the Data Source CSV file on, the local file path or link to that CSV file, which column contains the timestamps, which row contains the headers, which row marks the start of data points, etc. You must also map each CSV column you want to load data from to a HydroServer datastream.

::: tip **Made by programmers for non-programmers**
HydroServer uses 1-based indexing for Data Sources and Loaders. So, if your headers are found on the first row of your CSV file, the header row index would be `1`. If the column holding your timestamps is the second column in the file, the column index would be `2`.
:::

## Managing Data Sources

You can monitor the status of all your data sources from the [`Data Sources Dashboard`](http://hydroserver-dev.ciroh.org/orchestration). The Streaming Data Loader application will push status updates to HydroServer whenever it tries to load data to HydroServer.

You can pause a Streaming Data Loader from uploading new data and resume on-demand from the `pause` and `play` icons on the `Orchestration Systems`. This table is also where you can edit/delete a Data Source or view their details.
