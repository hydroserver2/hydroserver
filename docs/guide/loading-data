# Loading Data

## Streaming Data Loader Application

The Streaming Data Loader desktop app is a tool that can be used to
automatically load data into HydroServer datastreams from local
CSV files. You can download the SDL app here.

When you install the SDL app, it will ask for your account credentials
and a name for the SDL instance. Since you can install multiple
SDL apps across multiple machines, it's recommended you give a unique
descriptive name to each instance so you can easily identify them
from HydroServer. Also be aware that the credentials you provide will be
used to upload your data, so you must be listed as an owner on any 
data streams you want to load data into.

After providing the instance name and your credentials, the
rest of the data loading configuration will done through the
HydroServer website. If you need detailed logs from this instance of the
SDL, you can access them by clicking on the app icon in the system tray
and selecting "HydroLoader Logs".

You can view all Streaming Data Loader apps you've set up on HydroServer
through the Data Loaders Dashboard under "Data Management". If you ever
uninstall a Streaming Data Loader, you can also delete the record of that
SDL from this dashboard.

## Data Sources

After installing the Streaming Data Loader, you can configure data
sources on HydroServer for the SDL to load data from. A data source
is a CSV file that the Streaming Data Loader can read and contains
raw timeseries data for one or more HydroServer data streams.

Data sources can be set up from the Data Sources Dashboard on HydroServer 
(located under Data Management). When you set up a data source, the 
associated Streaming Data Loader will automatically register and schedule 
data loading tasks for that source. Multiple data streams can be linked
to a data source from the setup form on the Data Sources Dashboard, or
one at a time from the Site Details page by clicking on a data stream
for the site and selecting "Link Data Source".

You can also monitor the status of all your data sources from the Data
Sources Dashboard. The SDL app will push status updates to HydroServer
whenever it tries to load data in addition to storing logs locally.

