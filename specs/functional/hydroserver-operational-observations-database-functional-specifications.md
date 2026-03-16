# HydroServer Operational Observations Database

_Functional Specifications_

## 1 Introduction


An Operational Observations Database is one of the main components of HydroServer (Figure 1). The Operational Observations Database is the primary storage location for hydrologic observations that are uploaded to the HydroServer.

Figure 1. HydroServer system architecture with operational observations database shown in blue in the center.

## 2 Requirements


The following are the requirements that must be met by the operational Operational Observations Database:

- Must be highly available
- 24/7 uptime
- Must be highly performant
- Support performant loading of data and metadata via HydroServer’s APIs.
- Support performant delivery of data and metadata through HydroServer’s APIs.
- Support performant data management via HydroServer’s APIs and the HydroServer Data Management web application.
- Must be scalable
- Support data management for individual researchers - e.g., data collection and management for < 10 monitoring locations.
- Support data management for small to medium organizations - e.g., data collection and management for < 100 monitoring locations.
- Support data management for large organizations with > 1000 monitoring locations.
- Support aggregation of data from a single or for multiple different organizations into one database.
- Must conform to the SensorThings and Observations Data Model 2.0 information model for environmental time series data and metadata.
- Must be backed up regularly with a plan for replication and disaster recovery.
- Must be deployed/deployable to commercial cloud infrastructure using common database technologies.
- Must serve as the data source for data archival to HydroShare via the Data Archival Service.
- Must support controlled vocabularies for some attributes used to describe observational data (e.g., observed property names) using controlled vocabularies derived from Version 2.0 of the Observations Data Model (ODM2) - http://vocabulary.odm2.org.

## 3 Supported Functionality


The following describe specific functionality that will be provided by the HydroServer database functionality:

- Accepts observational data loaded to HydroServer via the SensorThings API.
- Serves as the metadata storage database for all monitoring site (Thing), observed property, sensor/method, processing levels, units, etc. metadata for monitoring sites that have been loaded to the system for describing time series data.
- Serves as the source of data to be archived to HydroShare or another archival service using the Data Archival Service.
- Serves as the source of observational data delivered via public-facing Data Dissemination Services (e.g., the SensorThings API for delivering data).

## 4 Information Model for Environmental Time Series


Environmental time series data consist of individually time-stamped observations of environmental variables made using some procedure (usually a sensor deployed in situ at a fixed location monitoring site). The ODM2 Information Model (Horsburgh et al., 2016) provides an information model for describing environmental time series data that can be implemented using multiple technologies (e.g., relational database, JSON schema, XML schema, etc.). The following is a statement of the core ODM2 time series information model that must be supported:

A time series of observations of an observed variable is created at a site using a method by a person who is affiliated with an organization. The numeric values for observations are expressed using units that describe the dimensionality of the data and have a processing level (e.g., raw data, quality controlled data, etc.).

The following definitions may be useful in defining the data model for HydroServer:

Affiliation: The relationship between a person and an organization.

Method: The procedure used to create or make the observations.

Monitoring Site: A physical location at which observations are collected/made.

Observation: The numeric result and timestamp associated with applying a method or sensor at a monitoring site to record an observed property.

Observed Property: The environmental phenomenon that was observed (e.g., discharge, temperature).

Organization: The organizations that people work for or represent when creating observations.

People: The people associated with observation (i.e., who created the observation).

Processing Level: The level of processing to which observations have been subjected.

Result: The outcome of an observational procedure - consisting of an observation or set of observations.

Sensor: A particular type of method for creating/making observations consisting of an electronic device deployed to the environment to observe a phenomenon.

Time Series: A specific type of result consisting of a series of individually timestamped values representing observations of a variable at a site.

Units: The dimensional units associated with the numeric value of the observed property (e.g., m3/s, Degrees Celsius).

The Open Geospatial Consortium’s SensorThings API specification (Liang et al., 2021) has an associated data model. As a generalized data model for data associated with the Internet of Things (IoT), it is not as expressive as ODM2 for describing environmental sensor time series data, but it is a specification for how data can be organized to work with their API specification.  The combination of the two information/data models provides a way to both unambiguously describe time series data while also successfully delivering it via the OGC SensorThings API data encodings.

References

Horsburgh, J. S., Aufdenkampe, A. K., Mayorga, E., Lehnert, K. A., Hsu, L., Song, L., Spackman Jones, A., Damiano, S. G., Tarboton, D. G., Valentine, D., Zaslavsky, I., Whitenack, T. (2016). Observations Data Model 2: A community information model for spatially discrete Earth observations, Environmental Modelling & Software, 79, 55-74, https://doi.org/10.1016/j.envsoft.2016.01.010.

Liang, S., Khalafbeigi, T., van der Schaaf, H. (2021). OGC SensorThings API Part 1: Sensing Version 1.1, Open Geospatial Consortium Implementation Standard, Version 1.1, OGC 18-088, https://docs.ogc.org/is/18-088/18-088.html.
