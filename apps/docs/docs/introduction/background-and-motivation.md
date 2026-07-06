# Background and Motivation

## Why We Built HydroServer

Operational and scientific use of environmental sensor data requires effective data management software, yet operators of sensor networks often struggle with day-to-day data management and eventual data sharing. Few reliable, modern, and generic options exist — available commercial software tends to be expensive or tied to specific sensor and datalogger manufacturers.

HydroServer was developed at the [Utah Water Research Laboratory](https://uwrl.usu.edu) at [Utah State University](https://www.usu.edu) to address these gaps and meet several key needs:

1. Ingest and retrieve large volumes of time-series data efficiently.
2. Provide a formally structured data model suitable for environmental time series data.
3. Meet the day-to-day needs of researchers, scientists, and practitioners who need data management software for environmental sensor data.

## HydroServer's History

HydroServer was originally part of the Consortium of Universities for the Advancement of Hydrologic Science, Inc. (CUAHSI) Hydrologic Information System (HIS). Developed around 2007 – 2015, the CUAHSI HIS was a first of its kind HIS that enabled distributed data servers (HydroServers) to host databases and web services that were then cataloged by CUAHSI to provide data discovery and download services. The CUAHSI HIS was operated by CUAHSI for several years as a service to the hydrology science community in the United States. 

In 2022, USU received funding through the Cooperative Institute for Research to Operations in Hydrology (CIROH) to modernize HydroServer as a data management system for environmental sensor data. HydroServer is now being used in several different operational contexts for environmental sensor data management.

## Why OGC SensorThings Was Chosen — and Extended

The Open Geospatial Consortium (OGC) [SensorThings API (v1.1)](https://docs.ogc.org/is/18-088/18-088.html) offers a standardized way to expose and organize sensor data. It provides an extensible, web-friendly data model and API ideal for Internet of Things (IoT) devices, and is widely used in domains like environmental monitoring, building automation, and smart cities. It is a modern, REST-based API with data transfer encodings that use JSON.

HydroServer adopts SensorThings' core data model (shown below), using it as the backbone of our own system:

<a :href="STDataModelLight" target="_blank" rel="noopener noreferrer" >
  <img :src="STDataModelDark" alt="OGC SensorThings Data Model" class="dark-only" />
  <img :src="STDataModelLight" alt="OGC SensorThings Data Model" class="light-only" />
</a>

However, SensorThings was designed to be _generic_ — which made it flexible but too abstract for the specific needs of hydrologic and environmental time-series data. In particular, it lacked fields for:

- Information about users along with authentication and access control
- Extract, transform, load-style data orchestration
- Controlled vocabulary references
- Detailed, environmental sensor-specific metadata such as processing levels, units, qualifying comments on observations, photos, tags, etc.

Fortunately, the SensorThings data model and API support extensibility using the `properties` and `parameters` attributes of each entity. We leveraged this mechanism to add the metadata needed for unambiguous environmental data interpretation.

## Influence of ODM2 on HydroServer

To enhance SensorThings for use with environmental sensor data, we extended its entities using metadata fields inspired by [Observations Data Model 2 (ODM2)](https://doi.org/10.1016/j.envsoft.2016.01.010), a community information model for Earth observations.

While ODM2 supports many types of observation data, HydroServer focuses on a specific subset: time series observations from fixed-location monitoring sites.

The UML diagram below shows the portion of the ODM2 model that influenced HydroServer’s extensions:

<a :href="ODMModelLight" target="_blank" rel="noopener noreferrer" >
  <img :src="ODMModelDark" alt="ODM Time Series Information Model" class="dark-only" />
  <img :src="ODMModelLight" alt="ODM Time Series Information Model" class="light-only" />
</a>

By combining the flexible API structure of SensorThings with the domain-specific metadata richness of ODM2, we created a hybrid data model that is still standards-compliant, but tailored for environmental sensor data workflows.

For detailed information about HydroServer's data model, go to the [data model documentation](/references/data-model.md).

<script setup>
const STDataModelLight = '/data-model/ogc_sensorthings_data_model_light.png'
const STDataModelDark = '/data-model/ogc_sensorthings_data_model_dark.png'
const ODMModelLight = '/data-model/odm_time_series_information_model_light.png'
const ODMModelDark = '/data-model/odm_time_series_information_model_dark.png'
</script>
