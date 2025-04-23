# HydroServer Data Model Data Dictionary

This document describes the entities and attributes within the HydroServer data model. 


## User

A registered HydroServer user with identifying details and access metadata.

| Required | Attribute            | Definition                                                                 | Data Type     |
| -------- | -------------------- | -------------------------------------------------------------------------- | ------------- |
| M        | id                   | A primary key unique identifier for the User.                              | Integer       |
| M        | email                | A unique email address identifying the User.                               | String        |
| M        | firstName            | The User’s first name.                                                     | String        |
| M        | lastName             | The User’s last name.                                                      | String        |
| O        | middleName           | The User’s middle name.                                                    | String        |
| O        | phone                | A contact phone number for the User.                                       | String        |
| O        | address              | The User’s mailing or physical address.                                    | String        |
| O        | link                 | A URL associated with the User (e.g., profile or homepage).                | URL           |
| M        | userType             | A descriptor for the type or role of the User.                             | String        |
| O        | organizationId       | A reference to the Organization the User is affiliated with.               | Integer       |
| M        | isOwnershipAllowed   | Indicates whether the User is allowed to own Workspaces.                   | Boolean       |
| M        | isSuperuser          | Indicates whether the User is a superuser (admin).                         | Boolean       |
| M        | isStaff              | Indicates whether the User has a staff account.                            | Boolean       |
| M        | isActive             | Indicates whether the User's account is active.                            | Boolean       |
| M        | dateJoined           | The date and time the User created their HydroServer account.              | DateTime      |
| M        | lastLogin            | The date and time of the User's last login.                                | DateTime      |


## Organization

An entity such as an institution, agency, or company that is associated with a User.

| Required | Attribute         | Definition                                                                   | Data Type |
| -------- | ----------------- | ---------------------------------------------------------------------------- | --------- |
| M        | id                | A primary key unique identifier for the Organization.                        | Integer   |
| M        | code              | A short, unique code identifying the Organization.                           | String    |
| M        | name              | The full name of the Organization.                                           | String    |
| O        | description       | A brief textual description of the Organization.                             | String    |
| O        | link              | A URL linking to the Organization’s homepage or relevant web presence.       | URL       |
| M        | type              | A classification or descriptor of the Organization (e.g., university, NGO).  | String    |


## Workspace

Workspaces in HydroServer are used to organize and manage access to user-managed data. All user-managed resources in HydroServer are created within the context of a workspace. Each workspace has one owner and can have any number of collaborators with varying levels of access to resources within the workspace.


| Required | Attribute   | Definition                                                                 | Data Type |
| -------- | ----------- | -------------------------------------------------------------------------- | --------- |
| M        | id          | A primary key unique identifier for the Workspace.                         | UUID      |
| M        | name        | A name for the Workspace.                                                  | String    |
| M        | ownerId     | A foreign key identifier for the User who owns the Workspace.              | Integer   |
| M        | isPrivate   | A boolean indicating whether the Workspace is private or publicly visible. | Boolean   |


## Role

A set of permissions or access level definitions assigned to collaborators within a Workspace. HydroServer's default roles are 'Viewer' and 'Editor'.

| Required | Attribute    | Definition                                                                 | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the Role.                              | UUID      |
| O        | workspaceId  | A foreign key identifier for the Workspace to which the Role belongs.      | UUID      |
| M        | name         | A name for the Role.                                                       | String    |
| O        | description  | A text description of the Role.                                            | String    |


## Permission

Defines a specific permission granted to a Role for a particular type of resource.

| Required | Attribute       | Definition                                                                     | Data Type |
| -------- | --------------- | ------------------------------------------------------------------------------ | --------- |
| M        | roleId          | A foreign key identifier for the Role to which this permission belongs.        | UUID      |
| M        | permissionType  | The type of permission (e.g., view, create, etc) granted to the Role.          | String    |
| M        | resourceType    | The type of resource the permission applies to (e.g., Datastream, Thing, etc). | String    |


## Collaborator

Associates a User with a Role in a specific Workspace.

