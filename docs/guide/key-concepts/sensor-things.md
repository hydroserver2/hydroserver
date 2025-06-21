# SensorThings

The SensorThings API is an open standard developed by the Open Geospatial Consortium (OGC). HydroServer conforms to this standard and extends it in a few important ways. First, HydroServer is built to support multi-tenet setups, and therefore provides authentication and access control capabilities that go well beyond the SensorThings specification. Second, HydroServer extends metadata flexibility. We knew it would be important for users with existing data to be able to migrate all of their metadata without losing important fields. Therefore, HydroServer extends the SensorThings 'Datastream' database table with additional fields and auxiliary database tables such as Unit, and Processing Level as well as a tagging system.

We won't take the time to explain SensorThings in this documentation since there are ample explanations available elsewhere.

To read OGC's SensorThings API specification for v1.1 [follow this link.](https://docs.ogc.org/is/18-088/18-088.html)

Below: the SensorThings data model.

<img src="/sensorThings-min.png" alt="SensorThings Image" class="img-white-bg">
