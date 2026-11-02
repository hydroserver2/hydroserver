# HydroServer Data Model Data Dictionary

This document describes the Django model fields that back HydroServer's core data model.

Attribute names below use camelCase, matching the API and the [data model diagrams](/references/data-model.md). Foreign keys are shown as `*Id` attributes. In the database, each attribute is stored under its `snake_case` equivalent (for example, `monitoringSiteId` is the `monitoring_site_id` column).

M = Mandatory
O = Optional

## Metadata field conventions

Method, ObservedProperty, ProcessingLevel, Unit, and ResultQualifier share these conventions:

| Field | Meaning | Requirement |
| --- | --- | --- |
| `name` | The label every frontend displays to identify the item. | Required; at most 255 characters. |
| `description` | Free-text comments from the user. | Required text without a fixed length limit, except Unit has no description and ResultQualifier's is optional. |
| `definition` | A URL defining or documenting the item, such as a vocabulary term, standard, or manual. | Optional URL; at most 2,000 characters. ResultQualifier has no definition. |
| `code` | An external or organizational identifier. | Optional; at most 255 characters. Unit has no code because its definition serves this purpose. |

Elsewhere in the data model, `link` is a person's or organization's website. A linked resource's `url` identifies an external link, and its `file` holds an uploaded file.

## Datastream

A Datastream groups a collection of Observations measuring the same ObservedProperty and produced by the same Method. Each instance of a Datastream represents the properties for a time series of Observations.

| Required | Attribute                      | Definition                                                                                                         | Data Type |
| -------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------ | --------- |
| M        | id                             | A primary key unique identifier for the Datastream.                                                                | UUID      |
| M        | name                           | A text name for the Datastream.                                                                                    | String    |
| M        | description                    | A text description for the Datastream.                                                                             | Text      |
| M        | methodId                      | A foreign key identifier for the Method used to produce the Datastream.                                            | UUID      |
| M        | monitoringSiteId              | A foreign key identifier for the MonitoringSite at which the Datastream was created.                               | UUID      |
| M        | observedPropertyId           | A foreign key identifier for the ObservedProperty associated with the Datastream.                                  | UUID      |
| M        | unitId                        | A foreign key identifier for the Unit used for Observations within the Datastream.                                 | UUID      |
| M        | processingLevelId            | A foreign key identifier indicating the ProcessingLevel for the Datastream.                                        | UUID      |
| M        | observationType               | The type of Observation recorded in the Datastream.                                                                | String    |
| M        | resultType                    | The type of result represented by the Datastream.                                                                  | String    |
| O        | status                         | A text value indicating the status of the Datastream.                                                              | String    |
| O        | observedArea                  | The spatial extent associated with the Datastream. This field exists in the database but is currently unused.      | String    |
| M        | sampledMedium                 | The environmental medium sampled by the Datastream.                                                                | String    |
| O        | valueCount                    | The number of Observations within the Datastream.                                                                  | Integer   |
| M        | noDataValue                  | A numeric value used to indicate the absence of data.                                                              | Float     |
| O        | intendedTimeSpacing          | A numeric value indicating the intended spacing between Observations.                                              | Float     |
| O        | intendedTimeSpacingUnit     | A string indicating the unit for `intendedTimeSpacing`.                                                          | String    |
| M        | aggregationStatistic          | A text string indicating the aggregation statistic for the Datastream.                                             | String    |
| M        | timeAggregationInterval      | A numeric value indicating the time interval over which recorded Observations were aggregated.                     | Float     |
| M        | timeAggregationIntervalUnit | A string indicating the unit for `timeAggregationInterval`.                                                      | String    |
| O        | phenomenonBeginTime          | The time at which the activity began that results in the Datastream's Observations.                                | Datetime  |
| O        | phenomenonEndTime            | The time at which the activity ended that results in the Datastream's Observations.                                | Datetime  |
| O        | resultBeginTime              | The timestamp of the first Observation in the Datastream. This field remains in the model but is currently unused. | Datetime  |
| O        | resultEndTime                | The timestamp of the last Observation in the Datastream. This field remains in the model but is currently unused.  | Datetime  |
| M        | isPrivate                     | An access control flag indicating whether the Datastream metadata and data are private by default.                 | Boolean   |
| M        | isVisible                     | An access control flag indicating whether the Datastream should be shown in normal data-discovery responses.       | Boolean   |
| M        | tags                           | Custom key-value metadata for the Datastream, stored as a JSON object of non-empty string keys and values. Defaults to `{}`. | JSON      |

## Observation

An Observation is the act of measuring or otherwise determining the value of a property, including its numeric result and the date/time at which it was observed.

| Required | Attribute         | Definition                                                                                                               | Data Type    |
| -------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------ |
| M        | id                | A primary key unique identifier for the Observation.                                                                     | UUID         |
| M        | datastreamId     | A foreign key identifier for the Datastream to which the Observation belongs.                                            | UUID         |
| M        | phenomenonTime   | A datetime value indicating the time instant when the Observation happened.                                              | Datetime     |
| M        | result            | The numeric value of the Observation.                                                                                    | Float        |
| O        | resultTime       | The time that the Observation's result was generated, if different from `phenomenonTime`.                               | Datetime     |
| O        | qualityCode      | A text code indicating the quality of the Observation.                                                                   | String       |
| O        | resultQualifiers | A JSON array of ResultQualifier names. | JSON array |

