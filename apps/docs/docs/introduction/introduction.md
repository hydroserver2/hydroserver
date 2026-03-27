# Introduction

## What is HydroServer?

HydroServer is a data management system designed to store, manage, and share a diverse range of environmental time-series data. It is a modular system that connects data sources to researchers and decision-makers.

### The HydroServer Instance

The core of the ecosystem is your **HydroServer Instance**. This is the live, hosted environment—consisting of the database, APIs, and apps—that serves as the central hub for your environmental data.

Most organizations will start by following our [production deployment guide](/how-to/deployment/production-deployment-overview.md) to spin up their own instance, whether on-premises (using a local server or VM) or through a cloud provider like **Google Cloud Platform** or **Amazon Web Services**. Throughout this documentation, when we refer to "an instance," we mean your specific, deployed version of the HydroServer software that you manage and maintain as a persistent web service.

### Client-side applications and packages which include:

1. `hydroserverpy` **(Python Package)**: This is a Python wrapper for the HydroServer REST API, designed for those who want to manage data programmatically. Beyond simple API interaction, the package includes specialized tools for performing time-series ETL (Extract, Transform, Load) and automated quality control.

2. `hydroserver-ts` **(NodeJS Package)**: This is a TypeScript library designed to help developers build web applications that need to plug into HydroServer’s APIs.

3. **The Streaming Data Loader**: A desktop application designed to automate data ingestion into HydroServer. It monitors local CSV files containing environmental time-series data and automatically loads them into your HydroServer instance, reducing the need for manual uploads.

## Cite HydroServer

The following are the preferred citations for HydroServer:

Horsburgh, J. S., Lippold, K., Slaugh, D. L., Ramirez, M. (2024). HydroServer: A software stack supporting collection, communication, storage, management, and sharing of data from in situ environmental sensors, Environmental Modelling & Software, 106637, [https://doi.org/10.1016/j.envsoft.2025.106637](https://doi.org/10.1016/j.envsoft.2025.106637).

Horsburgh, J. S., Lippold, K., Slaugh, D. L. (2025). Adapting OGC’s SensorThings API and data model to support data management and sharing for environmental sensors, Environmental Modelling & Software, 183, 106241, [https://doi.org/10.1016/j.envsoft.2024.106241](https://doi.org/10.1016/j.envsoft.2024.106241).

## Next Steps

If you'd like a hands-on tutorial for setting up a monitoring site and streaming data to a playground instance of Hydroserver, head over to [HydroServer 101.](/tutorials/hydroserver-101.md)

If you'd like to read more about our system, we recommend starting with [Key Concepts](/introduction/key-concepts/sites).
