# HydroServer Timescale Cloud Database

This guide provides step-by-step instructions for setting up a HydroServer database on the Timescale Cloud platform. Before proceeding, ensure you have created a [Timescale Cloud](https://www.timescale.com/) account and set up an instance of the [HydroServer API services app](https://github.com/hydroserver2/hydroserver-api-services) to execute the required management commands.

## Configuring Timescale Hypertable Partition Interval

HydroServer uses TimescaleDB to partition the observations table based on the phenomenonTime field. Before setting up TimescaleDB, consider the size and range of the observations data you plan to store. The default partition interval is seven days, but you may choose a longer interval such as 30 days or 365 days if you anticipate storing data spanning many years. You may also consider using a standard PostgreSQL database without TimescaleDB if the total volume of your observations data will not be large enough to benefit from partitioning.

Please note that although the partition interval in TimescaleDB is adjustable, the database cannot automatically rechunk existing partitions. If you need to modify the partition interval after loading observations data, a manual process is required. This involves creating a new observations hypertable with the updated interval, copying data from the old table to the new one, and subsequently dropping the old table to remove outdated chunks.

## Create a Timescale Cloud Database Instance

1. In the Timescale Cloud dashboard, click "Create Service" and follow the provided instructions to set up your Timescale Cloud database.
2. Once the service is created, download the service config file. Delay creating a hypertable; Django will manage table creation in the next step.

## Run Django Migrations and Timescale Setup Commands

Before running the commands below, ensure you have a local instance of the Django HydroServer backend app or access to a deployed instance. Connect to your new service using the environment variable or entry in your .env file:

- DATABASE_URL

The value should be a connection string linking to your TimescaleDB instance, utilizing the "Service URL" under "Connection info" on your Timescale Cloud Services dashboard. Replace "postgres" with "postgresql". You may need to remove "?sslmode=require" depending on where you're running the commands from. Include the service password after the user in the string. The URL pattern should resemble this:

```txt
postgresql://{db_user}:{db_password}@{db_host}:{db_port}/tsdb
```

Once the environment variable is added, execute the following command from your root project folder (containing "manage.py"):

```bash
python manage.py migrate
```

This generates all required metadata and application tables for HydroServer, excluding hypertables. To configure the TimescaleDB extension and create hypertables, run the next command using your preferred partition interval value in days (the default value is seven days) with "--partition-interval-days", or using "--no-timescale" if you want to create the observations table with partitioning disabled:

```bash
python manage.py configure_timescaledb --partition-interval-days {interval in days}
```

Now, all necessary tables are generated in your Timescale database. Several tables can be prepopulated with data. To load metadata master lists, run the following command:

```bash
python manage.py loaddata observed_properties_masterlist.yaml processing_levels_masterlist.yaml sensors_masterlist.yaml units_masterlist.yaml
```

Loading may take some time, especially from a local machine. Lastly, load a fixture with testing data (for testing or development environments only) using:

```bash
python manage.py loaddata test_data.yaml
```

Now, HydroServer backend instances can connect to this database using the connection URL for this service.