**NOTE**: `qualityCode` is persisted in the database, but the current Data Management API does not include it in the main observation schema. The API exposes `resultQualifiers` in observation payloads and as the `resultQualifiers` filter on observation queries; their values are qualifier names, not optional external codes. The Python client uses `result_qualifiers` for the corresponding keyword argument and DataFrame column.

## ObservedProperty

An ObservedProperty specifies the phenomenon of an Observation, such as flow, temperature, pH, or dissolved oxygen concentration.

| Required | Attribute              | Definition                                                                                                                         | Data Type |
| -------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                     | A primary key unique identifier for the ObservedProperty.                                                                          | UUID      |
| O        | workspaceId           | A foreign key identifier for the Workspace that owns the ObservedProperty. If omitted, the ObservedProperty is shared system-wide. | UUID      |
| M | name | The label displayed by every frontend. | String (255) |
| O | definition | A URL defining or documenting the item. | URL (2,000) |
| M | description | Free-text comments from the user. | Text |
| M | type | The type of ObservedProperty. | String (255) |
| O | code | An external or organizational identifier. | String (255) |

## Organization

An Organization is a body of people having a particular purpose, such as a business, agency, research group, or laboratory.

| Required | Attribute         | Definition                                              | Data Type  |
| -------- | ----------------- | ------------------------------------------------------- | ---------- |
| M        | id                | A primary key unique identifier for the Organization.   | BigInteger |
| M        | code              | A brief text code or abbreviation for the Organization. | String     |
| M        | name              | A descriptive name for the Organization.                | String     |
| O        | description       | A text description of the Organization.                 | Text       |
| O        | link              | A URL pointing to a website for the Organization.       | URL        |
| M        | organizationType | A text string indicating the type of Organization.      | String     |

## User

Individual users who own workspaces, collaborate on data management, or manage account information in HydroServer.

| Required | Attribute             | Definition                                                                                                                                                                                                | Data Type              |
| -------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| M        | id                    | A primary key unique identifier for the User.                                                                                                                                                             | BigInteger             |
| M        | username              | The Django username field. HydroServer keeps this synchronized to the user's email address.                                                                                                               | String                 |
| M        | password              | The stored password hash.                                                                                                                                                                                 | String                 |
| O        | lastLogin            | The datetime when the User last logged in.                                                                                                                                                                | Datetime               |
| M        | isSuperuser          | A boolean value indicating whether the User bypasses explicit permission assignments.                                                                                                                     | Boolean                |
| O        | firstName            | The User's first name.                                                                                                                                                                                    | String                 |
| O        | middleName           | The User's middle name.                                                                                                                                                                                   | String                 |
| O        | lastName             | The User's last name.                                                                                                                                                                                     | String                 |
| M        | email                 | The User's contact email address.                                                                                                                                                                         | String                 |
| M        | isStaff              | A boolean value indicating whether the User can access the Django admin site.                                                                                                                             | Boolean                |
| M        | isActive             | A boolean value indicating whether the account is active.                                                                                                                                                 | Boolean                |
| M        | dateJoined           | The datetime when the User account was created.                                                                                                                                                           | Datetime               |
| O        | phone                 | The User's contact phone number.                                                                                                                                                                          | String                 |
| O        | address               | The User's physical mailing address.                                                                                                                                                                      | String                 |
| O        | link                  | A URL pointing to a website for the User.                                                                                                                                                                 | URL                    |
| M        | userType             | A text string indicating the type of User.                                                                                                                                                                | String                 |
| O        | organizationId       | A one-to-one identifier for the Organization with which the User is affiliated. Each User may be affiliated with at most one Organization, and each Organization may be affiliated with at most one User. | BigInteger             |
| O        | ownedWorkspaceLimit | The maximum number of workspaces the User may own. `0` prevents ownership and `NULL` allows unlimited ownership.                                                                                          | Positive Small Integer |

**NOTE**: `groups` and `user_permissions` are also persisted through Django auth many-to-many join tables, but they are not columns on the `User` row itself.

## ProcessingLevel

The degree of quality control or processing to which a Datastream has been subjected.

| Required | Attribute    | Definition                                                                                                                       | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the ProcessingLevel.                                                                         | UUID      |
| O        | workspaceId | A foreign key identifier for the Workspace that owns the ProcessingLevel. If omitted, the ProcessingLevel is shared system-wide. | UUID      |
| O | code | An external or organizational identifier. | String (255) |
| M | name | The label displayed by every frontend. | String (255) |
| M | description | Free-text comments from the user. | Text |
| O | definition | A URL defining or documenting the item. | URL (2,000) |

## ResultQualifier

Data qualifying comments added to individual data values to qualify their interpretation or use.