| Required | Attribute    | Definition                                                                   | Data Type |
| -------- | ------------ | ---------------------------------------------------------------------------- | --------- |
| M        | workspaceId  | A foreign key identifier for the Workspace the user collaborates on.         | UUID      |
| M        | userId       | A foreign key identifier for the User who is a collaborator.                 | Integer   |
| M        | roleId       | A foreign key identifier for the Role assigned to the User in the Workspace. | UUID      |


## Thing

A thing is an object of the physical world (physical things) or the information world (virtual things) that is capable of being identified and integrated into communication networks. In the context of environmental monitoring and HydroServer, a Thing is a monitoring station or "Site" (e.g., a streamflow gage, water quality station, weather station, diversion measurement location, etc.).

| Required | Attribute              | Definition                                                                 | Data Type |
| -------- | ---------------------- | -------------------------------------------------------------------------- | --------- |
| M        | id                     | A primary key unique identifier for the Thing.                             | UUID      |
| M        | workspaceId            | A foreign key identifier for the Workspace that the Thing belongs to.      | UUID      |
| M        | name                   | A text string giving a name for the Thing.                                 | String    |
| M        | description            | A text string giving a description for the Thing.                          | String    |
| M        | samplingFeatureType    | A text string specifying the type of sampling feature - usually "Site".    | String    |
| M        | samplingFeatureCode    | A text string specifying a shortened code identifying the Thing.           | String    |
| M        | siteType               | A text string specifying the type of Site represented by the Thing - e.g., "Streamflow Gage", "Water Quality Station", "Weather Station", "Diversion Station", etc. | String    |
| O        | isPrivate              | Indicates whether the Thing is private to the owning Workspace.            | Boolean   |
| O        | dataDisclaimer         | A text string displayed on the HydroServer landing page for the Thing (Site) that specifies a data disclaimer for data at that site. | String    |


## Location

The Location entity locates the Thing. A Thing’s Location entity is defined as the last known location of the Thing. In the context of Things that are monitoring sites, this is the physical location of the monitoring site.

| Required | Attribute        | Definition                                                                                  | Data Type |
| -------- | ---------------- | ------------------------------------------------------------------------------------------- | --------- |
| M        | id               | A primary key unique identifier for the Location.                                           | UUID      |
| M        | thingId          | A foreign key identifier for the Thing to which this Location belongs.                      | UUID      |
| M        | name             | A text string name for the Location. Can be the same as the name of the Thing.              | String    |
| M        | description      | A text string description of the Location.                                                  | String    |
| M        | encodingType     | The encoding type of the Location - usually "GeoJSON".                                      | String    |
| M        | latitude         | A floating point number representing the latitude of the location using WGS84 coordinates.  | Decimal   |
| M        | longitude        | A floating point number representing the longitude of the location using WGS84 coordinates. | Decimal   |
| O        | elevation_m      | A floating point number representing the elevation of the location in meters.               | Decimal   |
| O        | elevationDatum   | A string indicating the elevation datum used by the site to specify the elevation.          | String    |
| O        | state            | The state in which the Location resides.                                                    | String    |
| O        | county           | The county in which the Location resides.                                                   | String    |
| O        | country          | The ISO 3166-1 alpha-2 country code (e.g., "US").                                           | String    |


## Tag

A key-value metadata pair associated with a Thing, used to provide additional descriptive or categorical information.

| Required | Attribute | Definition                                                          | Data Type |
| -------- | --------- | ------------------------------------------------------------------- | --------- |
| M        | thingId   | A foreign key identifier for the Thing to which the tag applies.    | UUID      |
| M        | key       | The tag key or name.                                                | String    |
| M        | value     | The tag value associated with the key.                              | String    |


## Photo

A photo of a Thing - e.g., photos of a monitoring site/location.

| Required | Attribute | Definition                                                                 | Data Type |
| -------- | --------- | -------------------------------------------------------------------------- | --------- |
| M        | thingId   | A foreign key identifier for the Thing to which the photo is linked.       | UUID      |
| M        | name      | A descriptive name for the photo.                                          | String    |
| M        | photo     | A file path reference to the uploaded photo file.                          | String    |


