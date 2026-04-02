# HydroServer Data Model Data Dictionary

This document describes the entities and attributes within the HydroServer data model.

M = Mandatory
O = Optional

## Datastream

A Datastream groups a collection of Observations measuring the same ObservedProperty and produced by the same Sensor. Each instance of a Datastream represents the properties for a time series of Observations.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Datastream. | UUID |
| M | name | A text name for the Datastream. | String |
| M | description | A text description for the Datastream. | String |
| M | sensorId | A foreign key identifier for the Sensor or method used to create the Datastream. | UUID |
| M | thingId | A foreign key identifier for the Thing on which or at which the Datastream was created. | UUID |
| M | observedPropertyId | A foreign key identifier for the ObservedProperty associated with the Datastream. | UUID |
| M | unitId | A foreign key identifier for the Unit used for Observations within the Datastream. | UUID |
| M | processingLevelId | A foreign key identifier indicating the ProcessingLevel for the Datastream. | UUID |
| M | observationType | The type of Observation recorded in the Datastream. | String |
| M | resultType | The type of result represented by the Datastream. | String |
| O | status | A text value indicating the status of the Datastream. | String |
| O | observedArea | The spatial extent associated with the Datastream. This field exists in the database but is not currently used by the main API. | String |
| M | sampledMedium | The environmental medium sampled by the Datastream. | String |
| O | valueCount | The number of Observations within the Datastream. | Integer |
| M | noDataValue | A numeric value used to indicate the absence of data. | Float |
| O | intendedTimeSpacing | A numeric value indicating the intended spacing between Observations. | Float |
| O | intendedTimeSpacingUnit | A string indicating the unit for `intendedTimeSpacing`. | String |
| M | aggregationStatistic | A text string indicating the aggregation statistic for the Datastream. | String |
| M | timeAggregationInterval | A numeric value indicating the time interval over which recorded Observations were aggregated. | Float |
| M | timeAggregationIntervalUnit | A string indicating the unit for `timeAggregationInterval`. | String |
| O | phenomenonBeginTime | The time at which the activity began that results in the Datastream's Observations. | Datetime |
| O | phenomenonEndTime | The time at which the activity ended that results in the Datastream's Observations. | Datetime |
| O | resultBeginTime | The timestamp of the first Observation in the Datastream. This field remains in the model but is currently unused. | Datetime |
| O | resultEndTime | The timestamp of the last Observation in the Datastream. This field remains in the model but is currently unused. | Datetime |
| M | isPrivate | An access control flag indicating whether the Datastream metadata and data are private by default. | Boolean |
| M | isVisible | An access control flag indicating whether the Datastream should be shown in normal data-discovery responses. | Boolean |

## Location

The Location entity stores the location of a Thing. In the context of Things that are monitoring sites, this is the physical location of the monitoring site.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Location. | UUID |
| M | thingId | A foreign key identifier for the Thing to which the Location belongs. | UUID |
| M | name | A text string name for the Location. | String |
| M | description | A text string description for the Location. | String |
| M | encodingType | The encoding type of the Location, usually `application/vnd.geo+json`. | String |
| M | latitude | The latitude of the Location using WGS84 coordinates. | Float |
| M | longitude | The longitude of the Location using WGS84 coordinates. | Float |
| O | elevationM | The elevation of the Location in meters. | Float |
| O | elevationDatum | A text string indicating the elevation datum used for the Location. | String |
| O | adminArea1 | A text string indicating the first-level administrative area for the Location. | String |
| O | adminArea2 | A text string indicating the second-level administrative area for the Location. | String |
| O | country | A two-character ISO country code for the Location. | String |

**NOTE**: The database allows a Thing to have multiple Location rows, but the current Data Management API treats Location as a single nested object on a Thing.

## Observation