| Required | Attribute    | Definition                                                                                                                       | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the ResultQualifier.                                                                         | UUID      |
| O        | workspaceId | A foreign key identifier for the Workspace that owns the ResultQualifier. If omitted, the ResultQualifier is shared system-wide. | UUID      |
| M        | name         | A brief text name identifying the ResultQualifier.                                                                               | String    |
| O        | description  | A longer text description or explanation of the ResultQualifier.                                                                 | Text      |

**NOTE**: The database enforces a unique constraint on `(name, workspaceId)`, including the system-wide `NULL` workspace scope.

## Method

A Method describes how a Datastream's Observations are produced, whether by an instrument, technician, laboratory procedure, simulation, or computation.

| Required | Attribute                | Definition                                                                                                     | Data Type |
| -------- | ------------------------ | -------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                       | A primary key unique identifier for the Method.                                                                | UUID      |
| O        | workspaceId             | A foreign key identifier for the Workspace that owns the Method. If omitted, the Method is shared system-wide. | UUID      |
| M | name | The label displayed by every frontend. | String (255) |
| O | code | An external or organizational identifier. | String (255) |
| M | type | A controlled-vocabulary value identifying the kind of Method. | String (255) |
| M | description | Free-text comments from the user. | Text |
| O | definition | A URL defining or documenting the item. | URL (2,000) |
| O        | sensorModel             | The model name when the Method represents an instrument.                                                       | String    |
| O        | sensorModelManufacturer | The model manufacturer when the Method represents an instrument.                                               | String    |
| O | sensorModelDefinition | A URL pointing to documentation for the sensor model. | URL (2,000) |

The SensorThings API continues to expose these records as Sensor entities for standards compatibility.

## MonitoringSite

A MonitoringSite stores a site and its single physical location in one row.

| Required | Attribute       | Definition                                                                                                                   | Data Type |
| -------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id              | A primary key unique identifier for the MonitoringSite.                                                                      | UUID      |
| M        | workspaceId    | A foreign key identifier for the Workspace that owns the MonitoringSite.                                                     | UUID      |
| M        | name            | A text name for the MonitoringSite.                                                                                          | String    |
| M        | description     | A text description for the MonitoringSite.                                                                                   | Text      |
| M        | code            | A shortened code identifying the MonitoringSite.                                                                             | String    |
| M        | type            | The type of monitoring site.                                                                                                 | String    |
| M        | latitude        | The site's latitude using WGS84 coordinates.                                                                                 | Decimal   |
| M        | longitude       | The site's longitude using WGS84 coordinates.                                                                                | Decimal   |
| O        | elevationM     | The site's elevation in meters.                                                                                              | Decimal   |
| O        | elevationDatum | The elevation datum used for the site.                                                                                       | String    |
| O        | adminArea1    | The first-level administrative area.                                                                                         | String    |
| O        | adminArea2    | The second-level administrative area.                                                                                        | String    |
| O        | country         | A two-character ISO country code.                                                                                            | String    |
| M        | isPrivate      | Whether the MonitoringSite is discoverable and its metadata publicly available.                                             | Boolean   |
| O        | dataDisclaimer | A disclaimer displayed with the MonitoringSite's data.                                                                      | Text      |
| M        | tags            | Custom key-value metadata for the MonitoringSite, stored as a JSON object of non-empty string keys and values. Defaults to `{}`. | JSON      |

## MonitoringSiteLinkedResource

A linked resource associated with a MonitoringSite, pointing to either a hosted file (such as a site photo or document) or an external URL. The database enforces unique `(monitoringSiteId, name)` pairs, and a check constraint that exactly one of `file`/`url` is set.

| Required | Attribute    | Definition                                                                | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the MonitoringSiteLinkedResource.     | UUID      |
| M        | monitoringSiteId | A foreign key identifier for the MonitoringSite to which the linked resource belongs. | UUID      |
| M        | name         | The name of the linked resource.                                          | String    |
| O        | description  | A text description of the linked resource.                               | Text      |
| O        | file         | The stored file object, if the resource is hosted by HydroServer.        | File      |
| O        | url          | The external URL, if the resource is not hosted by HydroServer.          | String    |
| M        | type         | A text string identifying the type of linked resource.                   | String    |

## Unit

The unit of measure associated with the Observations within a Datastream.

| Required | Attribute    | Definition                                                                                                 | Data Type |
| -------- | ------------ | ---------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the Unit.                                                              | UUID      |
| O        | workspaceId | A foreign key identifier for the Workspace that owns the Unit. If omitted, the Unit is shared system-wide. | UUID      |
| M | name | The label displayed by every frontend. | String (255) |
| M        | symbol       | An abbreviation or symbol used for the Unit.                                                               | String    |
| O | definition | A URL defining or documenting the item. | URL (2,000) |
| M | type | The type of Unit. | String (255) |

## Workspace

A Workspace is the ownership and access-control boundary for most HydroServer-managed resources.

| Required | Attribute  | Definition                                                          | Data Type  |
| -------- | ---------- | ------------------------------------------------------------------- | ---------- |
| M        | id         | A primary key unique identifier for the Workspace.                  | UUID       |
| M        | name       | A descriptive name for the Workspace.                               | String     |
| M        | ownerId   | A foreign key identifier for the User who owns the Workspace.       | BigInteger |
| M        | isPrivate | An access control flag indicating whether the Workspace is private. | Boolean    |

