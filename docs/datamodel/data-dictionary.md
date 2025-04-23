# HydroServer Data Model Data Dictionary

This document describes the entities and attributes within the HydroServer data model. 


## User

A registered HydroServer user with identifying details and access metadata.

| Required | Attribute            | Definition                                                                 | Data Type     |
| -------- | -------------------- | -------------------------------------------------------------------------- | ------------- |
| M        | id                   | A primary key unique identifier for the User.                              | Integer       |
| M        | email                | A unique email address identifying the User.                               | String        |
| M        | first_name           | The User’s first name.                                                     | String        |
| M        | last_name            | The User’s last name.                                                      | String        |
| O        | middle_name          | The User’s middle name.                                                    | String        |
| O        | phone                | A contact phone number for the User.                                       | String        |
| O        | address              | The User’s mailing or physical address.                                    | String        |
| O        | link                 | A URL associated with the User (e.g., profile or homepage).                | URL           |
| M        | user_type            | A descriptor for the type or role of the User.                             | String        |
| O        | organization_id      | A reference to the Organization the User is affiliated with.               | Integer       |
| M        | is_ownership_allowed | Indicates whether the User is allowed to own Workspaces.                   | Boolean       |
| M        | is_superuser         | Indicates whether the User is a superuser (admin).                         | Boolean       |
| M        | is_staff             | Indicates whether the User has a staff account.                            | Boolean       |
| M        | is_active            | Indicates whether the User's account is active.                            | Boolean       |
| M        | date_joined          | The date and time the User created their HydroServer account.              | DateTime      |
| M        | last_login           | The date and time of the User's last login.                                | DateTime      |


## Organization

An entity such as an institution, agency, or company that is associated with a User.

| Required | Attribute         | Definition                                                                   | Data Type |
| -------- | ----------------- | ---------------------------------------------------------------------------- | --------- |
| M        | id                | A primary key unique identifier for the Organization.                        | Integer   |
| M        | code              | A short, unique code identifying the Organization.                           | String    |
| M        | name              | The full name of the Organization.                                           | String    |
| O        | description       | A brief textual description of the Organization.                             | String    |
| O        | link              | A URL linking to the Organization’s homepage or relevant web presence.       | URL       |
| M        | organization_type | A classification or descriptor of the Organization (e.g., university, NGO).  | String    |


## Workspace

Workspaces in HydroServer are used to organize and manage access to user-managed data. All user-managed resources in HydroServer are created within the context of a workspace. Each workspace has one owner and can have any number of collaborators with varying levels of access to resources within the workspace.


| Required | Attribute   | Definition                                                                 | Data Type |
| -------- | ----------- | -------------------------------------------------------------------------- | --------- |
| M        | id          | A primary key unique identifier for the Workspace.                         | UUID      |
| M        | name        | A name for the Workspace.                                                  | String    |
| M        | owner_id    | A foreign key identifier for the User who owns the Workspace.              | Integer   |
| M        | is_private  | A boolean indicating whether the Workspace is private or publicly visible. | Boolean   |


## Role

A set of permissions or access level definitions assigned to collaborators within a Workspace. HydroServer's default roles are 'Viewer' and 'Editor'.

| Required | Attribute    | Definition                                                                 | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the Role.                              | UUID      |
| O        | workspace_id | A foreign key identifier for the Workspace to which the Role belongs.      | UUID      |
| M        | name         | A name for the Role.                                                       | String    |
| O        | description  | A text description of the Role.                                            | String    |


## Permission

Defines a specific permission granted to a Role for a particular type of resource.

| Required | Attribute       | Definition                                                                     | Data Type |
| -------- | --------------- | ------------------------------------------------------------------------------ | --------- |
| M        | role_id         | A foreign key identifier for the Role to which this permission belongs.        | UUID      |
| M        | permission_type | The type of permission (e.g., view, create, etc) granted to the Role.          | String    |
| M        | resource_type   | The type of resource the permission applies to (e.g., Datastream, Thing, etc). | String    |


