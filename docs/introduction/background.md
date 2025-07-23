# Background

HydroServer was developed at the Utah Water Research Laboratory to meet two key needs:

1. Ingest and retrieve large volumes of time-series data efficiently.
2. Provide a formally structured data model suitable for environmental research.

To meet these goals, we built:

- A PostgreSQL-based database using the Django REST Framework for API access.
- An implementation of the OGC SensorThings API standard as the foundation of the data model.

## Why SensorThings Was Chosen — and Extended

The [SensorThings API (v1.1)](https://docs.ogc.org/is/18-088/18-088.html) offers a standardized way to expose and organize sensor data. It provides an extensible, web-friendly format ideal for Internet of Things (IoT) devices, and is widely used in domains like environmental monitoring, building automation, and smart cities.

HydroServer adopts SensorThings' core data model (shown below), using it as the backbone of our own system:

<a :href="STDataModelLight" target="_blank" rel="noopener noreferrer" >
  <img :src="STDataModelDark" alt="OGC SensorThings Data Model" class="dark-only" />
  <img :src="STDataModelLight" alt="OGC SensorThings Data Model" class="light-only" />
</a>

However, SensorThings was designed to be _generic_ — which made it flexible but too abstract for the specific needs of hydrologic and environmental time-series data. In particular, it lacked fields for:

- Authentication and access control
- Extract, transform, load-style data orchestration
- Controlled vocabulary references
- Detailed metadata such as processing levels, units, qualifying comments on observations, photos, and tags

Fortunately, the SensorThings model supports extensibility using the properties and parameters attributes of each entity. We leveraged this mechanism to add the metadata needed for unambiguous environmental data interpretation.

## Influence of ODM2 on HydroServer

To enhance SensorThings for environmental use, we extended its entities using metadata fields inspired by [Observations Data Model 2 (ODM2)](https://doi.org/10.1016/j.envsoft.2016.01.010), a community information model for Earth observations.

While ODM2 supports many types of observation data, HydroServer focuses on a specific subset: time series observations from fixed-location monitoring sites.

The UML diagram below shows the portion of the ODM2 model that influenced HydroServer’s extensions:

<a :href="ODMModelLight" target="_blank" rel="noopener noreferrer" >
  <img :src="ODMModelDark" alt="ODM Time Series Information Model" class="dark-only" />
  <img :src="ODMModelLight" alt="ODM Time Series Information Model" class="light-only" />
</a>

By combining the flexible API structure of SensorThings with the domain-specific richness of ODM2, we created a hybrid model tailored for environmental data workflows.

# HydroServer Data Model

HydroServer operates on top of a relational database that stores time series data using [PostgreSQL](https://www.postgresql.org/). Here we document the relational data model used by the HydroServer software for storing time series data.

The following is an entity relationship diagram illustrating the HydroServer data model design. Primary and foreign keys are specified in the first column of each entity. Mandatory attributes are specified with "(M)" preceding the attribute name. Optional attributes are specified with "(O)" preceding the attribute name. Data types are specified following the attribute name. Given that some attributes were derived from the Observations Data Model (ODM2), the third column shows the the mapping of attributes in HydroServer's data model to ODM attributes. Entities shown with blue title bars are part of the SensorThings API data model. Entities with white title bars were added to the SensorThings data model to accommodate functionality required for the HydroServer software.

<a :href="hydroserverDataModelLight" target="_blank" rel="noopener noreferrer" >
  <img :src="hydroserverDataModelDark" alt="HydroServer Data Model" class="dark-only"/>
  <img :src="hydroserverDataModelLight" alt="HydroServer Data Model" class="light-only" />
</a>

<script setup>  
import STDataModelDark from "./ogc_sensorthings_data_model_dark.png"
import STDataModelLight from "./ogc_sensorthings_data_model_light.png"
import ODMModelDark from "./odm_time_series_information_model_dark.png"
import ODMModelLight from "./odm_time_series_information_model_light.png"
import hydroserverDataModelLight from './hydroserver_data_model_light.png' 
import hydroserverDataModelDark from './hydroserver_data_model_dark.png'
</script>