**NOTE**: The database enforces a unique constraint on `(name, ownerId)`.

## WorkspaceTransferConfirmation

A pending transfer record used when ownership of a Workspace is being transferred to another User.

| Required | Attribute    | Definition                                                                                                                     | Data Type  |
| -------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| M        | id           | A primary key unique identifier for the WorkspaceTransferConfirmation.                                                         | BigInteger |
| M        | workspaceId | A one-to-one foreign key identifier for the Workspace being transferred. Each Workspace may have at most one pending transfer. | UUID       |
| M        | newOwnerId | A foreign key identifier for the new owner.                                                                                    | BigInteger |

## Role

A Role is a named collection of permissions that can be assigned to user or service-account collaborators.

| Required | Attribute    | Definition                                                                                                 | Data Type |
| -------- | ------------ | ---------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the Role.                                                              | UUID      |
| O        | workspaceId | A foreign key identifier for the Workspace that owns the Role. If omitted, the Role is shared system-wide. | UUID      |
| M        | name         | A descriptive name for the Role.                                                                           | String    |
| O        | description  | A text description of the Role.                                                                            | Text      |

## Permission

A Permission associates a Role with the actions it may perform on a resource type.

| Required | Attribute     | Definition                                                                                                                                                                                                                                                                                                                  | Data Type  |
| -------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| M        | id            | A primary key unique identifier for the Permission.                                                                                                                                                                                                                                                                         | BigInteger |
| M        | roleId       | A foreign key identifier for the Role to which the Permission belongs.                                                                                                                                                                                                                                                      | UUID       |
| M        | resourceType | The resource type to which the Permission applies. One of `*`, `Workspace`, `Role`, `ServiceAccount`, `Collaborator`, `MonitoringSite`, `ObservedProperty`, `ProcessingLevel`, `ResultQualifier`, `Method`, `Unit`, `Datastream`, `Observation`, `DataConnection`, `EtlTask`, `RatingCurve`, `DataProductTask`, or `MonitoringTask`. | String     |
| M        | canView      | Whether the Role may view this resource type.                                                                                                                                                                                                                                                                               | Boolean    |
| M        | canCreate    | Whether the Role may create this resource type.                                                                                                                                                                                                                                                                             | Boolean    |
| M        | canEdit      | Whether the Role may edit this resource type.                                                                                                                                                                                                                                                                               | Boolean    |
| M        | canDelete    | Whether the Role may delete this resource type.                                                                                                                                                                                                                                                                             | Boolean    |

## Collaborator

A Collaborator associates either a User or a ServiceAccount with a Workspace through a Role.

| Required | Attribute          | Definition                                                          | Data Type  |
| -------- | ------------------ | ------------------------------------------------------------------- | ---------- |
| M        | id                 | A primary key unique identifier for the Collaborator.               | BigInteger |
| M        | workspaceId       | A foreign key identifier for the Workspace.                         | UUID       |
| O        | userId            | A foreign key identifier for the collaborating User.                | BigInteger |
| O        | serviceAccountId | A foreign key identifier for the collaborating ServiceAccount.      | UUID       |
| M        | roleId            | A foreign key identifier for the Role assigned to the Collaborator. | UUID       |

**NOTE**: Exactly one of `userId` and `serviceAccountId` must be set. The database allows each User or ServiceAccount to appear at most once per Workspace.

## ServiceAccount

A ServiceAccount grants non-interactive access through a generated API key. It belongs to a Workspace and receives permissions through Collaborator records.

| Required | Attribute      | Definition                                                                  | Data Type |
| -------- | -------------- | --------------------------------------------------------------------------- | --------- |
| M        | id             | A primary key unique identifier for the ServiceAccount.                     | UUID      |
| M        | email          | The generated unique email-like identifier used in collaborator operations. | String    |
| M        | name           | A descriptive name for the ServiceAccount.                                  | String    |
| O        | description    | A text description of the ServiceAccount.                                   | Text      |
| O        | workspaceId   | The Workspace where the ServiceAccount was created.                         | UUID      |
| M        | createdAt     | The datetime when the ServiceAccount was created.                           | Datetime  |
| O        | lastUsedAt   | The datetime when the ServiceAccount last authenticated.                    | Datetime  |
| M        | isActive      | Whether the ServiceAccount may authenticate.                                | Boolean   |
| O        | deactivatedAt | The datetime when the ServiceAccount was deactivated.                       | Datetime  |
| M        | keyPrefix     | The unique public prefix of the generated API key.                          | String    |
| M        | keyHash       | The stored hash of the API key secret.                                      | String    |
| O        | keyCreatedAt | The datetime when the current API key was generated.                        | Datetime  |
| O        | keyExpiresAt | The datetime when the current API key expires.                              | Datetime  |

## DatastreamLinkedResource

A linked resource associated with a Datastream, pointing to either a hosted file or an external URL.

