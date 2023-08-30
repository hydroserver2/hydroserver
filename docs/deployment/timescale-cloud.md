# HydroServer Timescale Cloud Database

This guide will walk you through setting up a HydroServer database on the Timescale Cloud
platform. Before you continue, you should create a [Timescale Cloud](https://www.timescale.com/) account. You should 
also set up an instance of the [HydroServer Django backend app](https://github.com/hydroserver2/hydroserver-webapp-back)
to run the necessary management commands.

## Create a Timescale Cloud Database Instance

From the Timescale Cloud dashboard, click "Create Service", and follow the instructions to create your Timescale Cloud
database. Once the service is created, download the service config file. Don't create a hypertable yet, Django will
handle the creation of all tables in the next step.

## Run Django Migrations and Timescale Setup Commands

To run the following commands, you'll need either a local instance of the Django HydroServer backend app, or have access
to a deployed instance. To connect to your new service, you'll use the following environment variable or entry in your
.env file:

- DATABASE_URL

The value should be a connection string to links to your TimescaleDB instance. You can use the "Service URL" under
"Connection info" on your Timescale Cloud Services dashboard, but you'll need to replace "postgres" with "postgresql",
and you may need to remove "?sslmode=require" depending on where you're running the commands from. You'll also need to 
include the service password after the user in the string. The URL should be patterned like this:

- postgresql://{db_user}:{db_password}@{db_host}:{db_port}/tsdb

Once you've added this environment variable, run the following command from your root project folder (which should
contain a file called "manage.py"):

```
python manage.py migrate
```

This will generate all necessary metadata and application tables for HydroServer, except for hypertables. To configure
the TimescaleDB extension and generate hypertables, run the following command next:

```
python manage.py configure_timescaledb
```

At this point, all necessary tables have been generated in your Timescale database. Next, there are several tables that
can be prepopulated with data. If you want to load these master lists, run the following command:

```
python manage.py loaddata observed_properties_masterlist.yaml processing_levels_masterlist.yaml sensors_masterlist.yaml units_masterlist.yaml
```

This command may take several minutes if you're loading the data from your local machine. Finally, you may also load a
fixture containing some testing data. You should only load this data in testing or development environments. Run the
following command to load test data:

```
python manage.py loaddata test_data.yaml
```

You should now be able to connect HydroServer backend instances to this database using the connection URL for this
service.
