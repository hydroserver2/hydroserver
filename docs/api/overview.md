# APIs Overview

HydroServer is composed of three APIs:

1. The [SensorThings API](/api/sensor-things-api.md) - is a faithful Django implementation of the spec.
2. The [Data Management API](/api/data-management-api.md) - contains extensions to the SensorThings API needed for fully representing a diverse range of data and allows users to manage that data in a straightforward way. In this API, you'll find extensions such as processing levels for datastreams and more metadata fields for Things.
3. The [Identity and Access Management API](/api/identity-and-access-management-api.md) - contains extensions for representing users in order to allow access control, ownership, and identification throughout our software.
