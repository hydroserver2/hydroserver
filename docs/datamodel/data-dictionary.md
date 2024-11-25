# HydroServer Data Model Data Dictionary

This document describes the entities and attributes within the HydroServer data model. 

## Datastream

A Datastream groups a collection of Observations measuring the same ObservedProperty and produced by the same Sensor. Each instance of a Datastream represents the properties for a time series of Observations.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the datastream. | UUID |
| M |name | A text name for the datastream. Can be auto generated. | String |
| M | description| A text description for the datastream. Can be auto generated | String |
| M | sensorId | Foreign key identifier for the Sensor (method) used to create the Datasteam | UUID |
| M | thingId | Foreign key identifier for the thing on which or at which the Datastream was created. | UUID |
| M | observedPropertyID | Foreign key identifier for the observed property associated with the Datastream | UUID |
| M | unitId | Foreign key identifier for the units of measure in which the Observations within the Datastream are stored | UUID |
| M | observationType | The type of Observation derived from a list of observation types - "Field Observation" or "Derived Value" | String |
| M | resultType | The specific type of result represented by the Datastream. All time series are of type "Time series coverage". | String |
| O | status | A string value indicating the status of data collection/creation for the Datastream. | String |
| M | sampledMedium | The environmental media that is sampled by the Datastream (e.g., air, water, snow, etc.). | Boolean |
| O | valueCount | The number of Observations within the Datastream. | Integer |
| M | noDataValue | A numeric value stored to indicate the absence of data (e.g., -9999). | Float |
| M | processingLevelId | A foreign key identifier indicating the ProcessingLevel for the Datastream | UUID |
| O | intendedTimeSpacing | A numeric value indicating the intended time spacing for Observations within the Datastream. | Float |
| O | intendedTimeSpacingUnits | A foreign key identifier indicating the Units for the intendedTimeSpacing. | UUID |
| M | aggregationStatistic | A string indicating the recorded aggregation statistics for the Datastream (e.g., minimum, maximum, mean, etc.) | String |
| M | timeAggregationInterval | A numeric value indicating the time interval over which recorded Observations were aggregated - i.e., the temporal footprint for each recorded Observation. | Float |
| M | timeAggregationIntervalUnitsID | A foreign key identifier indicating the Units for the timeAggregationInterval. | UUID |
| M | isVisible | An access control flag indicating whether the Datastream metadata is publicly visible. | Boolean |
| M | isDataVisible | An access control flag indicating whether the Observations for the Datastream are visible. | Boolean |
| O | dataSource | A string storing a path to a file from which the Datastream is loaded using the HydroServer Streaming Data Loader software. | String |
| O | dataSourceColumn | A string storing the name of the column in the file from which the Datastream is loaded using the HydroServer Streaming Data Loader software. | String |
| M | archived | A boolean indicating whether the Datastream has been set up to archive to HydroShare or not. | Boolean |
| O | observedArea | The spatial bounding box or spatial extent (point) that belong to the Observations associated with this Datastream. | Object |
| O | phenomenonBeginTime | The Datetime at which the activity began that results in the Datastream's Observations. May be the same as resultBeginTime. | Datetime |
| O | phenomenonEndTime | The Datetime at which the activity ends that results in the Datastream's Observations. May be the same as resultEndTime. | Datetime |
| O | resultBeginTime | The timestamp of the first Observation in the Datastream. | Datetime |
| O | resultEndTime | The timestamp of the last Observation in the Datastream. | Datetime |

## FeatureOfInterest

An Observation results in a value being assigned to a phenomenon. The phenomenon is a property of a feature, the latter being the FeatureOfInterest of the Observation. The FeatureOfInterest may be a real-world feature such as a stream reach, watershed, aquifer, etc. 

**NOTE**: The SensorThings API specification treats FeatureOfInterest as a required attribute for each Observation. The FeatureOfInterest is allowed to be the same as the Location of the Thing (the Location of the monitoring site) associated with an Observation. So, for simplicity, HydroServer adopts this convention and uses the Location of the Thing as the default FeatureOfInterest for Observations associated with a Thing.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Feature. | UUID |
| M | name | A text string giving the name of the feature. | String |
| M | description | A text string providing a description of the feature. | String |
| M | encoding | A text string describing the encoding in which the feature is expressed - typicaly "GeoJSON". | String |
| M | feature | A GeoJSON encoding of the geometry of the feature. | Object |

## HistoricalLocation

A Thing’s HistoricalLocation entity set (the set of records specifying historical locations for a Thing) provides the times of the current (i.e., last known) and previous locations of the Thing. It is not uncommon for a monitoring site to change locations over time as instrumentation is changed or for other reasons. Thus HistoricalLocation can be used to track these changes.

**Note**: HydroServer currently assumes that a Thing has a single Location that is specified in the Location entity. Thus, in its current implementation, HydroServer's web user interfaces do not allow specification of different historical locations for a Thing. This will likely be updated with future versions of HydroServer. 

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | thingId | A foreign key identifer for the Thing for which the HistoricalLocation is specified. | UUID |
| M | time | The time when the Thing is known to be at the Location. | Datetime |
| M | locationId | A foreign key identifier for the Location. | UUID |