An Observation is the act of measuring or otherwise determining the value of a property, including its numeric result and the date/time at which it was observed.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Observation. | UUID |
| M | datastreamId | A foreign key identifier for the Datastream to which the Observation belongs. | UUID |
| M | phenomenonTime | A datetime value indicating the time instant when the Observation happened. | Datetime |
| M | result | The numeric value of the Observation. | Float |
| O | resultTime | The time that the Observation's result was generated, if different from `phenomenonTime`. | Datetime |
| O | qualityCode | A text code indicating the quality of the Observation. | String |
| O | resultQualifiers | An array containing the identifiers of any ResultQualifiers applied to the Observation. | Array |

**NOTE**: `qualityCode` is persisted in the database, but the current Data Management API does not include it in the main observation schema.

## ObservedProperty

An ObservedProperty specifies the phenomenon of an Observation, such as flow, temperature, pH, or dissolved oxygen concentration.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the ObservedProperty. | UUID |
| O | workspaceId | A foreign key identifier for the Workspace that owns the ObservedProperty. If omitted, the ObservedProperty is shared system-wide. | UUID |
| M | name | A descriptive name for the ObservedProperty. | String |
| M | definition | A text definition of the ObservedProperty or a URL pointing to a controlled definition. | URL |
| M | description | A text description of the ObservedProperty. | String |
| M | type | The type of ObservedProperty. | String |
| M | code | A brief text code identifying the ObservedProperty. | String |

## Organization

An Organization is a body of people having a particular purpose, such as a business, agency, research group, or laboratory.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Organization. | Integer |
| M | code | A brief text code or abbreviation for the Organization. | String |
| M | name | A descriptive name for the Organization. | String |
| O | description | A text description of the Organization. | String |
| O | link | A URL pointing to a website for the Organization. | URL |
| M | type | A text string indicating the type of Organization. | String |

## User

Individual users who own workspaces, collaborate on data management, or manage account information in HydroServer.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the User. | Integer |
| M | firstName | The User's first name. | String |
| O | middleName | The User's middle name. | String |
| M | lastName | The User's last name. | String |
| M | email | The User's contact email address. | String |
| O | phone | The User's contact phone number. | String |
| O | address | The User's physical mailing address. | String |
| O | link | A URL pointing to a website for the User. | URL |
| M | type | A text string indicating the type of User. | String |
| O | organizationId | A foreign key identifier for the Organization with which the User is affiliated. | Integer |
| M | isOwnershipAllowed | A boolean value indicating whether the User may own workspaces. | Boolean |

## ProcessingLevel

The degree of quality control or processing to which a Datastream has been subjected.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the ProcessingLevel. | UUID |
| O | workspaceId | A foreign key identifier for the Workspace that owns the ProcessingLevel. If omitted, the ProcessingLevel is shared system-wide. | UUID |
| M | code | A brief text code identifying the ProcessingLevel. | String |
| O | definition | A text definition of the ProcessingLevel. | String |
| O | explanation | A longer text explanation of the ProcessingLevel. | String |

## ResultQualifier

Data qualifying comments added to individual data values to qualify their interpretation or use.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the ResultQualifier. | UUID |
| O | workspaceId | A foreign key identifier for the Workspace that owns the ResultQualifier. If omitted, the ResultQualifier is shared system-wide. | UUID |
| M | code | A brief text code identifying the ResultQualifier. | String |
| M | description | A longer text description or explanation of the ResultQualifier. | String |

## Sensor

A Sensor is an instrument, method, or procedure used to produce Observations for a Datastream.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Sensor. | UUID |
| O | workspaceId | A foreign key identifier for the Workspace that owns the Sensor. If omitted, the Sensor is shared system-wide. | UUID |
| M | name | A descriptive name for the Sensor. | String |
| M | description | A longer text description of the Sensor. | String |
| M | encodingType | A string indicating how the Sensor information is encoded. | String |
| O | methodCode | A brief text code identifying the Sensor or method. | String |
| M | methodType | A text string indicating the type of Sensor or method. | String |
| O | methodLink | A URL pointing to documentation that defines or describes the Sensor or method. | URL |
| O | manufacturer | The name of the Sensor manufacturer. | String |
| O | model | The name of the Sensor model. | String |
| O | modelLink | A URL pointing to documentation for the Sensor model. | URL |