## ObservedProperty

An ObservedProperty specifies the phenomenon of an Observation (e.g., flow, temperature, pH, dissolved oxygen concentration, etc.).

| Required | Attribute             | Definition                                                                                             | Data Type |
| -------- | --------------------- | ------------------------------------------------------------------------------------------------------ | --------- |
| M        | id                    | A primary key unique identifier for the ObservedProperty.                                              | UUID      |
| O        | workspaceId           | A foreign key identifier for the Workspace the ObservedProperty belongs to.                            | UUID      |
| M        | name                  | A descriptive name for the ObservedProperty - preferably chosen from a controlled vocabulary.          | String    |
| M        | definition            | A text string providing a definition of the ObservedProperty or a URL pointing to a definition of the ObservedProperty - e.g., a URL pointing to the controlled vocabulary that defines the observed property. | String    |
| M        | description           | A text description of the ObservedProperty. May be the same as the definition of the ObservedProperty. | String    |
| M        | observedPropertyType  | The type of ObservedProperty - preferably selected from a controlled vocabulary (e.g., Hydrology, Instrumentation, Climate, Soil, Water Quality, etc.). | String    |
| M        | code                  | A brief text code identifying the ObservedProperty.                                                    | String    |


## ProcessingLevel

The degree of quality control or processing to which a Datastream has been subjected. For example, raw versus quality controlled data.

| Required | Attribute    | Definition                                                                                                        | Data Type |
| -------- | ------------ | ----------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the ProcessingLevel.                                                          | UUID      |
| O        | workspaceId  | A foreign key identifier for the Workspace the ProcessingLevel belongs to.                                        | UUID      |
| M        | code         | A brief text code identifying the Processing level - e.g., "0" for "Raw data", "1" for "Quality controlled data." | String    |
| O        | definition   | A text definition of the ProcessingLevel.                                                                         | String    |
| O        | explanation  | A longer text explanation of the ProcessingLevel.                                                                 | String    |


## ResultQualifier

Data qualifying comments added to individual data values to qualify their interpretation or use.

| Required | Attribute    | Definition                                                                 | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the ResultQualifier.                   | UUID      |
| O        | workspaceId  | A foreign key identifier for the Workspace the ResultQualifier belongs to. | UUID      |
| M        | code         | A brief text code identifying the ResultQualifier.                         | String    |
| M        | description  | A longer text description or explanation of the ResultQualifier.           | String    |


## Sensor

A Sensor is an instrument that observes a property or phenomenon with the goal of producing an estimate of the value of the property. 

| Required | Attribute         | Definition                                                                                | Data Type |
| -------- | ----------------- | ----------------------------------------------------------------------------------------- | --------- |
| M        | id                | A primary key unique identifier for the Sensor.                                           | UUID      |
| O        | workspaceId       | A foreign key identifier for the Workspace the Sensor belongs to.                         | UUID      |
| M        | name              | A descriptive name for the Sensor.                                                        | String    |
| M        | description       | A longer text description of the Sensor.                                                  | String    |
| M        | encodingType      | A string indicating how the Sensor information is encoded by the API - "application/json" | String    |
| O        | manufacturer      | The name of the Sensor's manufacturer.                                                    | String    |
| O        | model             | The name of the Sensor model.                                                             | String    |
| O        | modelLink         | A URL linking to more information about the Sensor model.                                 | String    |
| M        | methodType        | A string indicating the type of Sensor or Method - preferably chosen from a controlled vocabulary (e.g., "Instrument deployment"). | String    |
| O        | methodLink        | A URL pointing to a website that defines or describes the Sensor/Method.                  | String    |
| O        | methodCode        | A brief text code identifying the Sensor/Method.                                          | String    |


## Unit

The unit of measure associated with the Observations within a Datastream.