## Collaborator

Associates a User with a Role in a specific Workspace.

| Required | Attribute    | Definition                                                                   | Data Type |
| -------- | ------------ | ---------------------------------------------------------------------------- | --------- |
| M        | workspace_id | A foreign key identifier for the Workspace the user collaborates on.         | UUID      |
| M        | user_id      | A foreign key identifier for the User who is a collaborator.                 | Integer   |
| M        | role_id      | A foreign key identifier for the Role assigned to the User in the Workspace. | UUID      |


## Thing

A thing is an object of the physical world (physical things) or the information world (virtual things) that is capable of being identified and integrated into communication networks. In the context of environmental monitoring and HydroServer, a Thing is a monitoring station or "Site" (e.g., a streamflow gage, water quality station, weather station, diversion measurement location, etc.).

| Required | Attribute              | Definition                                                                 | Data Type |
| -------- | ---------------------- | -------------------------------------------------------------------------- | --------- |
| M        | id                     | A primary key unique identifier for the Thing.                             | UUID      |
| M        | workspace_id           | A foreign key identifier for the Workspace that the Thing belongs to.      | UUID      |
| M        | name                   | A text string giving a name for the Thing.                                 | String    |
| M        | description            | A text string giving a description for the Thing.                          | String    |
| M        | sampling_feature_type  | A text string specifying the type of sampling feature - usually "Site".    | String    |
| M        | sampling_feature_code  | A text string specifying a shortened code identifying the Thing.           | String    |
| M        | site_type              | A text string specifying the type of Site represented by the Thing - e.g., "Streamflow Gage", "Water Quality Station", "Weather Station", "Diversion Station", etc. | String    |
| O        | is_private             | Indicates whether the Thing is private to the owning Workspace.            | Boolean   |
| O        | data_disclaimer        | A text string displayed on the HydroServer landing page for the Thing (Site) that specifies a data disclaimer for data at that site. | String    |


## Location

The Location entity locates the Thing. A Thing’s Location entity is defined as the last known location of the Thing. In the context of Things that are monitoring sites, this is the physical location of the monitoring site.

| Required | Attribute        | Definition                                                                                  | Data Type |
| -------- | ---------------- | ------------------------------------------------------------------------------------------- | --------- |
| M        | id               | A primary key unique identifier for the Location.                                           | UUID      |
| M        | thing_id         | A foreign key identifier for the Thing to which this Location belongs.                      | UUID      |
| M        | name             | A text string name for the Location. Can be the same as the name of the Thing.              | String    |
| M        | description      | A text string description of the Location.                                                  | String    |
| M        | encoding_type    | The encoding type of the Location - usually "GeoJSON".                                      | String    |
| M        | latitude         | A floating point number representing the latitude of the location using WGS84 coordinates.  | Decimal   |
| M        | longitude        | A floating point number representing the longitude of the location using WGS84 coordinates. | Decimal   |
| O        | elevation_m      | A floating point number representing the elevation of the location in meters.               | Decimal   |
| O        | elevation_datum  | A string indicating the elevation datum used by the site to specify the elevation.          | String    |
| O        | state            | The state in which the Location resides.                                                    | String    |
| O        | county           | The county in which the Location resides.                                                   | String    |
| O        | country          | The ISO 3166-1 alpha-2 country code (e.g., "US").                                           | String    |


## Tag

A key-value metadata pair associated with a Thing, used to provide additional descriptive or categorical information.

| Required | Attribute | Definition                                                          | Data Type |
| -------- | --------- | ------------------------------------------------------------------- | --------- |
| M        | thing_id  | A foreign key identifier for the Thing to which the tag applies.    | UUID      |
| M        | key       | The tag key or name.                                                | String    |
| M        | value     | The tag value associated with the key.                              | String    |


## Photo

A photo of a Thing - e.g., photos of a monitoring site/location.