**NOTE**: HydroServer uses the Sensor entity for both physical instruments and derived methods or procedures, such as transformations or rating-curve-derived values.

## Thing

A Thing is an object of the physical world or information world that is capable of being identified and integrated into communication networks. In the context of HydroServer, a Thing is typically a monitoring station or site.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Thing. | UUID |
| M | workspaceId | A foreign key identifier for the Workspace that owns the Thing. | UUID |
| M | name | A text string giving a name for the Thing. | String |
| M | description | A text string giving a description for the Thing. | String |
| M | samplingFeatureType | A text string specifying the type of sampling feature. | String |
| M | samplingFeatureCode | A text string specifying a shortened code identifying the Thing. | String |
| M | siteType | A text string specifying the type of site represented by the Thing. | String |
| M | isPrivate | An access control flag indicating whether the Thing is discoverable and whether its metadata is publicly available. | Boolean |
| O | dataDisclaimer | A text string displayed with the Thing's data to specify any disclaimer. | String |

## ThingTag

A key-value tag associated with a Thing.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the ThingTag. | Integer |
| M | thingId | A foreign key identifier for the Thing to which the tag belongs. | UUID |
| M | key | The tag key. | String |
| M | value | The tag value. | String |

## ThingFileAttachment

A file attached to a Thing, such as a site photo, document, or supporting artifact.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the ThingFileAttachment. | Integer |
| M | thingId | A foreign key identifier for the Thing to which the file attachment belongs. | UUID |
| M | name | The name of the attached file. | String |
| O | description | A text description of the attached file. | String |
| M | fileAttachment | The stored file object for the attachment. | File |
| M | fileAttachmentType | A text string identifying the type of file attachment. | String |

## Unit

The unit of measure associated with the Observations within a Datastream.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Unit. | UUID |
| O | workspaceId | A foreign key identifier for the Workspace that owns the Unit. If omitted, the Unit is shared system-wide. | UUID |
| M | name | A descriptive name for the Unit. | String |
| M | symbol | An abbreviation or symbol used for the Unit. | String |
| M | definition | A URL or text definition for the Unit. | URL |
| M | type | The type of Unit. | String |

## Workspace

A Workspace is the ownership and access-control boundary for most HydroServer-managed resources.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Workspace. | UUID |
| M | name | A descriptive name for the Workspace. | String |
| M | ownerId | A foreign key identifier for the User who owns the Workspace. | Integer |
| M | isPrivate | An access control flag indicating whether the Workspace is private. | Boolean |

## WorkspaceTransferConfirmation

A pending transfer record used when ownership of a Workspace is being transferred to another User.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the WorkspaceTransferConfirmation. | Integer |
| M | workspaceId | A foreign key identifier for the Workspace being transferred. | UUID |
| M | newOwnerId | A foreign key identifier for the new owner. | Integer |
| M | initiated | The datetime when the transfer was initiated. | Datetime |

## WorkspaceDeleteConfirmation

A pending confirmation record used when a Workspace deletion has been initiated.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the WorkspaceDeleteConfirmation. | Integer |
| M | workspaceId | A foreign key identifier for the Workspace to be deleted. | UUID |
| M | initiated | The datetime when deletion confirmation was initiated. | Datetime |

## Role

A Role is a named collection of permissions that can be assigned to collaborators or API keys.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Role. | UUID |
| O | workspaceId | A foreign key identifier for the Workspace that owns the Role. If omitted, the Role is shared system-wide. | UUID |
| M | name | A descriptive name for the Role. | String |
| O | description | A text description of the Role. | String |
| M | isUserRole | A boolean value indicating whether the Role may be assigned to a User collaborator. | Boolean |
| M | isAPIKeyRole | A boolean value indicating whether the Role may be assigned to an API key. | Boolean |

## Permission