| Required | Attribute    | Definition                                                                  | Data Type |
| -------- | ------------ | --------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the Unit.                               | UUID      |
| O        | workspaceId  | A foreign key identifier for the Workspace the Unit belongs to.             | UUID      |
| M        | name         | A descriptive name for the Unit.                                            | String    |
| M        | symbol       | An abbreviation or symbol used for the unit.                                | String    |
| M        | definition   | A URL pointing to a website or controlled vocabulary that defines the Unit. | String    |
| M        | unitType     | The type of Unit (e.g., Flow, Concentration, Volume, Length, Mass, etc.)    | String    |


## Datastream

A Datastream groups a collection of Observations measuring the same ObservedProperty and produced by the same Sensor. Each instance of a Datastream represents the properties for a time series of Observations.

| Required | Attribute                      | Definition                                                                                | Data Type         |
| -------- | ------------------------------ | ----------------------------------------------------------------------------------------- | ----------------- |
| M        | id                             | A primary key unique identifier for the Datastream.                                       | UUID              |
| M        | name                           | A text name for the datastream. Can be auto generated.                                    | String            |
| M        | description                    | A text description for the datastream. Can be auto generated.                             | Text              |
| M        | thingId                        | Foreign key referencing the associated Thing.                                             | UUID              |
| M        | sensor_id                      | Foreign key referencing the Sensor that collected the data.                               | UUID              |
| M        | observedPropertyId             | Foreign key referencing the ObservedProperty being measured.                              | UUID              |
| M        | processingLevelId              | Foreign key referencing the ProcessingLevel of the data.                                  | UUID              |
| M        | unitId                         | Foreign key referencing the Unit of measurement.                                          | UUID              |
| M        | observationType                | The type of Observation derived from a list of observation types - "Field Observation" or "Derived Value"  | String            |
| M        | resultType                     | The specific type of result represented by the Datastream. All time series are of type "Time series coverage". | String            |
| O        | status                         | A string value indicating the status of data collection/creation for the Datastream.      | String            |
| M        | sampledMedium                  | The environmental media that is sampled by the Datastream (e.g., air, water, snow, etc.). | String            |
| O        | valueCount                     | Total number of recorded observations.                                                    | Integer           |
| M        | noDataValue                    | A numeric value stored to indicate the absence of data (e.g., -9999).                     | Float             |
| O        | intendedTimeSpacing            | Intended spacing between observations.                                                    | Float             |
| O        | intendedTimeSpacingUnit        | Unit for the intended time spacing.                                                       | String            |
| M        | aggregationStatistic           | Statistical method used to aggregate data (e.g., mean, max).                              | String            |
| M        | timeAggregationInterval        | Time interval over which aggregation occurs.                                              | Float             |
| M        | timeAggregationIntervalUnit    | Unit for the aggregation interval.                                                        | String            |
| O        | phenomenonBeginTime            | Timestamp of the earliest recorded phenomenon.                                            | DateTime          |
| O        | phenomenonEndTime              | Timestamp of the latest recorded phenomenon.                                              | DateTime          |
| M        | isPrivate                      | Whether the datastream is private.                                                        | Boolean           |
| M        | isVisible                      | Whether the datastream observations are visible in applications.                          | Boolean           |
| O        | dataSourceId                   | Foreign key linking to the source from which data was obtained.                           | UUID              |


## Observation

An Observation is the act of measuring or otherwise determining the value of a property, including its numeric result and the date/time at which it was observed.

| Required | Attribute        | Definition                                                                    | Data Type |
| -------- | ---------------- | ----------------------------------------------------------------------------- | --------- |
| M        | id               | A unique identifier for the Observation.                                      | UUID      |
| M        | datastreamId     | A foreign key identifier for the Datastream to which the Observation belongs. | UUID      |
| M        | phenomenonTime   | The time when the observation occurred or was measured.                       | DateTime  |
| M        | result           | The measured or observed value.                                               | Float     |
| O        | resultTime       | The time when the result was generated or recorded.                           | DateTime  |
| O        | qualityCode      | A text code or string indicating the quality of the Observation.              | String    |


