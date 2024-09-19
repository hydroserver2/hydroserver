# Terminology

## Sites

A Site as HydroServer defines them refers to a specific hydrologic entity, such as a weather station, stream gauge, or another environmental monitoring location. It encompasses both the physical location and the metadata describing the site. To follow SensorThing's naming convention, sites are called `things` in the Data Management API. However, since more users are familiar with the term `sites`, we've opted for that name in our user facing software like the HydroServer website.

A Site in the HydroServer system can encompass multiple time series of data, known as Datastreams. Each Datastream represents a distinct set of observations collected at the site, potentially through different instruments or methodologies. For instance, a single site like a weather station might have separate datastreams for temperature, humidity, and wind speed, each collected by different data loggers. This multi-datastream capability allows for a comprehensive and nuanced understanding of the site's environmental conditions.

### Site Metadata

Below is a list of the metadata available for a Site:

**- ID**: A unique identifier (UUID) for each site, ensuring that each site can be distinctly recognized and referenced within the system.

**- Name**: Provides a human-readable identification, often reflecting the site's geographical or functional characteristics.

**- Location**: Refers to the precise geographical coordinates of the site (lat, lon, el).

**- Site Type**: Categorizes the nature of the site. Options come from [ODM2's Site Type controlled vocabularies list.](http://vocabulary.odm2.org/sitetype/)

**- Site Code**: An additional identifier, often a concise code or abbreviation, used to reference the site. The purpose of having a code alongside the name and UUID is to allow lossless data migration from an ODM2 database.

**- Privacy**: Determines the accessibility of the site's data to the public. if is_private is false, any guest of the system can access the site and its metadata. If is_private is true, only the owners of this site can

**- Data Disclaimer**: Provides any necessary legal or usage notices related to the site's data.

### Additional Metadata / Tags

Tags are extra, customizable, key:value pairs that provide more context or categorization to the data, offering flexibility in metadata representation. For example, you might use tags to denote the project a datastream is part of, like `project:River Study`, or to indicate specific conditions during data collection, such as `season:summer`. These tags can be used from the `My Sites` page of the web app to filter and visually represent related sites.

### Site Ownership

Ownership within the HydroServer system is user-centric, meaning individual user accounts, rather than organizations, own the sites, datastreams, and metadata. Each user's account is the central point of control and responsibility for their associated hydrologic data. Organization information, when present, acts as an extension of the user's information. A user may be associated with an organization, but it is the user's account that maintains ownership and control over the data.

HydroServer has the concept of Primary and Secondary Owners. The motivation behind secondary owners is to gracefully handle the case where something happens to the primary owner where the site needs to be transferred to someone else.

The following table is a comparison of permissions for the primary and secondary owners of a site. In order to better understand some of the permissions, you may want to read the datastream section then come back.

| Permission                                          | Primary Owner           | Secondary Owner            |
| --------------------------------------------------- | ----------------------- | -------------------------- |
| Own sites, datastreams, linked metadata             | Yes                     | No                         |
| Add or remove site owners                           | Yes                     | No                         |
| Transfer primary ownership of a site                | Yes                     | No                         |
| Create, Update, Delete datastream's linked metadata | Yes                     | No                         |
| Select datastream's linked metadata                 | Yes                     | Yes (from primary owner's) |
| Modify datastream's direct metadata                 | Yes                     | Yes                        |
| Create, Delete datastreams                          | Yes                     | Yes                        |
| Create, Update, Delete sites                        | Yes                     | Yes                        |
| Remove self as owner                                | Yes (deletes site data) | Yes                        |
| Link a Data Loader to a Datastream                  | Yes                     | Yes                        |

## Datastreams

A Datastream is a sequence of data points collected over time, measured by a physical sensor or other method of data collection, and defined by various metadata. As far as user permissions are concerned, datastream metadata is differentiated in the following two groups:

### 1. Direct Metadata

This is the information that directly relates to a specific datastream that users can edit. Descriptions of each field is below:

**- Name** is the identifier for the Datastream, typically a string that reflects its purpose or content.

**- Description** a detailed text description of what the Datastream represents, including its scope and nature.

**- Observation Type**is a string indicating the method or type of observation, such as time series or event-based.

**- Sampled Medium** is the medium or environment from which the data is collected, like air, water, or soil.

**- No Data Value** is the numerical value used to represent missing or null data in the Datastream.

**- Aggregation Statistic**is string describing how data is aggregated, like average, sum, or maximum.

**- Time Aggregation Interval** refers to the numerical value indicating the time interval for data aggregation.

**- Status** is a string representing the current operational status of the Datastream, like complete or ongoing.

**- Value Count** is a numerical value representing the total number of data points in the Datastream. Calculated by the API automatically.

**- Intended Time Spacing** is the expected time interval between individual data points in the Datastream.

**- Intended Time Spacing Unit** the unit for the intended time spacing value.