## Location

The Location entity locates the Thing. A Thing’s Location entity is defined as the last known location of the Thing. In the context of Things that are monitoring sites, this is the physical location of the monitoring site.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Location. | UUID |
| M | name | A text string name for the Location. Can be the same as the name of the Thing. | String |
| M | description | A text string description for the Location. Can be the same as the name of the Thing. | String |
| M | encodingType | The encoding type of the Location - usually "GeoJSON". | String |
| M | latitude | A floating point number representing the latitude of the location using WGS84 coordinates. | Float |
| M | longitude | A floating point number representing the longitude of the location using WGS84 coordinates. | Float |
| O | elevation_m | A floating point number representing the elevation of the location in meters. | Float |
| O | elevationDatum | A string indicating the elevation datum used by the site to specify the elevation. | String |
| O | state | The name of the state in which the Location resides. | String |
| O | county | The name of the county in which the Location resides. | String |
| O | country | The name of the country in which the Location resides. | String |

## Observation

An Observation is the act of measuring or otherwise determining the value of a property, including its numeric result and the date/time at which it was observed.

**NOTE**: Because HydroShare assumes that the FeatureOfInterest associated with an Observation is the same as the Location of the Thing with which the Observation is associated, the FeatureOfInterestId is not currently stored in the Observation entity by HydroServer even though it is a required attribute. HydroServer's SensorThings API satisfies this requirement by returning the ID of the Thing as the FeatureOfInterest when Observations are requested via the HydroServer SensorThings API.

**NOTE**: validBeginTime and validEndTime are attributes that participate in the SensorThings data model, but are not used by HydrServer.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Observation | UUID |
| M | datastreamId | A foreign key identifier for the Datastream to which the observation belongs. | UUID |
| M | featureOfInterestId | A foreign key identifier for the FeatureOfInterest the Observation represents. | UUID |
| M | phenomenonTime | A datetime value indicating the time instant when the Observation happens. | Datetime |
| M | result | The numeric value of the Observation. The estimated value of an ObservedProperty from the Observation. | Float |
| O | resultTime | The time that the Observation's result was generated (if different than the phenomenonTime). NOTE: It is possible for a device to make an Observation of a phenomenon at a particular time (phenomenonTime) but not generate the numeric value of the result until some time later (resultTime). | Datetime |
| O | qualityCode | A text code or string indicating the quality of the Observation. | String |
| O | resultQualifiers | An array containing the foreign key identifiers for any data qualifying comments (ResultQualifiers) that have been applied to the Observation. | Array |
| O | validBeginTime | The beginning time for a time period during which the result may be used. | Datetime |
| O | ValidEndTime | The ending time for a time period during which the result may be used. | Datetime |

## ObservedProperty

An ObservedProperty specifies the phenomenon of an Observation (e.g., flow, temperature, pH, dissolved oxygen concentration, etc.).

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the ObservedProperty. | UUID |
| O | personId | A foreign key identifier for the Person who owns the ObservedProperty. | Integer |
| M | name | A descriptive name for the ObservedProperty - preferably chosen from a controlled vocabulary.  | String |
| M | definition | A text string providing a definition of the ObservedProperty or a URL pointing to a definition of the ObservedProperty - e.g., a URL pointing to the controlled vocabulary that defines the observed property. | URL |
| M | description | A text description of the ObservedProperty. May be the same as the definition of the ObservedProperty. | String |
| M | type | The type of ObservedProperty - preferably selected from a controlled vocabulary (e.g., Hydrology, Instrumentation, Climate, Soil, Water Quality, etc.). | String |
| M | code | A brief text code identifying the ObservedProperty. | String |

## Organization

An Organization is a body of people having a particular purpose, in particular a business, agency, research group, research institute, etc. For HydroServer, this is the Organization with which a Person involved in data collection is affiliated.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Organization. | String |
| M | code | A brief text code or abbreviation for the name of the Organization. | String |
| M | name | A descriptive name for the Organization. | String |
| O | description | A text description of the Organization. | String |
| M | type | A text string indicating the type of Organization - preferably selected from a controlled vocabulary (e.g., University, Laboratory, Research Institute, State Agency, etc.) | String |
| O | link | A URL pointing at a website for the Organization. | URL |

## Person

Individual people who are involved in data collection or who are responsible for observational data stored in the database.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Person. | Integer |
| M | firstName | The Person's first given name. | String |
| O | middleName | The Person's middle name. | String |
| M | lastName | The person's last name. | String |
| O | phone | The person's contact phone number. | String |
| M | email | The person's contact email address. | String |
| O | unverifiedEmail | The person's contact email address prior to email verification. | String |
| O | address | The person's physical mailing address. | String |
| O | link | A URL pointing at a website for the person. | URL |
| M | type | A text string indicating the type of person - preferably selected from a controlled vocabulary (e.g., University Faculty, University Graduate Student, Professional or Research Staff) | String |
| M | isVerified | A boolean value indicating whether a user has verified their email account after creating a user account. | Boolean |
| O | organizationID | A foreign key identifier for the Organization with which the person is affiliated. | UUID |

