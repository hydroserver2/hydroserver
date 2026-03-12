# HydroServer Python Client

The hydroserverpy Python package provides an interface for managing HydroServer data and metadata, loading observations, and performing data quality control. This guide will go over how to install the package and connect to a HydroServer instance. Full hydroserverpy documentation and examples can be found [here](https://hydroserver2.github.io/hydroserver/how-to/hydroserverpy/hydroserverpy-examples.html).

## Installation

You can install the package via pip:

```bash
pip install hydroserverpy
```

## Connecting to HydroServer

To connect to HydroServer, you need to initialize the client with the instance of HydroServer you're using and your user credentials if you want to access and modify your own data. If you don't provide authentication credentials you can read public data, but you will not be able to create or modify any data.

### Example: Anonymous User

```python
from hydroserverpy import HydroServer

# Initialize HydroServer connection.
hs_api = HydroServer(
    host='https://playground.hydroserver.org'
)
```

### Example: Basic Authentication

```python
from hydroserverpy import HydroServer

# Initialize HydroServer connection with credentials.
hs_api = HydroServer(
    host='https://playground.hydroserver.org',
    email='user@example.com',
    password='******'
)
```

## Funding and Acknowledgements

Funding for this project was provided by the National Oceanic & Atmospheric Administration (NOAA), awarded to the Cooperative Institute for Research to Operations in Hydrology (CIROH) through the NOAA Cooperative Agreement with The University of Alabama (NA22NWS4320003). Utah State University is a founding member of CIROH and receives funding under subaward from the University of Alabama. Additional funding and support have been provided by the State of Utah Division of Water Rights, the World Meteorological Organization, and the Utah Water Research laboratory at Utah State University.

