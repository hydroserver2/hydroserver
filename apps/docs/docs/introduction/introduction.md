# Introduction

Use the menu to your left to navigate through HyroServer's documentation. The following is a brief overview of the documentation we provide:

* **[Background](/introduction/background.md)**: Learn about why we developed HydroServer and why we chose SensorThings
* **[Getting Started](/introduction/getting-started.md)**: Link to the Playground instance where you can try out HydroServer functionality or link to developer documentation for deploying HydroServer or contributing code
* **[Key Concepts](/introduction/key-concepts/key-concepts.md)**: Learn about key organizational concepts in HydroServer's data model, including sites, datastreams, etc.
* **[Tutorials](/tutorials/tutorials.md)**: Access our HydroServer 101 tutorial (for users) along with information on getting started with the HydroServer TypeScript client (for web developers)
* **[How-to](/how-to/how-to.md)**: Access deployment documentation, documentation for our Python and TypeScript clients, and HydroServer API documentation - including code examples
* **[References](/references/references.md)**: Access low-level API documentation, detailed information about HydroServer's API

## What is HydroServer?

HydroServer is a Hydrologic Information System (HIS) designed to enable collection, storage, management, and sharing of a diverse range of environmental time-series data. It is a modular software system that is aimed at meeting the day-to-day data management needs of researchers, scientists, and practitioners who operate environmental monitoring stations, manage the data they produce, and have needs for standards-based data sharing.

### The HydroServer Instance

The core of the software ecosystem is your **HydroServer Instance**. This is the live, hosted environment—consisting of the database, application programming interfaces (APIs), and web apps—that serves as the central hub for your environmental sensor data.

Most organizations will start by following our [production deployment guide](/how-to/deployment/production-deployment-overview.md) to deploy their own instance, whether on-premises (using a local server or VM) or through a cloud provider like **Google Cloud Platform** or **Amazon Web Services**. We recommend deployment on Google Cloud Platform as our instructions and testing for that cloud provider is most comprehensive, but HydroServer can be deployed using the other options mentioned above. Throughout this documentation, when we refer to "an instance," we mean your specific, deployed version of the HydroServer software that you manage and maintain as a persistent web service.

### Client-side Applications and Packages

HydroServer includes two main client packages to help users work with HydroServer and the data and metadata it contains:

1. `hydroserverpy` **(Python Package)**: This is a Python wrapper for the HydroServer REST API, designed for those who want to manage data programmatically. Beyond simple API interaction, the package includes specialized tools for performing time series ETL (Extract, Transform, Load) and automated quality control. You can use hydroserverpy to script or automate nearly everything you can do through the web user interface of the HydroServer Data management App.

2. `hydroserver-ts` **(NodeJS Package)**: This is a TypeScript library designed to help developers build web applications that need to plug into HydroServer’s APIs.

3. **The Streaming Data Loader**: A desktop application designed to automate data ingestion from CSV data files into HydroServer. It monitors local or web accessible CSV files containing environmental time-series data and automatically loads them into your HydroServer instance, reducing the need for manual uploads. The Streaming Data Loader was designed to help integrate with commercial sensor software systems that interact with monitoring stations and produce datalogger files in CSV format.

## Cite HydroServer

The following are the preferred citations for HydroServer:

Horsburgh, J. S., Lippold, K., Slaugh, D. L., Ramirez, M. (2024). HydroServer: A software stack supporting collection, communication, storage, management, and sharing of data from in situ environmental sensors, Environmental Modelling & Software, 106637, [https://doi.org/10.1016/j.envsoft.2025.106637](https://doi.org/10.1016/j.envsoft.2025.106637).

Horsburgh, J. S., Lippold, K., Slaugh, D. L. (2025). Adapting OGC’s SensorThings API and data model to support data management and sharing for environmental sensors, Environmental Modelling & Software, 183, 106241, [https://doi.org/10.1016/j.envsoft.2024.106241](https://doi.org/10.1016/j.envsoft.2024.106241).


## Access HydroServer in GitHub

HydroServer is maintaned as an open-source software project in GitHub. Navigate to the HydroServer [GitHub Organization](https://github.com/hydroserver2) to access HydroServer's source code.

## Next Steps

If you'd like a hands-on tutorial for setting up a monitoring site and streaming data to a playground instance of Hydroserver, head over to [HydroServer 101.](/tutorials/hydroserver-101.md)

If you'd like to read more about our system, we recommend starting with [Key Concepts](/introduction/key-concepts/key-concepts).
