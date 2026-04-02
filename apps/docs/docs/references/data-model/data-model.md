# HydroServer Data Model Data Dictionary

This document describes the Django model fields that back HydroServer's core data model.

Attribute names below use the persisted model field names in `snake_case`. Foreign keys are shown as the stored `*_id` values. The API uses camelCase aliases.

M = Mandatory
O = Optional

## Datastream

A Datastream groups a collection of Observations measuring the same ObservedProperty and produced by the same Sensor. Each instance of a Datastream represents the properties for a time series of Observations.

| Required | Attribute                      | Definition                                                                                                         | Data Type |
| -------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------ | --------- |
| M        | id                             | A primary key unique identifier for the Datastream.                                                                | UUID      |
| M        | name                           | A text name for the Datastream.                                                                                    | String    |
| M        | description                    | A text description for the Datastream.                                                                             | Text      |
| M        | sensor_id                      | A foreign key identifier for the Sensor or method used to create the Datastream.                                   | UUID      |
| M        | thing_id                       | A foreign key identifier for the Thing on which or at which the Datastream was created.                            | UUID      |
| M        | observed_property_id           | A foreign key identifier for the ObservedProperty associated with the Datastream.                                  | UUID      |
| M        | unit_id                        | A foreign key identifier for the Unit used for Observations within the Datastream.                                 | UUID      |
| M        | processing_level_id            | A foreign key identifier indicating the ProcessingLevel for the Datastream.                                        | UUID      |
| M        | observation_type               | The type of Observation recorded in the Datastream.                                                                | String    |
| M        | result_type                    | The type of result represented by the Datastream.                                                                  | String    |
| O        | status                         | A text value indicating the status of the Datastream.                                                              | String    |
| O        | observed_area                  | The spatial extent associated with the Datastream. This field exists in the database but is currently unused.      | String    |
| M        | sampled_medium                 | The environmental medium sampled by the Datastream.                                                                | String    |
| O        | value_count                    | The number of Observations within the Datastream.                                                                  | Integer   |
| M        | no_data_value                  | A numeric value used to indicate the absence of data.                                                              | Float     |
| O        | intended_time_spacing          | A numeric value indicating the intended spacing between Observations.                                              | Float     |
| O        | intended_time_spacing_unit     | A string indicating the unit for `intended_time_spacing`.                                                          | String    |
| M        | aggregation_statistic          | A text string indicating the aggregation statistic for the Datastream.                                             | String    |
| M        | time_aggregation_interval      | A numeric value indicating the time interval over which recorded Observations were aggregated.                     | Float     |
| M        | time_aggregation_interval_unit | A string indicating the unit for `time_aggregation_interval`.                                                      | String    |
| O        | phenomenon_begin_time          | The time at which the activity began that results in the Datastream's Observations.                                | Datetime  |
| O        | phenomenon_end_time            | The time at which the activity ended that results in the Datastream's Observations.                                | Datetime  |
| O        | result_begin_time              | The timestamp of the first Observation in the Datastream. This field remains in the model but is currently unused. | Datetime  |
| O        | result_end_time                | The timestamp of the last Observation in the Datastream. This field remains in the model but is currently unused.  | Datetime  |
| M        | is_private                     | An access control flag indicating whether the Datastream metadata and data are private by default.                 | Boolean   |
| M        | is_visible                     | An access control flag indicating whether the Datastream should be shown in normal data-discovery responses.       | Boolean   |

## Location

The Location entity stores the location of a Thing. In the context of Things that are monitoring sites, this is the physical location of the monitoring site.

| Required | Attribute       | Definition                                                                      | Data Type |
| -------- | --------------- | ------------------------------------------------------------------------------- | --------- |
| M        | id              | A primary key unique identifier for the Location.                               | UUID      |
| M        | thing_id        | A foreign key identifier for the Thing to which the Location belongs.           | UUID      |
| M        | name            | A text string name for the Location.                                            | String    |
| M        | description     | A text string description for the Location.                                     | Text      |
| M        | encoding_type   | The encoding type of the Location, usually `application/vnd.geo+json`.          | String    |
| M        | latitude        | The latitude of the Location using WGS84 coordinates.                           | Decimal   |
| M        | longitude       | The longitude of the Location using WGS84 coordinates.                          | Decimal   |
| O        | elevation_m     | The elevation of the Location in meters.                                        | Decimal   |
| O        | elevation_datum | A text string indicating the elevation datum used for the Location.             | String    |
| O        | admin_area_1    | A text string indicating the first-level administrative area for the Location.  | String    |
| O        | admin_area_2    | A text string indicating the second-level administrative area for the Location. | String    |
| O        | country         | A two-character ISO country code for the Location.                              | String    |

