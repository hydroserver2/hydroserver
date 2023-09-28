# SensorThings

SensorThings API is an open standard developed by the Open Geospatial Consortium (OGC) which HydroServer
conforms to. In order to understand HydroServer's architecture, we feel it's necessary to first offer
a simple overview of SensorThings as it is used for HydroServer.

To read OGC's SensorThings API specification for v1.1 [follow this link.](https://docs.ogc.org/is/18-088/18-088.html)

## SensorThings Architecture

<img src="/sensorThings-min.png" alt="SensorThings Image" class="img-white-bg">

SensorThings is centered around the concept of a datastream, which is a structure that consists of an
observed property (what you're measuring), sensor (what you're using to measure it), 0 or more observations
(a data pair of [time, result]), and a list of metadata properties. For HydroServer, these metadata include
properties like observations start and end time and unit of measurement.

A user can specify a 'Thing', which for HydroServer this can be something like a groundwater well,
stream flow gauge, or Snow Monitoring Site. These 'Things' contain a collection of datastreams.

::: tip
It's important to note that SensorThings uses the term "Thing" in order to stay as general as possible.
In the field of water data management, most users are more familiar with the term "site" as in a monitoring
site. Therefore, we've opted to refer to a 'Thing' as 'Site' in all of our user facing applications, but stick with
SensorThing's original 'Thing' naming for our APIs
:::

Additionally, the SensorThings spec defines a Thing with its current locations and many historical locations.

## HydroServer Architecture

Not to be confused with the SensorThings API specification, we've created a Django API named the "HydroServer SensorThings API"
that implements the SensorThings spec with a few caveats. Our implementation of SensorThings doesn't use historical locations
and requires a Thing to have one and only one location. This is because in the context of water data management
we can assume the sensor will never move, or if it does, we think of it as a completely different entity. For in
depth documentation of our SensorThings implementation, [go here.](/api/sensor-things-api.md)

In order to host a system with a diverse user base, we needed to add concepts like users, organizations, and various metadata.
These functionalities are implemted in extension APIs called the [Data Management API](/api/data-management-api.md) and the [Account Management API](/api/account-management-api.md).