## OrchestrationSystem

An external system that manages and coordinates various processes or operations within a Workspace.

| Required | Attribute                 | Definition                                                                           | Data Type |
| -------- | ------------------------- | ------------------------------------------------------------------------------------ | --------- |
| M        | id                        | A unique identifier for the OrchestrationSystem.                                     | UUID      |
| O        | workspaceId               | A foreign key identifier for the Workspace to which the system belongs.              | UUID      |
| M        | name                      | The name of the OrchestrationSystem.                                                 | String    |
| M        | type                      | The type or classification of the OrchestrationSystem (e.g., "SDL", "Airflow", etc). | String    |


## DataSource

Represents the source of data for one or more Datastreams, and is linked to an OrchestrationSystem and Workspace, containing configuration settings.

| Required | Attribute               | Definition                                                                      | Data Type |
| -------- | ----------------------- | ------------------------------------------------------------------------------- | --------- |
| M        | id                      | A primary key unique identifier for the DataSource.                             | UUID      |
| M        | workspaceId             | A foreign key referencing the Workspace to which the DataSource belongs.        | UUID      |
| M        | orchestrationSystemId   | A foreign key referencing the OrchestrationSystem that manages the data source. | UUID      |
| M        | name                    | The name of the data source.                                                    | String    |
| O        | settings                | A JSON field storing configuration settings for the data source.                | JSON      |
| O        | interval                | The time interval (in numerical form) between orchestration runs.               | Integer   |
| O        | intervalUnits           | The units for the interval (e.g., "hours", "days").                             | String    |
| O        | crontab                 | The cron expression specifying when the orchestration should run.               | String    |
| O        | startTime               | The time the orchestration should begin.                                        | DateTime  |
| O        | endTime                 | The time the orchestration should end.                                          | DateTime  |
| O        | paused                  | A flag indicating whether the orchestration is paused.                          | Boolean   |
| O        | lastRunSuccessful       | A flag indicating whether the last orchestration run was successful.            | Boolean   |
| O        | lastRunMessage          | A message about the last orchestration run (e.g., success or failure details).  | String    |
| O        | lastRun                 | The timestamp of when the last orchestration run occurred.                      | DateTime  |
| O        | nextRun                 | The timestamp of the next scheduled orchestration run.                          | DateTime  |



## DataArchive

Represents an external location one or more Datastreams is archived or exported to, and is linked to an OrchestrationSystem and Workspace, containing configuration settings.

| Required | Attribute               | Definition                                                                       | Data Type |
| -------- | ----------------------- | -------------------------------------------------------------------------------- | --------- |
| M        | id                      | A primary key unique identifier for the DataArchive.                             | UUID      |
| M        | workspaceId             | A foreign key referencing the Workspace to which the DataArchive belongs.        | UUID      |
| M        | orchestrationSystemId   | A foreign key referencing the OrchestrationSystem that manages the data archive. | UUID      |
| M        | name                    | The name of the data archive.                                                    | String    |
| O        | settings                | A JSON field storing configuration settings for the data archive.                | JSON      |
| O        | interval                | The time interval (in numerical form) between orchestration runs.                | Integer   |
| O        | intervalUnits           | The units for the interval (e.g., "hours", "days").                              | String    |
| O        | crontab                 | The cron expression specifying when the orchestration should run.                | String    |
| O        | startTime               | The time the orchestration should begin.                                         | DateTime  |
| O        | endTime                 | The time the orchestration should end.                                           | DateTime  |
| O        | paused                  | A flag indicating whether the orchestration is paused.                           | Boolean   |
| O        | lastRunSuccessful       | A flag indicating whether the last orchestration run was successful.             | Boolean   |
| O        | lastRunMessage          | A message about the last orchestration run (e.g., success or failure details).   | String    |
| O        | lastRun                 | The timestamp of when the last orchestration run occurred.                       | DateTime  |
| O        | nextRun                 | The timestamp of the next scheduled orchestration run.                           | DateTime  |