**NOTE**: The database allows a Thing to have multiple Location rows, but the current Data Management API treats `location` as a single nested object on a Thing.

## Observation

An Observation is the act of measuring or otherwise determining the value of a property, including its numeric result and the date/time at which it was observed.

| Required | Attribute         | Definition                                                                                                               | Data Type    |
| -------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------ |
| M        | id                | A primary key unique identifier for the Observation.                                                                     | UUID         |
| M        | datastream_id     | A foreign key identifier for the Datastream to which the Observation belongs.                                            | UUID         |
| M        | phenomenon_time   | A datetime value indicating the time instant when the Observation happened.                                              | Datetime     |
| M        | result            | The numeric value of the Observation.                                                                                    | Float        |
| O        | result_time       | The time that the Observation's result was generated, if different from `phenomenon_time`.                               | Datetime     |
| O        | quality_code      | A text code indicating the quality of the Observation.                                                                   | String       |
| O        | result_qualifiers | A many-to-many relationship to ResultQualifier. This is stored in a join table, not as an array column on `Observation`. | Many-to-many |

**NOTE**: `quality_code` is persisted in the database, but the current Data Management API does not include it in the main observation schema. The API also uses `resultQualifierCodes` rather than exposing the join table directly.

## ObservedProperty

An ObservedProperty specifies the phenomenon of an Observation, such as flow, temperature, pH, or dissolved oxygen concentration.

| Required | Attribute              | Definition                                                                                                                         | Data Type |
| -------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                     | A primary key unique identifier for the ObservedProperty.                                                                          | UUID      |
| O        | workspace_id           | A foreign key identifier for the Workspace that owns the ObservedProperty. If omitted, the ObservedProperty is shared system-wide. | UUID      |
| M        | name                   | A descriptive name for the ObservedProperty.                                                                                       | String    |
| M        | definition             | A text definition of the ObservedProperty or a URL pointing to a controlled definition.                                            | Text      |
| M        | description            | A text description of the ObservedProperty.                                                                                        | Text      |
| M        | observed_property_type | The type of ObservedProperty.                                                                                                      | String    |
| M        | code                   | A brief text code identifying the ObservedProperty.                                                                                | String    |

## Organization

An Organization is a body of people having a particular purpose, such as a business, agency, research group, or laboratory.

| Required | Attribute         | Definition                                              | Data Type  |
| -------- | ----------------- | ------------------------------------------------------- | ---------- |
| M        | id                | A primary key unique identifier for the Organization.   | BigInteger |
| M        | code              | A brief text code or abbreviation for the Organization. | String     |
| M        | name              | A descriptive name for the Organization.                | String     |
| O        | description       | A text description of the Organization.                 | Text       |
| O        | link              | A URL pointing to a website for the Organization.       | URL        |
| M        | organization_type | A text string indicating the type of Organization.      | String     |

## User

Individual users who own workspaces, collaborate on data management, or manage account information in HydroServer.

| Required | Attribute            | Definition                                                                                                                                                                                                | Data Type  |
| -------- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| M        | id                   | A primary key unique identifier for the User.                                                                                                                                                             | BigInteger |
| M        | username             | The Django username field. HydroServer keeps this synchronized to the user's email address.                                                                                                               | String     |
| M        | password             | The stored password hash.                                                                                                                                                                                 | String     |
| O        | last_login           | The datetime when the User last logged in.                                                                                                                                                                | Datetime   |
| M        | is_superuser         | A boolean value indicating whether the User bypasses explicit permission assignments.                                                                                                                     | Boolean    |
| O        | first_name           | The User's first name.                                                                                                                                                                                    | String     |
| O        | middle_name          | The User's middle name.                                                                                                                                                                                   | String     |
| O        | last_name            | The User's last name.                                                                                                                                                                                     | String     |
| M        | email                | The User's contact email address.                                                                                                                                                                         | String     |
| M        | is_staff             | A boolean value indicating whether the User can access the Django admin site.                                                                                                                             | Boolean    |
| M        | is_active            | A boolean value indicating whether the account is active.                                                                                                                                                 | Boolean    |
| M        | date_joined          | The datetime when the User account was created.                                                                                                                                                           | Datetime   |
| O        | phone                | The User's contact phone number.                                                                                                                                                                          | String     |
| O        | address              | The User's physical mailing address.                                                                                                                                                                      | String     |
| O        | link                 | A URL pointing to a website for the User.                                                                                                                                                                 | URL        |
| M        | user_type            | A text string indicating the type of User.                                                                                                                                                                | String     |
| O        | organization_id      | A one-to-one identifier for the Organization with which the User is affiliated. Each User may be affiliated with at most one Organization, and each Organization may be affiliated with at most one User. | BigInteger |
| M        | is_ownership_allowed | A boolean value indicating whether the User may own workspaces.                                                                                                                                           | Boolean    |

