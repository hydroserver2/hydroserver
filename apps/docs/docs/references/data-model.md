# HydroServer Data Model 

The following are entity relationship diagrams illustrating the HydroServer data model design. You can also access a [data dictionary](/references/data-dictionary.md) that describes each of the entities and attributes along with data types and descriptive information.

Primary and foreign keys are specified in the first column of each entity. Mandatory attributes are specified with "(M)" preceding the attribute name. Optional attributes are specified with "(O)" preceding the attribute name. Data types are defined in the data dictionary document. In the data storage model, entities shown with blue title bars are part of the SensorThings API data model, and entities with white title bars were added to accommodate functionality required for the HydroServer software. Greyed-out entities with a struck-through name are SensorThings concepts that HydroServer exposes through the SensorThings API but doesn't store as tables. In the data processing model, title bar colors group the entities by feature: orchestration, ETL, data products, and monitoring. `PeriodicTask` (purple) belongs to the django-celery-beat scheduler and is abbreviated.

## Identity and Access Management Model

Covers users, workspaces, roles, and collaborators — the entities that control who owns and has access to resources in HydroServer.

<a :href="hydroserverIamModelLight" target="_blank" rel="noopener noreferrer">
  <img :src="hydroserverIamModelDark" alt="HydroServer IAM Model" class="dark-only"/>
  <img :src="hydroserverIamModelLight" alt="HydroServer IAM Model" class="light-only"/>
</a>

## Data Storage Model

Covers sites, datastreams, observations, and associated metadata — the core entities for representing monitoring locations and the time series data collected at them.

<a :href="hydroserverDataModelLight" target="_blank" rel="noopener noreferrer">
  <img :src="hydroserverDataModelDark" alt="HydroServer Data Model" class="dark-only"/>
  <img :src="hydroserverDataModelLight" alt="HydroServer Data Model" class="light-only"/>
</a>

## Data Processing Model

Covers ETL tasks, data product tasks, and monitoring tasks — the entities that define automated data ingestion, transformation, and quality monitoring workflows.

<a :href="hydroserverProcessingModelLight" target="_blank" rel="noopener noreferrer">
  <img :src="hydroserverProcessingModelDark" alt="HydroServer Processing Model" class="dark-only"/>
  <img :src="hydroserverProcessingModelLight" alt="HydroServer Processing Model" class="light-only"/>
</a>

<script setup>
const hydroserverIamModelLight = '/data-model/hydroserver_iam_model_light.png'
const hydroserverIamModelDark = '/data-model/hydroserver_iam_model_dark.png'
const hydroserverDataModelLight = '/data-model/hydroserver_data_model_light.png'
const hydroserverDataModelDark = '/data-model/hydroserver_data_model_dark.png'
const hydroserverProcessingModelLight = '/data-model/hydroserver_processing_model_light.png'
const hydroserverProcessingModelDark = '/data-model/hydroserver_processing_model_dark.png'
</script>