## Photo

A photo of a Thing - e.g., photos of a monitoring site/location.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Photo. | UUID |
| M | thingId | A foreign key identifier for the Thing that is the subject of the photo. | UUID |
| M | filePath | A string providing the path for retrieving the photo file for display or download. | String |

## ProcessingLevel

The degree of quality control or processing to which a Datastream has been subjected. For example, raw versus quality controlled data.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the ProcessingLevel. | UUID |
| O | personId | A foreign key identifier for the Person who owns the ProcessingLevel. | Integer |
| M | code | A brief text code identifying the Processing level - e.g., "0" for "Raw data", "1" for "Quality controlled data." | String |
| O | definition | A text definition of the ProcessingLevel. | String |
| O | explanation | A longer text explanation of the ProcessingLevel. | String |

## ResultQualifier

Data qualifying comments added to individual data values to qualify their interpretation or use.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the ResultQualifier. | UUID |
| O | personId | A foreign key identifier for the Person who created the ResultQualifier. | Integer |
| M | code | A brief text code identifying the ResultQualifier. | String |
| M | description | A longer text description or explanation of the ResultQualifier. | String |

## Sensor

A Sensor is an instrument that observes a property or phenomenon with the goal of producing an estimate of the value of the property. 

**NOTE**: The SensorThings API data model uses the Sensor entity to describe the instrument used to make an Observation. However, some time series data are produced using a method or procedure whereby a Datastream is derived or created from another sensor Datastream (e.g., discharge derived from stage using a site-specific rating curve or daily data derived from 30-minute data through aggregation). In all cases, the "Sensor" entity is used to describe the method or procedure used to create Observations within a Datastream - even when there may not be a physical sensor involved or where data are derived from another Datastream.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Sensor. | UUID |
| O | personId | A foreign key identifier for the Person who created the Sensor. | Integer |
| M | name | A descriptive name for the Sensor. | String |
| M | description | A longer text description of the Sensor. | String |
| M | encodingType | A string indicating how the Sensor information is encoded by the API - "application/json" | String |
| O | methodCode | A brief text code identifying the Sensor/Method. | String |
| M | methodType | A string indicating the type of Sensor or Method - preferably chosen from a controlled vocabulary (e.g., "Instrument deployment"). | String |
| O | methodLink | A URL pointing to a website that defines or describes the Sensor/Method. | URL |
| O | manufacturer | The name of the Sensor manufacturer. | String |
| O | model | The name of the Sensor model. | String |
| O | modelLink | A URL for a website that describes the specific Sensor model. | URL |

## Thing

A thing is an object of the physical world (physical things) or the information world (virtual things) that is capable of being identified and integrated into communication networks. In the context of environmental monitoring and HydroServer, a Thing is a monitoring station or "Site" (e.g., a streamflow gage, water quality station, weather station, diversion measurement location, etc.).

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Thing. | UUID |
| M | name | A text string giving a name for the Thing. | String |
| M | description | A text string giving a description for the Thing. | String |
| M | samplingFeatureType | A text string specifying the type of sampling feature - usually "Site". | String |
| M | samplingFeatureCode | A text string specifying a shortened code identifying the Thing. | String |
| M | siteType | A text string specifying the type of Site represented by the Thing - e.g., "Streamflow Gage", "Water Quality Station", "Weather Station", "Diversion Station", etc. | String |
| M | isPrivate | An access control flag indicating whether the Thing is dicoverable and whethger metadata for the Thing is publicly available. | Boolean |
| O | dataDisclaimer | A text string displayed on the HydroServer landing page for the Thing (Site) that specifies a data disclaimer for data at that site. | String |
| M | locationId | A foreign key identifier for the Thing's location. | UUID |

## ThingAssociation

An association between a Thing and the Person or Persons who own and/or manage the information for that Thing. 

**Note**: HydroServer currently allows Things (monitoring sites) to have primary and secondary owners. Each site must have a primary owner. Sites may have any number of secondary owners. Only site owners may modify site metadata, load data for a site, etc.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | thingId | A foreign key identifier for the Thing participating in the association. | UUID |
| M | personId | A foreign key identifier for the Person that is affiliated with the Thing. | Integer |
| M | ownsThing | An access control flag indicating whether the Person is an owner of the Thing. | Boolean |
| M | isPrimaryOwner | An access control flag indicating that the Person is the primary owner of the Thing. | Boolean |

## Unit

The unit of measure associated with the Observations within a Datastream.

| Required | Attribute | Definition | Data Type |
| -------- | --------- | ---------- | --------- |
| M | id | A primary key unique identifier for the Unit. | UUID |
| O | personId | A foreign key identifier for the Person who created the Unit. | Integer |
| M | name | A descriptive name for the Unit. | String |
| M | symbol | An abbreviation or symbol used for the unit. | String |
| M | definition | A URL pointing to a website or controlled vocabulary that defines the Unit. | URL |
| M | type | The type of Unit (e.g., Flow, Concentration, Volume, Length, Mass, etc.) | String |