**NOTE**: `groups` and `user_permissions` are also persisted through Django auth many-to-many join tables, but they are not columns on the `User` row itself.

## ProcessingLevel

The degree of quality control or processing to which a Datastream has been subjected.

| Required | Attribute    | Definition                                                                                                                       | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the ProcessingLevel.                                                                         | UUID      |
| O        | workspace_id | A foreign key identifier for the Workspace that owns the ProcessingLevel. If omitted, the ProcessingLevel is shared system-wide. | UUID      |
| M        | code         | A brief text code identifying the ProcessingLevel.                                                                               | String    |
| O        | definition   | A text definition of the ProcessingLevel.                                                                                        | Text      |
| O        | explanation  | A longer text explanation of the ProcessingLevel.                                                                                | Text      |

## ResultQualifier

Data qualifying comments added to individual data values to qualify their interpretation or use.

| Required | Attribute    | Definition                                                                                                                       | Data Type |
| -------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the ResultQualifier.                                                                         | UUID      |
| O        | workspace_id | A foreign key identifier for the Workspace that owns the ResultQualifier. If omitted, the ResultQualifier is shared system-wide. | UUID      |
| M        | code         | A brief text code identifying the ResultQualifier.                                                                               | String    |
| M        | description  | A longer text description or explanation of the ResultQualifier.                                                                 | Text      |

**NOTE**: The database enforces a unique constraint on `(code, workspace_id)`, including the system-wide `NULL` workspace scope.

## Sensor

A Sensor is an instrument, method, or procedure used to produce Observations for a Datastream.

| Required | Attribute         | Definition                                                                                                     | Data Type |
| -------- | ----------------- | -------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                | A primary key unique identifier for the Sensor.                                                                | UUID      |
| O        | workspace_id      | A foreign key identifier for the Workspace that owns the Sensor. If omitted, the Sensor is shared system-wide. | UUID      |
| M        | name              | A descriptive name for the Sensor.                                                                             | String    |
| M        | description       | A longer text description of the Sensor.                                                                       | Text      |
| M        | encoding_type     | A string indicating how the Sensor information is encoded.                                                     | String    |
| O        | method_code       | A brief text code identifying the Sensor or method.                                                            | String    |
| M        | method_type       | A text string indicating the type of Sensor or method.                                                         | String    |
| O        | method_link       | A URL pointing to documentation that defines or describes the Sensor or method.                                | String    |
| O        | manufacturer      | The name of the Sensor manufacturer.                                                                           | String    |
| O        | sensor_model      | The name of the Sensor model.                                                                                  | String    |
| O        | sensor_model_link | A URL pointing to documentation for the Sensor model.                                                          | String    |

**NOTE**: HydroServer uses the Sensor entity for both physical instruments and derived methods or procedures, such as transformations or rating-curve-derived values.

## Thing

A Thing is an object of the physical world or information world that is capable of being identified and integrated into communication networks. In the context of HydroServer, a Thing is typically a monitoring station or site.