| Required | Attribute     | Definition                                                                        | Data Type |
| -------- | ------------- |-----------------------------------------------------------------------------------| --------- |
| M        | id            | A primary key unique identifier for the DatastreamLinkedResource.                 | UUID      |
| M        | datastreamId | A foreign key identifier for the Datastream to which the linked resource belongs. | UUID      |
| M        | name          | The name of the linked resource.                                                  | String    |
| O        | description   | A text description of the linked resource.                                        | Text      |
| O        | file          | The stored file object, if the resource is hosted by HydroServer.                 | File      |
| O        | url           | The external URL, if the resource is not hosted by HydroServer.                   | String    |
| M        | type          | A text string identifying the type of linked resource.                            | String    |

**NOTE**: The database enforces a unique constraint on `(datastreamId, name)`, and a check constraint that exactly one of `file`/`url` is set.

# Orchestration

HydroServer's orchestration layer defines a base `Task` model that is extended by domain-specific task subclasses in the ETL, Data Products, and Data Monitoring apps. Each domain task is a multi-table-inheritance child of the base Task: its primary key is the inherited `task_ptr_id` (the parent Task's UUID), and the row in the subclass table joins with the row in the orchestration `task` table.

## Task

A Task defines an automated HydroServer workflow. It holds the schedule and run state shared by every task subtype. Each concrete task subclass — `EtlTask`, `DataProductTask`, and `MonitoringTask` — extends this model through multi-table inheritance.

| Required | Attribute        | Definition                                                                                                                               | Data Type  |
| -------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| M        | id               | A primary key unique identifier for the Task. Domain task subclasses share this identifier.                                              | UUID       |
| M        | name             | A descriptive name for the Task.                                                                                                         | String     |
| O        | description      | A text description for the Task.                                                                                                         | Text       |
| O        | periodicTaskId | A one-to-one identifier for the associated scheduler record in `django_celery_beat`. Each Task maps to at most one periodic task record. | BigInteger |
| O        | nextRunAt      | The datetime when the Task is expected to run next.                                                                                      | Datetime   |

## TaskRun

A TaskRun stores the execution history for a Task.

| Required | Attribute   | Definition                                                                          | Data Type |
| -------- | ----------- | ----------------------------------------------------------------------------------- | --------- |
| M        | id          | A primary key unique identifier for the TaskRun.                                    | UUID      |
| M        | taskId     | A foreign key identifier for the Task to which the run belongs.                     | UUID      |
| M        | status      | A text string indicating the run status: `PENDING`, `STARTED`, `SUCCESS`, or `FAILURE`. | String    |
| O        | message     | A text string describing the outcome or error message for the run.                  | Text      |
| M        | startedAt  | The datetime when the TaskRun started. Automatically populated on creation.         | Datetime  |
| O        | finishedAt | The datetime when the TaskRun finished.                                             | Datetime  |
| O        | result      | A JSON object storing execution result details.                                     | JSON      |

# ETL

The ETL app models the configuration used to extract data from an external source and load it into HydroServer Datastreams.

## DataConnection

A DataConnection describes a single external data source: where to fetch payloads, how to authenticate, and how to interpret the timestamps in the response. A DataConnection is shared across one or more `EtlTask` instances and one optional notification configuration.

| Required | Attribute         | Definition                                                                                                  | Data Type |
| -------- | ----------------- | ----------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                | A primary key unique identifier for the DataConnection.                                                     | UUID      |
| M        | name              | A descriptive name for the DataConnection.                                                                  | String    |
| O        | description       | A text description for the DataConnection.                                                                  | Text      |
| M        | workspaceId      | A foreign key identifier for the Workspace that owns the DataConnection.                                    | UUID      |
| M        | sourceUrl        | The URL template fetched by the extractor. May contain placeholder variables resolved at run time.          | Text      |
| O        | authHeaderName  | The name of an HTTP header used to authenticate against the source URL (e.g. `Authorization`).              | String    |
| O        | authHeaderValue | The value sent with the auth header, such as an API token. Stored as plain text.                            | Text      |
| O        | timezoneType     | The kind of timezone interpretation applied to the timestamps: `utc`, `offset`, or `iana`.                  | String    |
| O        | timezone          | The timezone value (an IANA name or an offset) used when `timezoneType` is `offset` or `iana`.             | String    |

## PlaceholderVariable

A PlaceholderVariable defines a named substitution that is resolved into the DataConnection's `sourceUrl` at run time.

| Required | Attribute          | Definition                                                                                                  | Data Type |
| -------- | ------------------ | ----------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                 | A primary key unique identifier for the PlaceholderVariable.                                                | UUID      |
| M        | dataConnectionId | A foreign key identifier for the DataConnection to which the placeholder belongs.                           | UUID      |
| M        | name               | The placeholder name as it appears in the `sourceUrl` template.                                            | String    |
| M        | variableType      | The type of value substituted at run time: `run_time`, `latest_observation_timestamp`, `window_start`, `window_end`, or `per_task`. | String    |
| O        | timestampFormat   | An optional format string used to render the substituted value when the value is a timestamp.               | String    |

