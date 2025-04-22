# HydroServer

This repository hosts the main issue tracker for the HydroServer software stack and documentation for HydroServer components. Code repositories for each HydroServer component are linked below.

- Access the [HydroServer issue tracker](https://github.com/hydroserver2/hydroserver/issues)
- Access [HydroServer documentation](https://hydroserver2.github.io/hydroserver/)

HydroServer is a software cyberinfrastructure platform created to support collection, management, and sharing of time series of observations from hydrologic and evironmental monitoring sites. Under development at the [Utah Water Research Laboratory](https://uwrl.usu.edu/) at [Utah State University](https://www.usu.edu/), HydroServer is designed to be an open platform that enables research groups, agencies, organizations, and practitioners to more easily collect and manage streaming observations from environmental sensors.

HydroServer consists of the following components:

**HydroServer Data Management Web Application**: A web application for creating and managing monitoring sites, data streams, and associated metadata.

- Map interface for browsing data collection sites
- User interface for registering sites and creating site metadata
- User interface for creating data streams and associated metadata
- An job orchestration user interface for configuring the automated extraction, transformation, and loading of source data to their destinations.
- A data management API for programmatically managing site and datastream metadata
- Data management app code repository: [https://github.com/hydroserver2/hydroserver-data-management-app](https://github.com/hydroserver2/hydroserver-data-management-app)
- API services code repository: [https://github.com/hydroserver2/hydroserver-api-services](https://github.com/hydroserver2/hydroserver-api-services)

**HydroServer SensorThings API**: A Python Django implementation of the Open Geospatial Consortium's SensorThings API for HydroServer

- SensorThings Part 1: Sensing Version 1.1 API implementation in Python using Django
- Data ingest to HydroServer from any device capable of HTTP POST requests
- Data querying via a REST API
- SensorThings API repository: [https://github.com/hydroserver2/hydroserver-sensorthings](https://github.com/hydroserver2/hydroserver-sensorthings)

**HydroServer Streaming Data Loader**: A desktop/server app and Python package for loading streaming data into a HydroServer instance.

- Cross platform app for running on Windows, Mac, or Linux
- Silent updater for loading data to a HydroServer instance from delimited text files
- Python package (used by the app) for loading data to HydroServer via the SensorThings API
- Streaming Data Loader Desktop app repository: [https://github.com/hydroserver2/hydroloader-desktop](https://github.com/hydroserver2/hydroloader-desktop)
- HydroLoader Python package repository: [https://github.com/hydroserver2/hydroloader](https://github.com/hydroserver2/hydroloader)

## History

HydroServer builds on prior efforts and systems established by Utah State University and the Consortium of Universities for the Advancement of Hydrologic Science, Inc. (CUAHSI) [Hydrologic Information System (HIS) project](http://his.cuahsi.org), including the original HydroServer software stack that was created by that project (lovingly referred to a HydroServer 1). The legacy HydroServer (HydroServer 1) software is [archived by CUAHSI](https://github.com/CUAHSI/HydroServer). To acknowledge this legacy, the GitHub organization for this work was called HydroServer 2.

## Funding and Acknowledgements

Funding for this project was provided by the National Oceanic & Atmospheric Administration (NOAA), awarded to the Cooperative Institute for Research to Operations in Hydrology (CIROH) through the NOAA Cooperative Agreement with The University of Alabama (NA22NWS4320003). Utah State University is a founding member of CIROH and receives funding under subaward from the University of Alabama. Additional funding and support have been provided by the Utah Water Research laboratory at Utah State University.