| Required | Attribute             | Definition                                                                                                          | Data Type |
| -------- | --------------------- | ------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                    | A primary key unique identifier for the Thing.                                                                      | UUID      |
| M        | workspace_id          | A foreign key identifier for the Workspace that owns the Thing.                                                     | UUID      |
| M        | name                  | A text string giving a name for the Thing.                                                                          | String    |
| M        | description           | A text string giving a description for the Thing.                                                                   | Text      |
| M        | sampling_feature_type | A text string specifying the type of sampling feature.                                                              | String    |
| M        | sampling_feature_code | A text string specifying a shortened code identifying the Thing.                                                    | String    |
| M        | site_type             | A text string specifying the type of site represented by the Thing.                                                 | String    |
| M        | is_private            | An access control flag indicating whether the Thing is discoverable and whether its metadata is publicly available. | Boolean   |
| O        | data_disclaimer       | A text string displayed with the Thing's data to specify any disclaimer.                                            | Text      |

## ThingTag

A key-value tag associated with a Thing.

| Required | Attribute | Definition                                                       | Data Type  |
| -------- | --------- | ---------------------------------------------------------------- | ---------- |
| M        | id        | A primary key unique identifier for the ThingTag.                | BigInteger |
| M        | thing_id  | A foreign key identifier for the Thing to which the tag belongs. | UUID       |
| M        | key       | The tag key.                                                     | String     |
| M        | value     | The tag value.                                                   | String     |

## ThingFileAttachment

A file attached to a Thing, such as a site photo, document, or supporting artifact.

| Required | Attribute            | Definition                                                                   | Data Type  |
| -------- | -------------------- | ---------------------------------------------------------------------------- | ---------- |
| M        | id                   | A primary key unique identifier for the ThingFileAttachment.                 | BigInteger |
| M        | thing_id             | A foreign key identifier for the Thing to which the file attachment belongs. | UUID       |
| M        | name                 | The name of the attached file.                                               | String     |
| O        | description          | A text description of the attached file.                                     | Text       |
| M        | file_attachment      | The stored file object for the attachment.                                   | File       |
| M        | file_attachment_type | A text string identifying the type of file attachment.                       | String     |

**NOTE**: The database enforces a unique constraint on `(thing_id, name)`.

## Unit

The unit of measure associated with the Observations within a Datastream.

| Required | Attribute    | Definition                                                                                                 | Data Type |
| -------- | ------------ | ---------------------------------------------------------------------------------------------------------- | --------- |
| M        | id           | A primary key unique identifier for the Unit.                                                              | UUID      |
| O        | workspace_id | A foreign key identifier for the Workspace that owns the Unit. If omitted, the Unit is shared system-wide. | UUID      |
| M        | name         | A descriptive name for the Unit.                                                                           | String    |
| M        | symbol       | An abbreviation or symbol used for the Unit.                                                               | String    |
| M        | definition   | A URL or text definition for the Unit.                                                                     | Text      |
| M        | unit_type    | The type of Unit.                                                                                          | String    |

## Workspace

A Workspace is the ownership and access-control boundary for most HydroServer-managed resources.

| Required | Attribute  | Definition                                                          | Data Type  |
| -------- | ---------- | ------------------------------------------------------------------- | ---------- |
| M        | id         | A primary key unique identifier for the Workspace.                  | UUID       |
| M        | name       | A descriptive name for the Workspace.                               | String     |
| M        | owner_id   | A foreign key identifier for the User who owns the Workspace.       | BigInteger |
| M        | is_private | An access control flag indicating whether the Workspace is private. | Boolean    |

**NOTE**: The database enforces a unique constraint on `(name, owner_id)`.

## WorkspaceTransferConfirmation

A pending transfer record used when ownership of a Workspace is being transferred to another User.

| Required | Attribute    | Definition                                                             | Data Type  |
| -------- | ------------ | ---------------------------------------------------------------------- | ---------- |
| M        | id           | A primary key unique identifier for the WorkspaceTransferConfirmation. | BigInteger |
| M        | workspace_id | A foreign key identifier for the Workspace being transferred.          | UUID       |
| M        | new_owner_id | A foreign key identifier for the new owner.                            | BigInteger |
| M        | initiated    | The datetime when the transfer was initiated.                          | Datetime   |

## WorkspaceDeleteConfirmation

A pending confirmation record used when a Workspace deletion has been initiated.

| Required | Attribute    | Definition                                                           | Data Type  |
| -------- | ------------ | -------------------------------------------------------------------- | ---------- |
| M        | id           | A primary key unique identifier for the WorkspaceDeleteConfirmation. | BigInteger |
| M        | workspace_id | A foreign key identifier for the Workspace to be deleted.            | UUID       |
| M        | initiated    | The datetime when deletion confirmation was initiated.               | Datetime   |