| Required | Attribute | Definition                                                                 | Data Type |
| -------- | --------- | -------------------------------------------------------------------------- | --------- |
| M        | thing_id  | A foreign key identifier for the Thing to which the photo is linked.       | UUID      |
| M        | name      | A descriptive name for the photo.                                          | String    |
| M        | photo     | A file path reference to the uploaded photo file.                          | String    |


## ObservedProperty

An ObservedProperty specifies the phenomenon of an Observation (e.g., flow, temperature, pH, dissolved oxygen concentration, etc.).

| Required | Attribute             | Definition                                                                                             | Data Type |
| -------- | --------------------- | ------------------------------------------------------------------------------------------------------ | --------- |
| M        | id                    | A primary key unique identifier for the ObservedProperty.                                              | UUID      |
| O        | workspace_id          | A foreign key identifier for the Workspace the ObservedProperty belongs to.                            | UUID      |
| M        | name                  | A descriptive name for the ObservedProperty - preferably chosen from a controlled vocabulary.          | String    |
| M        | definition            | A text string providing a definition of the ObservedProperty or a URL pointing to a definition of the ObservedProperty - e.g., a URL pointing to the controlled vocabulary that defines the observed property. | String    |
| M        | description           | A text description of the ObservedProperty. May be the same as the definition of the ObservedProperty. | String    |
| M        | observed_property_type| The type of ObservedProperty - preferably selected from a controlled vocabulary (e.g., Hydrology, Instrumentation, Climate, Soil, Water Quality, etc.). | String    |
| M        | code                  | A brief text code identifying the ObservedProperty.                                                    | String    |


## ProcessingLevel

The degree of quality control or processing to which a Datastream has been subjected. For example, raw versus quality controlled data.

| Required | Attribute    | Definition                                                                                                        | Data Type |
| -------- | ------------ | ----------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the ProcessingLevel.                                                          | UUID      |
| O        | workspace_id | A foreign key identifier for the Workspace the ProcessingLevel belongs to.                                        | UUID      |
| M        | code         | A brief text code identifying the Processing level - e.g., "0" for "Raw data", "1" for "Quality controlled data." | String    |
| O        | definition   | A text definition of the ProcessingLevel.                                                                         | String    |
| O        | explanation  | A longer text explanation of the ProcessingLevel.                                                                 | String    |


## ResultQualifier

Data qualifying comments added to individual data values to qualify their interpretation or use.

| Required | Attribute    | Definition                                                                 | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the ResultQualifier.                   | UUID      |
| O        | workspace_id | A foreign key identifier for the Workspace the ResultQualifier belongs to. | UUID      |
| M        | code         | A brief text code identifying the ResultQualifier.                         | String    |
| M        | description  | A longer text description or explanation of the ResultQualifier.           | String    |


## Sensor

A Sensor is an instrument that observes a property or phenomenon with the goal of producing an estimate of the value of the property. 

| Required | Attribute         | Definition                                                                                | Data Type |
| -------- | ----------------- | ----------------------------------------------------------------------------------------- | --------- |
| M        | id                | A primary key unique identifier for the Sensor.                                           | UUID      |
| O        | workspace_id      | A foreign key identifier for the Workspace the Sensor belongs to.                         | UUID      |
| M        | name              | A descriptive name for the Sensor.                                                        | String    |
| M        | description       | A longer text description of the Sensor.                                                  | String    |
| M        | encoding_type     | A string indicating how the Sensor information is encoded by the API - "application/json" | String    |
| O        | manufacturer      | The name of the Sensor's manufacturer.                                                    | String    |
| O        | sensor_model      | The name of the Sensor model.                                                             | String    |
| O        | sensor_model_link | A URL linking to more information about the Sensor model.                                 | String    |
| M        | method_type       | A string indicating the type of Sensor or Method - preferably chosen from a controlled vocabulary (e.g., "Instrument deployment"). | String    |
| O        | method_link       | A URL pointing to a website that defines or describes the Sensor/Method.                  | String    |
| O        | method_code       | A brief text code identifying the Sensor/Method.                                          | String    |


## Unit

The unit of measure associated with the Observations within a Datastream.

