# Backend Setup

## Prerequisites

Before starting, make sure you have the following software installed on your machine:

- Python 3.10+
- Docker

## Installation

1. Clone the repository:

```bash
git clone https://github.com/hydroserver2/hydroserver.git
cd hydroserver
```

2. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Define Django Settings

For our setup, we define environment variables in a .env file for local development and the same variables as GitHub secrets for deployment. For a basic development environment, only `DATABASE_URL` needs to be defined.

1. Create a `.env` file in the root of your project directory with the settings defined in .env.example.
2. The default `DATABASE_URL` is `postgresql://postgres:password@localhost:5432/tsdb`. Feel free to use this or change it to your preference.

## Setup the Database

Since HydroServer uses the Django ORM for easy database development, most of the database tables will use Postgres. However, in order to speed up database retrieval times, HydroServer uses a TimescaleDB instance to store data for the high volume `Observation Table`. We will use Docker to run TimescaleDB. Note we're using the same `DATABASE_URL` as the previous step.

1. Start a detached Docker container with the TimescaleDB image and map TimescaleDB to Postgres

```bash
docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=password -e POSTGRES_DB=tsdb timescale/timescaledb-ha:pg14-latest
```

-d is for detached mode. It allows the container to run in the background

--name timescaledb: This assigns a custom name (timescaledb) to the running container

-p 5432:5432: This maps port 5432 of the host machine to port 5432 inside the Docker container.

-e POSTGRES_PASSWORD=password: This sets an environment variable inside the container. Specifically, it sets the password for the PostgreSQL superuser (typically "postgres") to "password".

-e POSTGRES_DB=tsdb: This sets another environment variable to specify the name of the default database to be created upon container startup. In this case, the database name will be tsdb.

timescale/timescaledb-ha:pg14-latest: This specifies the image to be used for the container. It's the high-availability (HA) version of TimescaleDB based on PostgreSQL 14. The pg14-latest tag means you're pulling the latest version of this image based on PostgreSQL 14.

2. Setup Django Postgres tables:

```bash
python manage.py migrate
```

3. Setup TimescaleDB Tables

TimescaleDB installation and hypertables require additional steps beyond the Django migrate command. Run the following command to create the Observations table, install TimescaleDB, and set up the observation table as a hypertable.

```bash
python manage.py configure_timescaledb
```

-OR-

If you aren't using the TimescaleDB extension in development, instead run the following command to create the
observations table without installing TimescaleDB or setting up a hypertable.

```bash
python manage.py configure_timescaledb --no-timescale
```

## Start the Development Web Server

Start the development web server:

```bash
python manage.py runserver
```

For local development, you can access the server at `http://localhost:8000`. If you'd like to change that URL, the PROXY_BASE_URL can be found in settings.py

## Additional helpful commands

You should be ready for development after following the above instructions. If you came across any errors during setup, I've found the following commands to be useful:

```bash
docker ps                 # lists currently running containers
docker ps -a              # lists all containers in any state
docker stop timescaledb   # stops the timescaledb container
docker start timescaledb  # starts the timescaledb container
docker rm timescaledb     # deletes the timescaledb container
```

### Load Test Data

We made some sample data for testing that you can load into the database with the python script load_test_data.py:

```bash
python load_test_data.py
```