## Payload

A Payload describes how the response body returned by the extractor should be parsed. Each DataConnection has at most one Payload row.

| Required | Attribute          | Definition                                                                                              | Data Type |
| -------- | ------------------ | ------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                 | A primary key unique identifier for the Payload.                                                        | UUID      |
| M        | dataConnectionId | A one-to-one foreign key identifier for the DataConnection to which the Payload belongs.                | UUID      |
| M        | payloadType       | The payload encoding: `CSV` or `JSON`.                                                                  | String    |
| O        | headerRow         | For CSV payloads, the row index containing column headers.                                              | Integer   |
| O        | dataStartRow     | For CSV payloads, the row index where data begins.                                                      | Integer   |
| O        | delimiter          | For CSV payloads, the field delimiter: `,`, `\t`, `;`, `\|`, or ` `.                                    | String    |
| O        | jmespath           | For JSON payloads, a JMESPath expression used to select observation records out of the response body.  | Text      |
| M        | timestampKey      | The field name or column key that identifies the timestamp in the source payload.                       | String    |
| O        | timestampFormat   | An optional format string used to parse non-ISO timestamps from the source payload.                     | String    |
| O        | dataIngestionWindowStartAnchor | The reference point for the start of the data ingestion window: `latest_observation_timestamp`, `run_time`, or `fixed_timestamp`. If omitted, the window has no start. | String |
| O        | dataIngestionWindowStartLookback | An amount of time subtracted from the start anchor. Not used with `fixed_timestamp`.          | Integer   |
| O        | dataIngestionWindowStartLookbackUnit | The unit for `dataIngestionWindowStartLookback`: `minutes`, `hours`, or `days`.     | String    |
| O        | dataIngestionWindowStartTimestamp | The window start datetime, required when the start anchor is `fixed_timestamp`.              | Datetime  |
| O        | dataIngestionWindowEndAnchor | The reference point for the end of the data ingestion window, with the same choices as the start anchor. If omitted, the window has no end. | String |
| O        | dataIngestionWindowEndLookback | An amount of time subtracted from the end anchor. Not used with `fixed_timestamp`.              | Integer   |
| O        | dataIngestionWindowEndLookbackUnit | The unit for `dataIngestionWindowEndLookback`: `minutes`, `hours`, or `days`.         | String    |
| O        | dataIngestionWindowEndTimestamp | The window end datetime, required when the end anchor is `fixed_timestamp`.                    | Datetime  |

## DataConnectionNotification

A DataConnectionNotification records the configuration for the periodic task run summary email associated with a DataConnection.

| Required | Attribute          | Definition                                                                                                                                              | Data Type  |
| -------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| M        | dataConnectionId | The primary key for the DataConnectionNotification — a one-to-one foreign key to DataConnection. Each DataConnection has at most one notification row. | UUID       |
| O        | periodicTaskId   | A one-to-one identifier for the associated scheduler record in `django_celery_beat`.                                                                    | BigInteger |

## DataConnectionNotificationRecipient

A notification email recipient associated with a DataConnectionNotification.

| Required | Attribute       | Definition                                                                       | Data Type |
| -------- | --------------- | -------------------------------------------------------------------------------- | --------- |
| M        | id              | A primary key unique identifier for the DataConnectionNotificationRecipient.     | UUID      |
| M        | notificationId | A foreign key identifier for the DataConnectionNotification.                     | UUID      |
| M        | email           | An email address that receives notifications for the parent DataConnection.      | Email     |

**NOTE**: The database enforces a unique constraint on `(notificationId, email)`.

## EtlTask

An EtlTask extends `Task` with the ETL-specific configuration that links the run to a DataConnection and any runtime overrides used by the extractor, transformer, and loader.

| Required | Attribute          | Definition                                                                                                | Data Type |
| -------- | ------------------ | --------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                 | A primary key unique identifier for the EtlTask. Inherited from the parent `Task` row as `task_ptr_id`. | UUID      |
| M        | dataConnectionId | A foreign key identifier for the DataConnection used by the EtlTask.                                      | UUID      |
| M        | taskVariables     | A JSON object storing runtime variables substituted into the DataConnection placeholders for this Task.   | JSON      |

## EtlMapping

An EtlMapping associates a source identifier produced by the DataConnection with the target Datastream into which the values should be loaded. The previous `TaskMapping` / `TaskMappingPath` pair has been collapsed into this single model.

| Required | Attribute             | Definition                                                                  | Data Type |
| -------- | --------------------- | --------------------------------------------------------------------------- | --------- |
| M        | id                    | A primary key unique identifier for the EtlMapping.                         | UUID      |
| M        | etlTaskId           | A foreign key identifier for the EtlTask to which the mapping belongs.      | UUID      |
| M        | sourceIdentifier     | A text identifier representing an incoming source field or column.          | String    |
| M        | targetDatastreamId  | A foreign key identifier for the Datastream that receives the mapped values. | UUID      |

# Data Products

The Data Products app models derived Datastreams produced by transformations such as rating curves, derivations, and time-series aggregations.

## DataProductTask