**- Phenomenon Begin Time** is the actual start time of the phenomena being observed, formatted in ISO 8601 UTC. Calculated by the API automatically.

**- Phenomenon End Time** is the actual end time of the phenomena being observed, formatted in ISO 8601 UTC. Calculated by the API automatically.

**- Result Begin Time** is the start time the observation was recorded for the data results in the Datastream.

**- Result End Time** is the end time the observation was recorded for the data results in the Datastream.

::: tip
Usually the phenomenon time and result time are the same, but sometimes there's a delay between the event and when it was recorded that needs to be accounted for. Only using phenomenon time will suit most use cases.
:::

**- Data Source Column** is a string indicating the column index or name of the Data Source CSV file that corresponds to this Datastream's observation values.

**- Is Visible** is a boolean value (true or false) indicating if the Datastream is visible to users.

**- Is Data Visible** is a boolean value determining whether the actual data of the Datastream is accessible to users.

### 2. Linked Metadata

These are pieces of information that the Datastream references but does not own. They include things like Units, Processing Levels, and Sensors. These are pointers (Foreign keys) to other tables in the database, connecting your Datastream to a set of properties defined by the primary owner. For example, the 'Unit' in a Datastream points to a Unit created by the primary owner. While secondary owners can choose which Unit, Sensor, etc., their Datastream should reference, they cannot directly edit the properties of these Units or Sensors from within the Datastream. In the Data Management app, some will have a dropdown populated with a controlled vocabulary list from ODM2. When creating linked metadata, We recommend first searching the controlled vocabulary list and populating your metadata from it for the sake of being consistent with other users.

**- Unit** refers to the measurement units of the data (like liters, meters, etc.). Each unit has a name, description, symbol (like 'C' for degrees celsius), and type.
[ODM2's Units controlled vocabularies list](http://vocabulary.odm2.org/units/)

**- Processing Level** indicates the degree of processing or analysis that the data has undergone, which includes a code, definition, and explanation. Users are free to use their own conventions, but the webapp provides the following defaults that can be loaded from templates like the other linked metadata:

- 0: Raw data
- 1: Quality controlled data
- 2: Derived products
- 3: Interpreted products
- 4: Knowledge products
- 9999: Unknown

**- Observed Property** is the specific characteristic or attribute being observed, like temperature or flow rate.
[ODM2's Observed Property controlled vocabularies list](http://vocabulary.odm2.org/variablename/)

**- Sensor** is the device or methodology used to collect the data. The Sensor model captures details like type, manufacturer, and model, essential for understanding data collection methods.

**- Result Qualifier** provides additional information about the result of an observation, like its accuracy or reliability. Each Result Qualifier has a code and a description to clarify its meaning. For instance, if ice affects a sensor, impacting the observation's reliability, a user can add a Result Qualifier with the code 'ICE' to denote this specific condition. This helps in understanding and interpreting the data accurately, especially when external factors influence the measurements.

**- Data Loader** - The Streaming Data Loader desktop app is a tool used to automatically load data into HydroServer from local data files of a compatible computer. To learn how to install and configure a datastream to use a dataloader, go to the [Loading Data](loading-data.md) section of the documentation. In short, a user can install the desktop app on their system, assign that computer a name, then link that computer to various datastreams.

::: tip
Any system which is running the Streaming Data Loader desktop app is referred to as a **Data Loader**.
:::

**- Data Source** is a CSV file on the user's computer(Data Loader) that the Streaming Data Loader desktop app can read and periodically stream to the HydroServer database automatically. A single Data Source may contains raw time series data for one or more datastreams.

## Observations

Observations are the individual data points collected within a datastream. Each observation is a record of what was measured at a specific time and place, along with an optional list of result qualifiers for that data point. Each observation will contain the ID of the datastream it belongs to

## Access Control

Access Control for sites and datastreams is handled through three privacy settings:

1. **Site Privacy (thing.is_private)**: This setting determines whether your entire site is private or public. If you set your site to private, it means that only the site owners can view the site and all associated datastreams through the website or API. This is like having a closed folder that only selected people can open.

2. **Datastream Visibility (datastream.is_visible)**: This setting is about who can see a specific datastream at your site. Even if your site is public, you might want to keep certain datastreams of that site private. When this setting is on, it means that only the site owners can view this particular datastream's details and data.

3. **Datastream Data Visibility (datastream.is_data_visible)**: This one is a bit more specific. It allows you to show the metadata (like the name, description, and type) of a datastream to the public but keep the actual observation data private.

### Conditional Settings

These privacy settings work in a hierarchical, conditional manner:

If you set the **Site Privacy** to private (thing.is_private), then both **Datastream Visibility** (datastream.is_visible) and **Datastream Data Visibility** (datastream.is_data_visible) will automatically be set to private as well. However, if the site is public, you can still control the visibility of each datastream and its data individually.

It's important to note that with the exception of Data Sources and Data Loaders, **Linked Metadata**, is always public through the API.