## Role

A Role is a named collection of permissions that can be assigned to collaborators or API keys.

| Required | Attribute      | Definition                                                                                                 | Data Type |
| -------- | -------------- | ---------------------------------------------------------------------------------------------------------- | --------- |
| M        | id             | A primary key unique identifier for the Role.                                                              | UUID      |
| O        | workspace_id   | A foreign key identifier for the Workspace that owns the Role. If omitted, the Role is shared system-wide. | UUID      |
| M        | name           | A descriptive name for the Role.                                                                           | String    |
| O        | description    | A text description of the Role.                                                                            | Text      |
| M        | is_user_role   | A boolean value indicating whether the Role may be assigned to a User collaborator.                        | Boolean   |
| M        | is_apikey_role | A boolean value indicating whether the Role may be assigned to an API key.                                 | Boolean   |

## Permission

A Permission associates a Role with an allowed action on a resource type.

| Required | Attribute       | Definition                                                                | Data Type  |
| -------- | --------------- | ------------------------------------------------------------------------- | ---------- |
| M        | id              | A primary key unique identifier for the Permission.                       | BigInteger |
| M        | role_id         | A foreign key identifier for the Role to which the Permission belongs.    | UUID       |
| M        | permission_type | The permitted action, such as `view`, `create`, `edit`, `delete`, or `*`. | String     |
| M        | resource_type   | The resource type to which the Permission applies.                        | String     |

## Collaborator

A Collaborator associates a User with a Workspace through a Role.

| Required | Attribute    | Definition                                                          | Data Type  |
| -------- | ------------ | ------------------------------------------------------------------- | ---------- |
| M        | id           | A primary key unique identifier for the Collaborator.               | BigInteger |
| M        | workspace_id | A foreign key identifier for the Workspace.                         | UUID       |
| M        | user_id      | A foreign key identifier for the collaborating User.                | BigInteger |
| M        | role_id      | A foreign key identifier for the Role assigned to the Collaborator. | UUID       |

**NOTE**: The database enforces a unique constraint on `(user_id, workspace_id)`.

## APIKey

An APIKey grants non-interactive access to a Workspace using an assigned Role.

| Required | Attribute    | Definition                                                               | Data Type |
| -------- | ------------ | ------------------------------------------------------------------------ | --------- |
| M        | id           | A primary key unique identifier for the APIKey.                          | UUID      |
| M        | workspace_id | A foreign key identifier for the Workspace to which the API key belongs. | UUID      |
| M        | role_id      | A foreign key identifier for the Role assigned to the API key.           | UUID      |
| M        | name         | A descriptive name for the API key.                                      | String    |
| O        | description  | A text description of the API key.                                       | Text      |
| M        | created_at   | The datetime when the API key was created.                               | Datetime  |
| O        | expires_at   | The datetime when the API key expires.                                   | Datetime  |
| O        | last_used    | The datetime when the API key was last used.                             | Datetime  |
| M        | is_active    | A boolean value indicating whether the API key is active.                | Boolean   |
| M        | hashed_key   | The stored hashed representation of the API key secret.                  | String    |

## DatastreamTag

A key-value tag associated with a Datastream.

| Required | Attribute     | Definition                                                            | Data Type  |
| -------- | ------------- | --------------------------------------------------------------------- | ---------- |
| M        | id            | A primary key unique identifier for the DatastreamTag.                | BigInteger |
| M        | datastream_id | A foreign key identifier for the Datastream to which the tag belongs. | UUID       |
| M        | key           | The tag key.                                                          | String     |
| M        | value         | The tag value.                                                        | String     |

## DatastreamFileAttachment

A file attached to a Datastream.

| Required | Attribute            | Definition                                                                        | Data Type  |
| -------- | -------------------- | --------------------------------------------------------------------------------- | ---------- |
| M        | id                   | A primary key unique identifier for the DatastreamFileAttachment.                 | BigInteger |
| M        | datastream_id        | A foreign key identifier for the Datastream to which the file attachment belongs. | UUID       |
| M        | name                 | The name of the attached file.                                                    | String     |
| O        | description          | A text description of the attached file.                                          | Text       |
| M        | file_attachment      | The stored file object for the attachment.                                        | File       |
| M        | file_attachment_type | A text string identifying the type of file attachment.                            | String     |