A DataProductTask extends `Task` with the data-product context — the MonitoringSite under which the derived Datastreams are organized.

| Required | Attribute | Definition                                                                                                       | Data Type |
| -------- | --------- | ---------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id        | A primary key unique identifier for the DataProductTask. Inherited from the parent `Task` row as `task_ptr_id`. | UUID      |
| M        | monitoringSiteId  | A foreign key identifier for the MonitoringSite that owns the derived Datastreams produced by this task.                  | UUID      |

## DataProductTransformation

A DataProductTransformation describes how a single derived (output) Datastream is computed from one or more input Datastreams.

| Required | Attribute              | Definition                                                                                                                          | Data Type |
| -------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                     | A primary key unique identifier for the DataProductTransformation.                                                                  | UUID      |
| M        | taskId                | A foreign key identifier for the DataProductTask to which the transformation belongs.                                               | UUID      |
| M        | outputDatastreamId   | A one-to-one foreign key identifier for the Datastream that receives the transformation output.                                     | UUID      |
| M        | transformationType    | The type of transformation: `rating_curve`, `derivation`, or `aggregation`.                                                          | String    |
| O        | ratingCurveId        | A foreign key identifier for the RatingCurve used when `transformationType` is `rating_curve`.                                     | UUID      |
| O        | formula                | A formula (expression) string used when `transformationType` is `derivation`, referencing one or more input variable names.        | Text      |
| O        | stopOnGaps        | For `derivation` transformations, whether a run stops at timestamps not shared by all inputs (vs. skipping them). Inputs holding their no-data value always produce the output's no-data value. | Boolean   |
| O        | stopOnError          | For `derivation` transformations, whether a run stops when the formula produces a non-finite result (vs. filling and continuing).    | Boolean   |
| O        | outputIntervalUnits  | The interval unit for `aggregation` outputs: `minutes`, `hours`, `days`, `weeks`, or `months`.                                      | String    |
| O        | outputInterval        | The positive interval count corresponding to `outputIntervalUnits`.                                                               | Integer   |
| O        | timezoneType          | For interval-aligned aggregations, the timezone interpretation: `utc`, `offset`, or `iana`.                                         | String    |
| O        | timezone               | The timezone value (an IANA name or an offset) used when `timezoneType` is `offset` or `iana`.                                     | String    |
| O        | aggregationMethod     | For `aggregation` transformations, the aggregation function: `mean`, `sum`, `min`, `max`, `first`, `last`, or `time_weighted_mean`. | String    |
| O        | minValues             | For `aggregation` transformations, the minimum number of input observations required per window.                                    | Integer   |

## DataProductTransformationInput

A DataProductTransformationInput records a single input Datastream consumed by a DataProductTransformation, optionally bound to a named variable in the formula.

| Required | Attribute         | Definition                                                                                                  | Data Type |
| -------- | ----------------- | ----------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                | A primary key unique identifier for the DataProductTransformationInput.                                     | UUID      |
| M        | transformationId | A foreign key identifier for the DataProductTransformation that consumes the input.                         | UUID      |
| M        | datastreamId     | A foreign key identifier for the input Datastream.                                                          | UUID      |
| O        | variableName     | The variable name used in the transformation `formula` to reference this input.                             | String    |

**NOTE**: The database enforces a unique constraint on `(transformationId, variableName)` when `variableName` is not null.

## RatingCurve

A RatingCurve defines a mapping from input values to output values, used by `rating_curve` transformations to convert one Datastream (e.g. stage) to another (e.g. discharge).

| Required | Attribute      | Definition                                                                          | Data Type |
| -------- | -------------- | ----------------------------------------------------------------------------------- | --------- |
| M        | id             | A primary key unique identifier for the RatingCurve.                                | UUID      |
| M        | monitoringSiteId       | A foreign key identifier for the MonitoringSite to which the RatingCurve belongs.            | UUID      |
| M        | name           | A descriptive name for the RatingCurve.                                             | String    |
| O        | description    | A text description for the RatingCurve.                                             | Text      |
| M        | fittingMethod | The method used to fit the curve: `linear` or `power_law`.                          | String    |

## RatingCurvePoint

A RatingCurvePoint defines a single (input, output) sample used to fit a RatingCurve.

| Required | Attribute       | Definition                                                              | Data Type |
| -------- | --------------- | ----------------------------------------------------------------------- | --------- |
| M        | id              | A primary key unique identifier for the RatingCurvePoint.               | UUID      |
| M        | ratingCurveId | A foreign key identifier for the RatingCurve to which the point belongs. | UUID      |
| M        | inputValue     | The input value of the point (e.g. stage).                              | Float     |
| M        | outputValue    | The output value of the point (e.g. discharge).                         | Float     |

# Data Monitoring

The Data Monitoring app models scheduled checks that evaluate Datastreams against quality-control rules and notify recipients when rules are violated.

## MonitoringTask

A MonitoringTask extends `Task` with the data-monitoring context — the MonitoringSite whose Datastreams are evaluated.