A Permission associates a Role with an allowed action on a resource type.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Permission. | Integer |
| M | roleId | A foreign key identifier for the Role to which the Permission belongs. | UUID |
| M | permissionType | The permitted action, such as `view`, `create`, `edit`, `delete`, or `*`. | String |
| M | resourceType | The resource type to which the Permission applies. | String |

## Collaborator

A Collaborator associates a User with a Workspace through a Role.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Collaborator. | Integer |
| M | workspaceId | A foreign key identifier for the Workspace. | UUID |
| M | userId | A foreign key identifier for the collaborating User. | Integer |
| M | roleId | A foreign key identifier for the Role assigned to the Collaborator. | UUID |

## APIKey

An APIKey grants non-interactive access to a Workspace using an assigned Role.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the APIKey. | UUID |
| M | workspaceId | A foreign key identifier for the Workspace to which the API key belongs. | UUID |
| M | roleId | A foreign key identifier for the Role assigned to the API key. | UUID |
| M | name | A descriptive name for the API key. | String |
| O | description | A text description of the API key. | String |
| M | createdAt | The datetime when the API key was created. | Datetime |
| O | expiresAt | The datetime when the API key expires. | Datetime |
| O | lastUsed | The datetime when the API key was last used. | Datetime |
| M | isActive | A boolean value indicating whether the API key is active. | Boolean |
| M | hashedKey | The stored hashed representation of the API key secret. | String |

## DatastreamTag

A key-value tag associated with a Datastream.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the DatastreamTag. | Integer |
| M | datastreamId | A foreign key identifier for the Datastream to which the tag belongs. | UUID |
| M | key | The tag key. | String |
| M | value | The tag value. | String |

## DatastreamFileAttachment

A file attached to a Datastream.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the DatastreamFileAttachment. | Integer |
| M | datastreamId | A foreign key identifier for the Datastream to which the file attachment belongs. | UUID |
| M | name | The name of the attached file. | String |
| O | description | A text description of the attached file. | String |
| M | fileAttachment | The stored file object for the attachment. | File |
| M | fileAttachmentType | A text string identifying the type of file attachment. | String |

## OrchestrationSystem

An OrchestrationSystem identifies the engine or environment used to run automated HydroServer tasks.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the OrchestrationSystem. | UUID |
| O | workspaceId | A foreign key identifier for the Workspace that owns the OrchestrationSystem. If omitted, the OrchestrationSystem is shared system-wide. | UUID |
| M | name | A descriptive name for the OrchestrationSystem. | String |
| M | type | A text string indicating the type of orchestration system. | String |

## DataConnection

A DataConnection stores the extraction, transformation, and loading configuration used by HydroServer ETL tasks.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the DataConnection. | UUID |
| M | name | A descriptive name for the DataConnection. | String |
| M | type | A text string indicating the type of DataConnection. | String |
| O | workspaceId | A foreign key identifier for the Workspace that owns the DataConnection. If omitted, the DataConnection is shared system-wide. | UUID |
| O | extractorType | The type of extractor configured for the DataConnection. | String |
| M | extractorSettings | A JSON object storing extractor configuration settings. | Object |
| O | transformerType | The type of transformer configured for the DataConnection. | String |
| M | transformerSettings | A JSON object storing transformer configuration settings. | Object |
| O | loaderType | The type of loader configured for the DataConnection. | String |
| M | loaderSettings | A JSON object storing loader configuration settings. | Object |

## DataConnectionNotificationRecipient

A notification email recipient associated with a DataConnection.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the DataConnectionNotificationRecipient. | Integer |
| M | dataConnectionId | A foreign key identifier for the DataConnection. | UUID |
| M | email | An email address that receives notifications for the DataConnection. | String |

## Task