| Required | Attribute    | Definition                                                                  | Data Type |
| -------- | ------------ | --------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the Unit.                               | UUID      |
| O        | workspace_id | A foreign key identifier for the Workspace the Unit belongs to.             | UUID      |
| M        | name         | A descriptive name for the Unit.                                            | String    |
| M        | symbol       | An abbreviation or symbol used for the unit.                                | String    |
| M        | definition   | A URL pointing to a website or controlled vocabulary that defines the Unit. | String    |
| M        | unit_type    | The type of Unit (e.g., Flow, Concentration, Volume, Length, Mass, etc.)    | String    |


## Datastream

A Datastream groups a collection of Observations measuring the same ObservedProperty and produced by the same Sensor. Each instance of a Datastream represents the properties for a time series of Observations.

| Required | Attribute                      | Definition                                                                                | Data Type         |
| -------- | ------------------------------ | ----------------------------------------------------------------------------------------- | ----------------- |
| M        | id                             | A primary key unique identifier for the Datastream.                                       | UUID              |
| M        | name                           | A text name for the datastream. Can be auto generated.                                    | String            |
| M        | description                    | A text description for the datastream. Can be auto generated.                             | Text              |
| M        | thing_id                       | Foreign key referencing the associated Thing.                                             | UUID              |
| M        | sensor_id                      | Foreign key referencing the Sensor that collected the data.                               | UUID              |
| M        | observed_property_id           | Foreign key referencing the ObservedProperty being measured.                              | UUID              |
| M        | processing_level_id            | Foreign key referencing the ProcessingLevel of the data.                                  | UUID              |
| M        | unit_id                        | Foreign key referencing the Unit of measurement.                                          | UUID              |
| M        | observation_type               | The type of Observation derived from a list of observation types - "Field Observation" or "Derived Value"  | String            |
| M        | result_type                    | The specific type of result represented by the Datastream. All time series are of type "Time series coverage". | String            |
| O        | status                         | A string value indicating the status of data collection/creation for the Datastream.      | String            |
| M        | sampled_medium                 | The environmental media that is sampled by the Datastream (e.g., air, water, snow, etc.). | String            |
| O        | value_count                    | Total number of recorded observations.                                                    | Integer           |
| M        | no_data_value                  | A numeric value stored to indicate the absence of data (e.g., -9999).                     | Float             |
| O        | intended_time_spacing          | Intended spacing between observations.                                                    | Float             |
| O        | intended_time_spacing_unit     | Unit for the intended time spacing.                                                       | String            |
| M        | aggregation_statistic          | Statistical method used to aggregate data (e.g., mean, max).                              | String            |
| M        | time_aggregation_interval      | Time interval over which aggregation occurs.                                              | Float             |
| M        | time_aggregation_interval_unit | Unit for the aggregation interval.                                                        | String            |
| O        | phenomenon_begin_time          | Timestamp of the earliest recorded phenomenon.                                            | DateTime          |
| O        | phenomenon_end_time            | Timestamp of the latest recorded phenomenon.                                              | DateTime          |
| M        | is_private                     | Whether the datastream is private.                                                        | Boolean           |
| M        | is_visible                     | Whether the datastream observations are visible in applications.                          | Boolean           |
| O        | data_source_id                 | Foreign key linking to the source from which data was obtained.                           | UUID              |


## Observation

An Observation is the act of measuring or otherwise determining the value of a property, including its numeric result and the date/time at which it was observed.

| Required | Attribute        | Definition                                                                    | Data Type |
| -------- | ---------------- | ----------------------------------------------------------------------------- | --------- |
| M        | id               | A unique identifier for the Observation.                                      | UUID      |
| M        | datastream_id    | A foreign key identifier for the Datastream to which the Observation belongs. | UUID      |
| M        | phenomenon_time  | The time when the observation occurred or was measured.                       | DateTime  |
| M        | result           | The measured or observed value.                                               | Float     |
| O        | result_time      | The time when the result was generated or recorded.                           | DateTime  |
| O        | quality_code     | A text code or string indicating the quality of the Observation.              | String    |