**NOTE**: The database enforces a unique constraint on `(datastream_id, name)`.

## OrchestrationSystem

An OrchestrationSystem identifies the engine or environment used to run automated HydroServer tasks.

| Required | Attribute                 | Definition                                                                                                                               | Data Type |
| -------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| M        | id                        | A primary key unique identifier for the OrchestrationSystem.                                                                             | UUID      |
| O        | workspace_id              | A foreign key identifier for the Workspace that owns the OrchestrationSystem. If omitted, the OrchestrationSystem is shared system-wide. | UUID      |
| M        | name                      | A descriptive name for the OrchestrationSystem.                                                                                          | String    |
| M        | orchestration_system_type | A text string indicating the type of orchestration system.                                                                               | String    |

## DataConnection

A DataConnection stores the extraction, transformation, and loading configuration used by HydroServer ETL tasks.

| Required | Attribute            | Definition                                                                                                                     | Data Type |
| -------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------- |
| M        | id                   | A primary key unique identifier for the DataConnection.                                                                        | UUID      |
| M        | name                 | A descriptive name for the DataConnection.                                                                                     | String    |
| M        | data_connection_type | A text string indicating the type of DataConnection.                                                                           | String    |
| O        | workspace_id         | A foreign key identifier for the Workspace that owns the DataConnection. If omitted, the DataConnection is shared system-wide. | UUID      |
| O        | extractor_type       | The type of extractor configured for the DataConnection.                                                                       | String    |
| M        | extractor_settings   | A JSON object storing extractor configuration settings.                                                                        | JSON      |
| O        | transformer_type     | The type of transformer configured for the DataConnection.                                                                     | String    |
| M        | transformer_settings | A JSON object storing transformer configuration settings.                                                                      | JSON      |
| O        | loader_type          | The type of loader configured for the DataConnection.                                                                          | String    |
| M        | loader_settings      | A JSON object storing loader configuration settings.                                                                           | JSON      |

## DataConnectionNotificationRecipient

A notification email recipient associated with a DataConnection.

| Required | Attribute          | Definition                                                                   | Data Type  |
| -------- | ------------------ | ---------------------------------------------------------------------------- | ---------- |
| M        | id                 | A primary key unique identifier for the DataConnectionNotificationRecipient. | BigInteger |
| M        | data_connection_id | A foreign key identifier for the DataConnection.                             | UUID       |
| M        | email              | An email address that receives notifications for the DataConnection.         | Email      |

**NOTE**: The database enforces a unique constraint on `(data_connection_id, email)`.

## Task

A Task defines an automated HydroServer workflow, including the associated DataConnection, orchestration target, schedule, and runtime variables.

| Required | Attribute               | Definition                                                                                                                                   | Data Type  |
| -------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| M        | id                      | A primary key unique identifier for the Task.                                                                                                | UUID       |
| M        | name                    | A descriptive name for the Task.                                                                                                             | String     |
| M        | task_type               | A text string indicating the Task type. The database stores this as a free-form string with a default of `ETL`; it does not enforce an enum. | String     |
| M        | workspace_id            | A foreign key identifier for the Workspace that owns the Task.                                                                               | UUID       |
| O        | data_connection_id      | A foreign key identifier for the DataConnection used by the Task.                                                                            | UUID       |
| M        | orchestration_system_id | A foreign key identifier for the OrchestrationSystem used by the Task.                                                                       | UUID       |
| O        | periodic_task_id        | A one-to-one identifier for the associated scheduler record in `django_celery_beat`. Each Task maps to at most one periodic task record.     | BigInteger |
| M        | paused                  | A boolean value indicating whether the Task is paused.                                                                                       | Boolean    |
| O        | next_run_at             | The datetime when the Task is expected to run next.                                                                                          | Datetime   |
| M        | extractor_variables     | A JSON object storing runtime variables for the extractor.                                                                                   | JSON       |
| M        | transformer_variables   | A JSON object storing runtime variables for the transformer.                                                                                 | JSON       |
| M        | loader_variables        | A JSON object storing runtime variables for the loader.                                                                                      | JSON       |

## TaskMapping

A TaskMapping associates an incoming source identifier with one or more target mapping paths.