| Required | Attribute | Definition                                                                                                  | Data Type |
| -------- | --------- | ----------------------------------------------------------------------------------------------------------- | --------- |
| M        | id        | A primary key unique identifier for the MonitoringTask. Inherited from the parent `Task` row as `task_ptr_id`. | UUID   |
| M        | monitoringSiteId  | A foreign key identifier for the MonitoringSite whose Datastreams are monitored by this task.                        | UUID      |

## MonitoringRule

A MonitoringRule defines a single quality-control check applied to a Datastream by a MonitoringTask.

| Required | Attribute             | Definition                                                                                              | Data Type |
| --------- | --------------------- | ------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                    | A primary key unique identifier for the MonitoringRule.                                                 | UUID      |
| M        | taskId               | A foreign key identifier for the MonitoringTask to which the rule belongs.                              | UUID      |
| M        | datastreamId         | A foreign key identifier for the Datastream evaluated by the rule.                                      | UUID      |
| M        | ruleType             | The type of rule: `range`, `rate_of_change`, `persistence`, or `missing_data`.                          | String    |
| O        | lastCheckedAt       | The datetime when the rule was last evaluated.                                                          | Datetime  |
| O        | minValue             | For `range` rules, the lower bound of the allowed range.                                                | Float     |
| O        | maxValue             | For `range` rules, the upper bound of the allowed range.                                                | Float     |
| O        | windowInterval       | For window-based rules, the positive number of `windowIntervalUnits` evaluated by the rule.           | Integer   |
| O        | windowIntervalUnits | For window-based rules, the unit of the evaluation window: `minutes`, `hours`, or `days`.               | String    |

**NOTE**: The database enforces a unique constraint on `(taskId, datastreamId, ruleType)`.

## MonitoringNotificationRecipient

A notification email recipient associated with a MonitoringTask.

| Required | Attribute | Definition                                                          | Data Type |
| -------- | --------- | ------------------------------------------------------------------- | --------- |
| M        | id        | A primary key unique identifier for the MonitoringNotificationRecipient. | UUID |
| M        | taskId   | A foreign key identifier for the MonitoringTask.                    | UUID      |
| M        | email     | An email address that receives notifications for the MonitoringTask. | Email     |

**NOTE**: The database enforces a unique constraint on `(taskId, email)`.

# Reference Data

## Controlled Vocabulary Tables

HydroServer also stores the controlled vocabulary terms used by the main entities in the following tables. `UserType` and `OrganizationType` are simple lookup tables. The rest are resources managed through the Data Management API, each with its own collection (for example, `monitoring-site-types`), and administrators can also manage them in the [administrator dashboard](/hosting-and-deployment/how-to/using-the-administrator-dashboard.md#controlled-vocabularies).

| Table                  | Attributes                  | Data Type                   |
| ---------------------- | --------------------------- | --------------------------- |
| `UserType`             | `id`, `name`, `public`      | BigInteger, String, Boolean |
| `OrganizationType`     | `id`, `name`, `public`      | BigInteger, String, Boolean |
| `MonitoringSiteType`   | `id`, `name`, `description` | UUID, String, Text          |
| `LinkedResourceType`   | `id`, `name`, `description` | UUID, String, Text          |
| `ObservedPropertyType` | `id`, `name`, `description` | UUID, String, Text          |
| `MethodType`           | `id`, `name`, `description` | UUID, String, Text          |
| `UnitType`             | `id`, `name`, `description` | UUID, String, Text          |
| `AggregationStatistic` | `id`, `name`, `description` | UUID, String, Text          |
| `DatastreamStatus`     | `id`, `name`, `description` | UUID, String, Text          |
| `SampledMedium`        | `id`, `name`, `description` | UUID, String, Text          |

## SensorThings Conceptual Entities

The current HydroServer SensorThings implementation still exposes SensorThings concepts that are not represented as first-class HydroServer database tables.

### FeatureOfInterest

HydroServer currently derives FeatureOfInterest behavior from the MonitoringSite context used by SensorThings responses rather than storing FeatureOfInterest as a first-class HydroServer model.

| Required | Attribute   | Definition                                                                           | Data Type |
| -------- | ----------- | ------------------------------------------------------------------------------------ | --------- |
| M        | id          | A primary key unique identifier for the FeatureOfInterest in SensorThings responses. | UUID      |
| M        | name        | A text string giving the name of the feature.                                        | String    |
| M        | description | A text string providing a description of the feature.                                | String    |
| M        | encodingType | A text string describing the encoding in which the feature is expressed.            | String    |
| M        | feature     | A GeoJSON encoding of the geometry of the feature.                                   | Object    |

### HistoricalLocation

HydroServer currently exposes HistoricalLocation through SensorThings but does not store it as a first-class HydroServer model in the main domain packages.

| Required | Attribute   | Definition                                                                            | Data Type |
| -------- | ----------- | ------------------------------------------------------------------------------------- | --------- |
| M        | thingId    | A foreign key identifier for the SensorThings Thing for which the HistoricalLocation is specified. | UUID      |
| M        | time        | The time when the Thing is known to be at the Location.                                           | Datetime  |
| M        | locationId | A foreign key identifier for the Location.                                            | UUID      |
