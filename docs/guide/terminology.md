# Terminology

## Workspaces

Ownership within the HydroServer system is user-centric, meaning individual user accounts, rather than organizations, own the sites, datastreams, and metadata. Each user's account is the central point of control and responsibility for their associated hydrologic data. Organization information, when present, acts as an extension of the user's information. A user may be associated with an organization, but it is the user's account that maintains ownership and control over the data.

Ownership of all user-managed HydroServer data is handled within the context of a workspace. Users must set up one or more workspaces to organize and manage access to their data. Workspace owners may choose whether a workspace is public or private, invite other HydroServer users to collaborate on their workspaces as editors or viewers, or transfer ownership of a workspace to another user.

The following table is a comparison of permissions for the owners, editors, and viewers of a workspace.

| Permission                                               | Owner      | Editor     | Viewer     |
| -------------------------------------------------------- | ---------- | ---------- | ---------- |
| Rename, transfer, edit privacy of workspace              | Yes        | No         | No         |
| Invite new workspace collaborators                       | Yes        | Yes        | No         |
| Create, update, delete sites, datastreams, and metadata  | Yes        | Yes        | No         |
| Set up SDL to stream observations to datastreams         | Yes        | Yes        | No         |
| View public and private data within workspace            | Yes        | Yes        | Yes        |

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

**- Privacy**: Determines the accessibility of the site's data to the public. if is_private is false, any guest of the system can access the site and its metadata. If is_private is true, only owners and collaborators of the site's workspace can access site data and metadata.

**- Data Disclaimer**: Provides any necessary legal or usage notices related to the site's data.

### Additional Metadata / Tags

Tags are extra, customizable, key:value pairs that provide more context or categorization to the data, offering flexibility in metadata representation. For example, you might use tags to denote the project a datastream is part of, like `project:River Study`, or to indicate specific conditions during data collection, such as `season:summer`. These tags can be used from the `My Sites` page of the web app to filter and visually represent related sites.

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

**- Is Visible** is a boolean value (true or false) indicating if the Datastream observations are visible to users in the data management app.

**- Is Private** is a boolean value determining whether the Datastream is accessible to the public.

### 2. Linked Metadata

These are pieces of information that the Datastream references but does not own. They include things like Units, Processing Levels, and Sensors. These are pointers (Foreign keys) to other tables in the database, connecting your Datastream to a set of properties defined by the primary owner. For example, the 'Unit' in a Datastream points to a Unit created by the primary owner. While secondary owners can choose which Unit, Sensor, etc., their Datastream should reference, they cannot directly edit the properties of these Units or Sensors from within the Datastream. In the Data Management App, some will have a dropdown populated with a controlled vocabulary list from ODM2. When creating linked metadata, We recommend first searching the controlled vocabulary list and populating your metadata from it for the sake of being consistent with other users.

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

## Job Orchestration

The Data Management App provides a Job Orchestration user interface that allows you to link source data to HydroServer datastreams.

**-Orchestration System** - An Orchestration System is any machine that's able to extract data from a source location, transform that data into a standard format, and load that data automatically to HydroServer's API. HydroServer allows remote systems to register themselves as 'Orchestration Systems'. Once a system is registered, various jobs can be configured for it from the Data Management App's 'Job Orchestration' page. This includes mapping the columns of a source CSV file to their related datastreams in HydroServer.

**- Streaming Data Loader** - The Streaming Data Loader is a desktop application that can be downloaded onto compatible computers to easily run orchestration jobs in the background. Installing the SDL and logging in will register your machine as an Orchestration System, where you will then be able to manage your automated data uploads from the Data Management App. To learn how to install and configure the Streaming Data Loader, go to the [Streaming Data Loader](/applications/streaming-data-loader.md) section of the documentation.

::: tip Streaming Data Loaders are Orchestration Systems
Any machine running the Streaming Data Loader application is an Orchestration System, but not all Orchestration Systems have to run the Streaming Data Loader app. For example, a machine running Apache Airflow in a local or cloud environment could register itself as an Orchestration System.
:::

**- Data Source** is a configuration file saved in the HydroServer database which can be managed through the user interface of the Data Management App's 'Job Orchestration' page. It allows you to:

1. Select the Orchestration System that will run a group of jobs.
2. Set a schedule for automatically triggering repeating jobs.
3. Define how and where your data will be extracted from (a local file, an HTTP URL, etc.)
4. Define the file type the source data will be contained in (a CSV file, JSON object, etc.) and how to transform your data into a HydroServer compatible format. This file is called a 'Payload' in HydroServer.
5. Define where to load the data (usually HydroServer's database).

**-Payload** is one file or unit of data extracted from a source system. A payload can be a CSV file, JSON payload, or even a TCP response. The Data Management App provides a payload form that allows you to link source identifiers (like CSV file column names) to HydroServer datastreams.

## Observations

Observations are the individual data points collected within a datastream. Each observation is a record of what was measured at a specific time and place, along with an optional list of result qualifiers for that data point. Each observation will contain the ID of the datastream it belongs to

## Access Control

Access Control for sites and datastreams is handled through four levels of granularity:

1. **Workspace Privacy (workspace.is_private)**: This setting determines whether a workspace is private or public. If your workspace is private, all sites, datastreams, and associated metadata will only be accesible to the workspace owner and collaborators.

2. **Site Privacy (thing.is_private)**: This setting determines whether your site is private or public. If you set your site to private, it means that only the workspace owners and collaborators can view the site and all associated datastreams through the website or API. This is like having a closed folder that only selected people can open. This allows users to set some sites as public and others as private within a public workspace.

2. **Datastream Privacy (datastream.is_private)**: This setting is about who can see a specific datastream at your site. Even if your site is public, you might want to keep certain datastreams of that site private. When this setting is on, it means that only the workspace owners and collaborators can view this particular datastream's details and data.

3. **Datastream Visibility (datastream.is_visible)**: This is a convenience setting for controlling visibility of data in the data management application. The datastream is considered public and its metadata will be visible to the public, but datastream observations will be hidden. Note: Observations can still be retrieved by anyone through the SensorThings API regardless of this setting.

### Conditional Settings

These privacy settings work in a hierarchical, conditional manner:

If you set the **Site Privacy** to private (thing.is_private), then both **Datastream Visibility** (datastream.is_visible) and **Datastream Data Visibility** (datastream.is_data_visible) will automatically be set to private as well. However, if the site is public, you can still control the visibility of each datastream and its data individually.