| Required | Attribute         | Definition                                                          | Data Type |
| -------- | ----------------- | ------------------------------------------------------------------- | --------- |
| M        | id                | A primary key unique identifier for the TaskMapping.                | UUID      |
| M        | task_id           | A foreign key identifier for the Task to which the mapping belongs. | UUID      |
| M        | source_identifier | A text identifier representing an incoming source field or path.    | String    |

## TaskMappingPath

A TaskMappingPath maps a source identifier to a target identifier and any configured transformations.

| Required | Attribute            | Definition                                                                 | Data Type |
| -------- | -------------------- | -------------------------------------------------------------------------- | --------- |
| M        | id                   | A primary key unique identifier for the TaskMappingPath.                   | UUID      |
| M        | task_mapping_id      | A foreign key identifier for the TaskMapping to which the path belongs.    | UUID      |
| M        | target_identifier    | A text identifier representing the destination field or path.              | String    |
| M        | data_transformations | A JSON array of transformation definitions applied along the mapping path. | JSON      |

## TaskRun

A TaskRun stores the execution history for a Task.

| Required | Attribute   | Definition                                                      | Data Type |
| -------- | ----------- | --------------------------------------------------------------- | --------- |
| M        | id          | A primary key unique identifier for the TaskRun.                | UUID      |
| M        | task_id     | A foreign key identifier for the Task to which the run belongs. | UUID      |
| M        | status      | A text string indicating the run status.                        | String    |
| M        | started_at  | The datetime when the TaskRun started.                          | Datetime  |
| O        | finished_at | The datetime when the TaskRun finished.                         | Datetime  |
| O        | result      | A JSON object storing execution result details.                 | JSON      |

## Controlled Vocabulary Tables

HydroServer also includes simple lookup tables that primarily store controlled vocabulary terms used by the main entities.

| Table                   | Attributes             | Data Type                   |
| ----------------------- | ---------------------- | --------------------------- |
| `UserType`              | `id`, `name`, `public` | BigInteger, String, Boolean |
| `OrganizationType`      | `id`, `name`, `public` | BigInteger, String, Boolean |
| `SiteType`              | `id`, `name`           | BigInteger, String          |
| `SamplingFeatureType`   | `id`, `name`           | BigInteger, String          |
| `FileAttachmentType`    | `id`, `name`           | BigInteger, String          |
| `VariableType`          | `id`, `name`           | BigInteger, String          |
| `SensorEncodingType`    | `id`, `name`           | BigInteger, String          |
| `MethodType`            | `id`, `name`           | BigInteger, String          |
| `UnitType`              | `id`, `name`           | BigInteger, String          |
| `DatastreamAggregation` | `id`, `name`           | BigInteger, String          |
| `DatastreamStatus`      | `id`, `name`           | BigInteger, String          |
| `SampledMedium`         | `id`, `name`           | BigInteger, String          |

## SensorThings Conceptual Entities

The current HydroServer SensorThings implementation still exposes SensorThings concepts that are not represented as first-class HydroServer database tables.

### FeatureOfInterest

HydroServer currently derives FeatureOfInterest behavior from the Thing and Location context used by SensorThings responses rather than storing FeatureOfInterest as a first-class HydroServer model.

| Required | Attribute   | Definition                                                                           | Data Type |
| -------- | ----------- | ------------------------------------------------------------------------------------ | --------- |
| M        | id          | A primary key unique identifier for the FeatureOfInterest in SensorThings responses. | UUID      |
| M        | name        | A text string giving the name of the feature.                                        | String    |
| M        | description | A text string providing a description of the feature.                                | String    |
| M        | encoding    | A text string describing the encoding in which the feature is expressed.             | String    |
| M        | feature     | A GeoJSON encoding of the geometry of the feature.                                   | Object    |

### HistoricalLocation

HydroServer currently exposes HistoricalLocation through SensorThings but does not store it as a first-class HydroServer model in the main domain packages.

| Required | Attribute   | Definition                                                                            | Data Type |
| -------- | ----------- | ------------------------------------------------------------------------------------- | --------- |
| M        | thing_id    | A foreign key identifier for the Thing for which the HistoricalLocation is specified. | UUID      |
| M        | time        | The time when the Thing is known to be at the Location.                               | Datetime  |
| M        | location_id | A foreign key identifier for the Location.                                            | UUID      |
