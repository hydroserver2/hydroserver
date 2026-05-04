# HydroServer Data Model 

The following is an entity relationship diagram illustrating the HydroServer data model design. You can also access a [data dictionary](data-dictionary.md) that describes each of the entities and attributes along with data types and descriptive information.

Primary and foreign keys are specified in the first column of each entity. Mandatory attributes are specified with "(M)" preceding the attribute name. Optional attributes are specified with "(O)" preceding the attribute name. Data types are defined in the data dictionary document. Entities shown with blue title bars are part of the SensorThings API data model. Entities with white title bars were added to the SensorThings data model to accommodate functionality required for the HydroServer software.

<a :href="hydroserverDataModelLight" target="_blank" rel="noopener noreferrer" >
  <img :src="hydroserverDataModelDark" alt="HydroServer Data Model" class="dark-only"/>
  <img :src="hydroserverDataModelLight" alt="HydroServer Data Model" class="light-only" />
</a>

<script setup>  
import hydroserverDataModelLight from '../../introduction/hydroserver_data_model_light.png'
import hydroserverDataModelDark from '../../introduction/hydroserver_data_model_dark.png'
</script>