## OrchestrationSystem

An external system that manages and coordinates various processes or operations within a Workspace.

| Required | Attribute                 | Definition                                                                           | Data Type |
| -------- | ------------------------- | ------------------------------------------------------------------------------------ | --------- |
| M        | id                        | A unique identifier for the OrchestrationSystem.                                     | UUID      |
| O        | workspace_id              | A foreign key identifier for the Workspace to which the system belongs.              | UUID      |
| M        | name                      | The name of the OrchestrationSystem.                                                 | String    |
| M        | orchestration_system_type | The type or classification of the OrchestrationSystem (e.g., "SDL", "Airflow", etc). | String    |


## DataSource

Represents the source of data for one or more Datastreams, and is linked to an OrchestrationSystem and Workspace, containing configuration settings.

| Required | Attribute               | Definition                                                                      | Data Type |
| -------- | ----------------------- | ------------------------------------------------------------------------------- | --------- |
| M        | id                      | A primary key unique identifier for the DataSource.                             | UUID      |
| M        | workspace_id            | A foreign key referencing the Workspace to which the DataSource belongs.        | UUID      |
| M        | orchestration_system_id | A foreign key referencing the OrchestrationSystem that manages the data source. | UUID      |
| M        | name                    | The name of the data source.                                                    | String    |
| O        | settings                | A JSON field storing configuration settings for the data source.                | JSON      |
| O        | interval                | The time interval (in numerical form) between orchestration runs.               | Integer   |
| O        | interval_units          | The units for the interval (e.g., "hours", "days").                             | String    |
| O        | crontab                 | The cron expression specifying when the orchestration should run.               | String    |
| O        | start_time              | The time the orchestration should begin.                                        | DateTime  |
| O        | end_time                | The time the orchestration should end.                                          | DateTime  |
| O        | paused                  | A flag indicating whether the orchestration is paused.                          | Boolean   |
| O        | last_run_successful     | A flag indicating whether the last orchestration run was successful.            | Boolean   |
| O        | last_run_message        | A message about the last orchestration run (e.g., success or failure details).  | String    |
| O        | last_run                | The timestamp of when the last orchestration run occurred.                      | DateTime  |
| O        | next_run                | The timestamp of the next scheduled orchestration run.                          | DateTime  |



## DataArchive

Represents an external location one or more Datastreams is archived or exported to, and is linked to an OrchestrationSystem and Workspace, containing configuration settings.

| Required | Attribute               | Definition                                                                       | Data Type |
| -------- | ----------------------- | -------------------------------------------------------------------------------- | --------- |
| M        | id                      | A primary key unique identifier for the DataArchive.                             | UUID      |
| M        | workspace_id            | A foreign key referencing the Workspace to which the DataArchive belongs.        | UUID      |
| M        | orchestration_system_id | A foreign key referencing the OrchestrationSystem that manages the data archive. | UUID      |
| M        | name                    | The name of the data archive.                                                    | String    |
| O        | settings                | A JSON field storing configuration settings for the data archive.                | JSON      |
| O        | interval                | The time interval (in numerical form) between orchestration runs.                | Integer   |
| O        | interval_units          | The units for the interval (e.g., "hours", "days").                              | String    |
| O        | crontab                 | The cron expression specifying when the orchestration should run.                | String    |
| O        | start_time              | The time the orchestration should begin.                                         | DateTime  |
| O        | end_time                | The time the orchestration should end.                                           | DateTime  |
| O        | paused                  | A flag indicating whether the orchestration is paused.                           | Boolean   |
| O        | last_run_successful     | A flag indicating whether the last orchestration run was successful.             | Boolean   |
| O        | last_run_message        | A message about the last orchestration run (e.g., success or failure details).   | String    |
| O        | last_run                | The timestamp of when the last orchestration run occurred.                       | DateTime  |
| O        | next_run                | The timestamp of the next scheduled orchestration run.                           | DateTime  |
