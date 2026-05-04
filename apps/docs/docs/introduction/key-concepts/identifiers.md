# HydroServer Identifiers (UUIDs)

HydroServer uses universally unique identifiers (UUIDs) within its database to uniquely identify monitoring sites, observed properties, datastreams, etc. This is important becuase many interactins with HydroServer's APIs use these UUIDs for data retrieval.

A UUID looks like the following:

`019b9aac-e3bd-77c6-9773-15f56add6f36`

UUIDs are long, and a little bit unwieldy, but they guarantee uniqueness, regardless of where they travel with the data. 

Because UUIDs are used in code to retrive data and metadata, HydroServer displays the UUIDs in the user interface of the Data Management Web App. For example, on the monitoring site landing page, you can see the UUID for the monitoring site in the site detail metadata. Each datastream on the monitoring site landing page also has a UUID. These UUIDs can be copied for use with the hydroserverpy Python client package and the API.
