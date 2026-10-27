# HydroServer Python Client

The hydroserverpy Python package provides an interface for managing HydroServer data and metadata, loading observations, and performing data quality control. This guide will go over how to install the package and connect to a HydroServer instance. Full hydroserverpy documentation and examples can be found [here](https://hydroserver2.github.io/hydroserver/user-guides/how-to/using-the-python-client.html).

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

### Example: API Key Authentication

```python
from hydroserverpy import HydroServer

hs_api = HydroServer(
    host='https://playground.hydroserver.org',
    apikey='hs_your_api_key'
)
```

### Example: OIDC Access Token Authentication

Applications that sign users in through HydroServer's OpenID Connect provider can act on the user's behalf with the access token they received:

```python
from hydroserverpy import HydroServer

hs_api = HydroServer(
    host='https://playground.hydroserver.org',
    access_token='your_access_token'
)
```

Access tokens expire, so you can pass a function instead of a string. It is called before every request, so it can return a refreshed token when the current one has expired. For example, with a token stored by python-social-auth:

```python
from social_django.utils import load_strategy

def get_access_token():
    social = user.social_auth.get(provider='oidc')
    if social.access_token_expired():
        social.refresh_token(load_strategy())
    return social.extra_data['access_token']

hs_api = HydroServer(
    host='https://playground.hydroserver.org',
    access_token=get_access_token
)
```

The token must carry the scopes for the operations you perform, for example `data:read` to read monitoring sites, datastreams, and observations, `data:write` to change them, and `workspace:read` to list workspaces. Requests made without a required scope fail with a 403 error that names the missing scope.

## Funding and Acknowledgements

Funding for this project was provided by the National Oceanic & Atmospheric Administration (NOAA), awarded to the Cooperative Institute for Research to Operations in Hydrology (CIROH) through the NOAA Cooperative Agreement with The University of Alabama (NA22NWS4320003). Utah State University is a founding member of CIROH and receives funding under subaward from the University of Alabama. Additional funding and support have been provided by the State of Utah Division of Water Rights, the World Meteorological Organization, and the Utah Water Research laboratory at Utah State University.
