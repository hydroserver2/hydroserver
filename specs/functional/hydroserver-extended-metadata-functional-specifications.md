# HydroServer Extended Metadata

_Functional Specifications_

Last Updated: January 7, 2026

## 1 Introduction


This is just initial ideas for implementing extended metadata on HydroServer’s data model using JSONB fields in PostgreSQL. This may eventually be expanded into a more complete functional specifications document if we decide the idea is worth pursuing.
## 2 Data Model Design

To support the storage of extended metadata, an indexed JSONB field called properties will be added to the following tables:
- Thing
- Datastream
- Observation
- Sensor
- ObservedProperty
- ProcessingLevel

The following tables will be removed and their existing contents migrated to corresponding properties:
- ThingTag → Thing.properties
- DatastreamTag → Datastream.properties
- ResultQualifier → Observation.properties

To support validation and enforcement of extended metadata, a new table called PropertySchema will be created with the following attributes:

PropertySchema
PK
(M) id
UUID

(M) name
String

(M) description
String

(M) type
String

(M) enabled
Boolean

(M) schema
JSONB
FK
(O) workspaceId
UUID

The schema field will contain a valid JSON Schema, which will be applied within either the given workspace, or globally if no workspace is provided. The type field defines which table properties the schema will be applied to, which must be one of Thing, Datastream, Observation, Sensor, ObservedProperty, or ProcessingLevel. The enabled field controls whether JSON Schema validation will be applied to incoming data.
## 3 JSON Schema Validation

JSON Schema validation on properties fields is optional; by default, properties fields will allow any valid JSON object to be entered, similar to HydroServer’s existing tagging functionality. To enable property validation, users must define and upload a JSON Schema document to HydroServer.

PostgreSQL cannot guarantee JSONB columns are valid against a JSON Schema, so validation must be performed when data are created or updated through the API. Validation will only be performed on data ingest, not egress. Data inserted or updated through a direct database connection will not be validated.

This behavior means that properties will not be automatically validated retroactively when a JSON Schema is applied or updated; these will need to be updated manually over time, such as when a user wants to add a new property to a record, they may need to also update old invalid properties if they no longer pass validation. Alternatively, an external script could automatically handle property data migrations when a schema is added or modified.

If more than one JSON Schema has been applied to the same data table, HydroServer will validate the properties against both schemas. Users and admins will need to take care not to apply mutually exclusive schemas to the same data table.

Example 1: Thing properties JSON schema to add distribution system and comment metadata fields.

{
  "type": "object",
  "properties": {
    "distributionSystem": {
      "type": "string",
      "enum": [
        "PROVO RIVER",
        "LOGAN RIVER"
      ],
      "description": "The distribution system the site belongs to."
    },
    "comments": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "comment": {
            "type": "string",
            "description": "The comment text."
          },
          "date": {
            "type": "string",
            "format": "date-time",
            "description": "When the comment was created."
          },
          "author": {
            "type": "string",
            "description": "Who authored the comment."
          }
        },
        "required": ["comment", "date", "author"],
        "additionalProperties": false
      },
      "description": "A list of comments associated with the site."
    }
  },
  "required": ["distributionSystem"],
  "additionalProperties": true
}

The above JSON Schema (applied to Things) requires a distributionSystem property whose value must be either "PROVO RIVER" or "LOGAN RIVER". It also allows an optional comments field, which is an array of objects; each comment must include comment, date, and author fields. Additional Thing properties beyond these two fields are allowed by this schema. The schema would be stored in the PropertySchema table and applied either globally or to a specific workspace.

Below is an example valid Thing properties object according to this schema:

{
  "distributionSystem": "LOGAN RIVER",
  "comments": [
    {
      "comment": "Minor sediment observed near intake.",
      "date": "2026-01-06T15:45:00Z",
      "author": "Bob"
    }
  ]
}

Example 2: Observation properties JSON schema to add optional quality flag metadata field.

{
  "type": "object",
  "properties": {
    "qualityFlag": {
      "type": "string",
      "enum": [
        "GOOD",
        "SUSPICIOUS",
        "BAD"
      ]
    }
  },
  "additionalProperties": false
}

The above JSON Schema (applied to Observations) allows an optional property called qualityFlag on observations whose value must be one of “GOOD”, “SUSPICIOUS”, or “BAD”. No other properties are allowed by this schema.

Below is an example valid Observation properties object according to this schema:

{
  "qualityFlag": "SUSPICIOUS"
}

Below is an example of an invalid Observation properties object that would be rejected by this schema because it contains an extra unallowed property, and the qualityFlag is not one of the allowed values:

{
  "qualityFlag": "OKAY",
  "comment": "This value looks fine to me.",
}
## 4 Additional Considerations

Performance and Scaling Implications
JSONB properties would be indexed in PostgreSQL using a GIN index. This type of index enables better filtering on JSONB fields, but it adds extra overhead on data ingestion and updates because the index needs to be updated and maintained. These indexes can also become quite large, especially for deeply nested data or very large tables like observations.

Filtering on properties and data inserts would need to be tested extensively on observations. The size, density, and uniformity of observation properties could significantly impact performance on both observation inserts and GET operations filtered by properties. The LRO staging instance would be a useful place to quickly test these features.

JSON Schema validation may also separately impact observation insert performance if the observations contain many properties that need to be validated.

The performance of data reads that are not filtered by properties should not be impacted by these features since validation will not happen on egress, and there may even be performance benefits by removing existing tagging/qualifier tables as fewer joins will need to be done to fetch data.
JSON Schema Granularity
The above design allows JSON Schemas to either be applied globally, or within specific workspaces. Additional control over the application of schema validation could be enabled by attaching schemas to specific records. For example, if a user wants a schema to apply only to observations of a specific subset of sites within a workspace, they would need to be able to associate a PropertySchema with a Thing, so only Observations belonging to Datastreams of that Thing are validated against the schema. This would require a many-to-many relationship between PropertySchemas and all tables with properties fields (Things, Datastreams, Observations, etc). This isn’t impossible, but it does make the model and maintaining the schemas more complicated.
HydroServer Data Model Cleanup
We may want to eventually migrate or remove some currently unused fields in HydroServer’s database model to properties fields. The following could be up for consideration:

- Thing
- SamplingFeatureType — Currently hardcoded to “Site” for all things.
- Datastream
- ObservationType — Currently hardcoded to “OM_Measurement” for all datastreams.
- ResultType — Currently hardcoded to “Time Series Coverage” for all datastreams.
- ResultBeginTime — Defaults to null.
- ResultEndTime — Defaults to null.
- Observation
- ResultTime — Defaults to null. This is required by SensorThings and should default to the PhenomenonTime.
- QualityCode — Defaults to null.
SensorThings Field Mappings
Properties could enable us to eventually do some useful mappings to SensorThings if we choose to do so. For example, users cannot currently define the name that appears in the STA Locations endpoints, it just defaults to “Location for {thing_name}”. We could look into having SensorThings treat a Thing property called “LocationName” as an override for the Location name that gets used in the SensorThings API instead of appearing as a Location or Thing STA property. We’d obviously need to document this behavior somewhere and it’s not necessarily super trivial to implement, but it could be an option down the road.