A Task defines an automated HydroServer workflow, including the associated DataConnection, orchestration target, schedule, and runtime variables.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Task. | UUID |
| M | name | A descriptive name for the Task. | String |
| M | type | A text string indicating the Task type. Current values include `ETL` and `Aggregation`. | String |
| M | workspaceId | A foreign key identifier for the Workspace that owns the Task. | UUID |
| O | dataConnectionId | A foreign key identifier for the DataConnection used by the Task. | UUID |
| M | orchestrationSystemId | A foreign key identifier for the OrchestrationSystem used by the Task. | UUID |
| O | periodicTaskId | A foreign key identifier for the associated scheduler record in `django_celery_beat`. | Integer |
| M | paused | A boolean value indicating whether the Task is paused. | Boolean |
| O | nextRunAt | The datetime when the Task is expected to run next. | Datetime |
| M | extractorVariables | A JSON object storing runtime variables for the extractor. | Object |
| M | transformerVariables | A JSON object storing runtime variables for the transformer. | Object |
| M | loaderVariables | A JSON object storing runtime variables for the loader. | Object |

## TaskMapping

A TaskMapping associates an incoming source identifier with one or more target mapping paths.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the TaskMapping. | UUID |
| M | taskId | A foreign key identifier for the Task to which the mapping belongs. | UUID |
| M | sourceIdentifier | A text identifier representing an incoming source field or path. | String |

## TaskMappingPath

A TaskMappingPath maps a source identifier to a target identifier and any configured transformations.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the TaskMappingPath. | UUID |
| M | taskMappingId | A foreign key identifier for the TaskMapping to which the path belongs. | UUID |
| M | targetIdentifier | A text identifier representing the destination field or path. | String |
| M | dataTransformations | An array of transformation definitions applied along the mapping path. | Array |

## TaskRun

A TaskRun stores the execution history for a Task.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the TaskRun. | UUID |
| M | taskId | A foreign key identifier for the Task to which the run belongs. | UUID |
| M | status | A text string indicating the run status. | String |
| M | startedAt | The datetime when the TaskRun started. | Datetime |
| O | finishedAt | The datetime when the TaskRun finished. | Datetime |
| O | result | A JSON object storing execution result details. | Object |

## Controlled Vocabulary Tables

HydroServer also includes simple lookup tables that primarily store controlled vocabulary terms used by the main entities.

| Table | Attributes | Data Type |
| ----- | ---------- | --------- |
| `UserType` | `id`, `name`, `public` | Integer, String, Boolean |
| `OrganizationType` | `id`, `name`, `public` | Integer, String, Boolean |
| `SiteType` | `id`, `name` | Integer, String |
| `SamplingFeatureType` | `id`, `name` | Integer, String |
| `FileAttachmentType` | `id`, `name` | Integer, String |
| `VariableType` | `id`, `name` | Integer, String |
| `SensorEncodingType` | `id`, `name` | Integer, String |
| `MethodType` | `id`, `name` | Integer, String |
| `UnitType` | `id`, `name` | Integer, String |
| `DatastreamAggregation` | `id`, `name` | Integer, String |
| `DatastreamStatus` | `id`, `name` | Integer, String |
| `SampledMedium` | `id`, `name` | Integer, String |

## SensorThings Conceptual Entities

The current HydroServer SensorThings implementation still exposes SensorThings concepts that are not represented as first-class HydroServer database tables.

### FeatureOfInterest

HydroServer currently derives FeatureOfInterest behavior from the Thing and Location context used by SensorThings responses rather than storing FeatureOfInterest as a first-class HydroServer model.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the FeatureOfInterest in SensorThings responses. | UUID |
| M | name | A text string giving the name of the feature. | String |
| M | description | A text string providing a description of the feature. | String |
| M | encoding | A text string describing the encoding in which the feature is expressed. | String |
| M | feature | A GeoJSON encoding of the geometry of the feature. | Object |

### HistoricalLocation

HydroServer currently exposes HistoricalLocation through SensorThings but does not store it as a first-class HydroServer model in the main domain packages.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | thingId | A foreign key identifier for the Thing for which the HistoricalLocation is specified. | UUID |
| M | time | The time when the Thing is known to be at the Location. | Datetime |
| M | locationId | A foreign key identifier for the Location. | UUID |
