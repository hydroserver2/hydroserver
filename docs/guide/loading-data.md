# Loading Data

## Streaming Data Loader Application

The Streaming Data Loader desktop app is a tool used to automatically load data into
HydroServer from local data files (such as datalogger output files for example). You can download
the SDL app from [this page](http://ciroh-his-dev.us-east-1.elasticbeanstalk.com/hydroloader/download).

When you install the SDL app, it will ask for your account credentials and a name for the SDL
instance. You can install multiple SDL apps across different machines, so it's recommended you
give a unique, descriptive name to each instance so you can easily identify them. Be aware that
the credentials you provide will be used to upload your data, so you must be listed as an owner
on any datastreams you want to use the SDL to load data into.

After providing the instance name and your credentials, the remaining data loading configuration
will be done through the HydroServer website. If you need detailed logs from this instance of the
SDL, you can access them by clicking on the app icon in the system tray and selecting
"View Log Output".

You can view all Streaming Data Loader instances you've set up on HydroServer through the [Data
Loaders Dashboard](http://beta.hydroserver2.org/data-loaders). If you ever uninstall an SDL instance,
you can also delete the record of that SDL from this dashboard.

## Data Sources

After installing the Streaming Data Loader, you can configure data sources on HydroServer for
the SDL to load data from. A data source is a CSV file that the HDL app can read and contains
raw timeseries data for one or more datastreams.

Data sources can be set up from the [Data Sources Dashboard](http://hydroserver-dev.ciroh.org/data-sources).
When you set up a data source, the associated SDL app will automatically register and schedule data
loading tasks for that data source. Multiple datastreams can be linked to a data source
from the setup form on the Data Sources Dashboard, or one at a time from the [Sites](http://hydroserver-dev.ciroh.org/sites)
page by selecting a site, then clicking "Link Data Source" for a data stream at that site.

You can also monitor the status of all your data sources from the Data Sources Dashboard. The SDL app
will push status updates to HydroServer whenever it tries to load data in addition to storing logs
locally.
