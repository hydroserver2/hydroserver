# HydroServer Overview

## What is HydroServer?

HydroServer is a Hydrologic Information System (HIS) designed to enable the collection, storage, management, and sharing of environmental time-series data. It is a modular software system aimed at meeting the day-to-day data management needs of researchers, scientists, and practitioners who operate environmental monitoring stations, help manage the data they produce, and make their data available through standards-based data sharing.

### The HydroServer Instance

The core of the software ecosystem is your **HydroServer Instance**. Rather than a single, centralized platform, HydroServer is a decentralized software system that you deploy independently. Your specific instance is the live, hosted environment—consisting of the database, application programming interfaces (APIs), and web apps—that serves as the dedicated central hub for your organization's environmental sensor data.

Most organizations will start by following our [production deployment guide](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md) to deploy their own instance, whether on-premises (using a local server or VM) or through a cloud provider like **Google Cloud Platform** or **Amazon Web Services**. The HydroServer platform is packaged and distributed as a set of deployable images, allowing you to host your instance across a wide variety of cloud providers—provided they support standard web application hosting, container services, and PostgreSQL relational databases. Throughout this documentation, when we refer to "an instance," we mean your specific, deployed version of the HydroServer software that you manage and maintain as a persistent web service.

### OGC SensorThings API

HydroServer implements the [OGC SensorThings API (v1.1)](https://docs.ogc.org/is/18-088/18-088.html), which serves as the foundation of its data model and other APIs. SensorThings is an open standard developed by the Open Geospatial Consortium (OGC) for connecting and sharing data from IoT sensors and environmental monitoring systems, enabling interoperability across platforms and tools.

For more on how HydroServer adopts and extends SensorThings, see [Background and Motivation](/introduction/background-and-motivation).

### Client-side Applications and Packages

HydroServer includes two main client packages to help users work with HydroServer and the data and metadata it contains:

1. `hydroserverpy` **(Python Package)**: This is a Python wrapper for the HydroServer REST API, designed for those who want to manage data programmatically. Beyond simple API interaction, the package includes specialized tools for performing time series ETL (Extract, Transform, Load) and automated quality control. You can use hydroserverpy to script or automate nearly everything you can do through the web user interface of the HydroServer Data management App.

2. `hydroserver-ts` **(NodeJS Package)**: This is a TypeScript library designed to help developers build web applications that need to plug into HydroServer’s APIs.

3. **The Streaming Data Loader**: A desktop application designed to automate data ingestion from CSV data files into HydroServer. It monitors local or web accessible CSV files containing environmental time-series data and automatically loads them into your HydroServer instance, reducing the need for manual uploads. The Streaming Data Loader was designed to help integrate with commercial sensor software systems that interact with monitoring stations and produce datalogger files in CSV format.

## Cite HydroServer

The following are the preferred citations for HydroServer:

Horsburgh, J. S., Lippold, K., Slaugh, D. L., Ramirez, M. (2024). HydroServer: A software stack supporting collection, communication, storage, management, and sharing of data from in situ environmental sensors, Environmental Modelling & Software, 106637, [https://doi.org/10.1016/j.envsoft.2025.106637](https://doi.org/10.1016/j.envsoft.2025.106637).

Horsburgh, J. S., Lippold, K., Slaugh, D. L. (2025). Adapting OGC’s SensorThings API and data model to support data management and sharing for environmental sensors, Environmental Modelling & Software, 183, 106241, [https://doi.org/10.1016/j.envsoft.2024.106241](https://doi.org/10.1016/j.envsoft.2024.106241).


## Access HydroServer on GitHub

HydroServer is maintained as an open-source software project on GitHub. Navigate to the [HydroServer GitHub Organization](https://github.com/hydroserver2) to view or contribute to HydroServer's source code.

## Next Steps

If you'd like a hands-on tutorial for setting up a monitoring site and streaming data to our playground instance of Hydroserver, head over to our [HydroServer 101](/user-guides/tutorials/hydroserver-101/) tutorial series.

If you're a developer wanting to contribute to HydroServer or build an application on top of it, check out our [Developer Documentation](/developing-and-contributing/).

If you want to deploy and manage your own instance of HydroServer, see our [Production Deployment Guide](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md).

To learn more about the HydroServer system and concepts, we recommend starting with [Key Concepts](/introduction/key-concepts/).
