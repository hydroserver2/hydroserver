# SensorThings

SensorThings API is an open standard developed by the Open Geospatial Consortium (OGC) which HydroServer conforms to. In order to understand HydroServer's architecture, we feel it's necessary to first offer a simple overview of SensorThings as it is used for HydroServer.

To read OGC's SensorThings API specification for v1.1 [follow this link.](https://docs.ogc.org/is/18-088/18-088.html)

## SensorThings Architecture

<img src="/sensorThings-min.png" alt="SensorThings Image" class="img-white-bg">

### Datastreams

SensorThings is centered around the concept of a datastream, which is a structure that consists of an observed property (what you're measuring), sensor (what you're using to measure it), 0 or more observations (a data pair of [time, result]), and a list of [`metadata properties`](terminology.md#datastreams). For HydroServer, these metadata include properties like observations start and end time and unit of measurement.

### Things

Multiple `Datastreams` belong to a [`Thing`](terminology.md#sites), which for HydroServer this can be something like a groundwater well, stream flow gauge, or Snow Monitoring Site. These `Things` are composed of the geographical location of the monitoring site as well as various metadata [defined here.](terminology.md#site-metadata)

::: tip
It's important to note that SensorThings uses the term `Thing` in order to stay as general as possible. In the field of water data management, more users are more familiar with the term `Site` as in a monitoring site. Therefore, we've opted to refer to a `Thing` as `Site` in all of our user facing applications, but stick with SensorThing's original `Thing` naming for our APIs.
:::

### Locations

You'll notice on the diagram the boxes labeled `Location` and `HistoricalLocation`. SensorThings is a generalized specification which allows real-time updating of a thing's location. Our implementation of SensorThings doesn't use historical locations and requires a Thing to have one and only one location. This is because in the context of water data management we can assume the sensor will never move, or if it does, we think of it as a completely different entity - though the location can be updated if needed.

### Feature of Interest

Similar to `Historical Locations`, the SensorThings spec provides `Features of Interest` to be linked to individual observations which HydroServer has opted out of in the interest of keeping the data model simple. Feature of Interest provides additional context to what is being measured, which is redundant for water data management. If you're monitoring the Logan River, your feature of interest will always be 'Logan River' so there's no need to link that feature to each observation for the site. Rather, HydroServer provides the ability to add custom tags and metadata to the site itself.

## HydroServer Architecture

The HydroServer implementation of SensorThings is composed of three APIs:

1. The [SensorThings API](/api/sensor-things-api.md) - is a faithful Django implementation of the spec.
2. The [Data Management API](/api/data-management-api.md) - contains extensions to the SensorThings API needed for fully representing a diverse range of data and allows users to manage that data in a straightforward way. In this API, you'll find extensions such as processing levels for datastreams and more metadata fields for Things.
3. The [Account Management API](/api/account-management-api.md) - contains extensions for representing users in order to allow access control, ownership, and identification throughout our software.
