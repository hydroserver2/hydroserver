# HydroServer Data Management Web Application

_Functional Specifications_

## 1 Introduction


The HydroServer Data Management web application is a data management and configuration tool that can be used to create and manage metadata about observational data, including sites, variables, methods, sources, processing levels, etc. It is the primary user interface for registering data collection sites and configuring them to receive data loaded through HydroServer’s application programming interfaces (APIs). It can also be used for setting data access control, data visualization, data archive with HydroShare, and data export.

## 2 Definitions


Datastream: A time series of data values for an observed property collected at a monitoring site.

Monitoring site: A physical location at which time series observations are made using sensors or other observation methods. A monitoring site is a “Thing” in the Open Geospatial Consortium’s (OGC) SensorThings API and data model specification.

## 3 Requirements


The following are requirements that must be met by the HydroServer Data Management web Application:

- It must be a web application.
- It must provide user accounts and user authentication - see separate functional specifications for HydroServer’s Identity and Access Management.
- It must communicate with HydroServer’s operational database through HydroServer’s APIs.
- It must be deployable locally or using services available via major commercial cloud platform providers (e.g., Amazon Web Services (AWS) and Google Cloud Platform (GCP).
- It must support access control for data and metadata associated with monitoring sites.

## 4 Supported Functionality


The following describe specific functionality that will be provided by the HydroServer Data Management web application:

### 4.1 User Accounts and User Management


- Users will be able to create an account with the Data Management web application.
- The application will enable site administrators to use an existing identity provider like ORCID and/or Google. This will allow users to create their user account and log into the application using their ORCID account, Google account, or other third party identity provider. NOTE: Academic users will have ORCIDs, but other types of users (e.g., agency employees) probably will not.
- For sign in with Google, see the following: https://developers.google.com/identity/gsi/web/guides/overview
- Site administrators will be able to disable account creation with ORCID and/or Google accounts as a configuration setting when the application is deployed.
- Users will be able to log into the Data Management web application.
- Users will have a basic profile page with the following metadata for users:
- Name
- Email
- Address
- Phone number
- User Type - This will implement a controlled vocabulary of user types.
- Affiliation - the organization a user is affiliated with.
- Link - A URL to a user’s website or other online profile.
- Authorization information for HydroShare - i.e., the token used to archive data via the user’s HydroShare account
- Organization information - Information about an organization with which the user is affiliated
- Organization name
- Organization code
- Link
- Organization type - This will implement a controlled vocabulary of organization types
- Description

### 4.2 Monitoring Site Functionality


- When the user is logged in, the Data Management web application will provide the following:
- A list of the user’s registered monitoring sites via a “Your Sites” page.
- On the “Your Sites” page, a map showing the location of all of the user’s sites with symbology that provides information about the status of data at that site (e.g., new data within the last day, week, month, year)
- Users will be able to click on the site location markers on the map of sites. A pop up will provide simple site metadata about the site and a link to the site’s landing page.
- The list of the user’s registered sites will include links to the landing page for each site (site details page).
- Each registered monitoring site will have a landing page/site details page that displays:
- A zoomable map of the site location.
- A listing of the site’s identifier, title, and all other descriptive metadata.
- A list of the datastreams for observed variables at that site, including:
- Metadata about the datastream, including at minimum the observed property, identifier, processing level, sampled medium, and sensor.
- The value, units, and date/time of the most recent observation for the observed variable at that site.
- A sparkline plot showing the most recent 72 hours of data for the datastream.
- Links to download the data values for the datastream.
- A link to “Visualize Data” for the datastream that sends the user to the “Visualize Data” page and generates a plot for the selected datastream
- On the “Your Sites” page, users will be able to register a new site:
- They will be presented with a web form where they can:
- Create the site’s metadata.
- Upload photos of the site to be displayed on the site’s landing page.
- Choose whether to make the site’s location and landing page publicly viewable.
- Include a user-editable data disclaimer for the site that will be displayed on the landing page for the site above the table of datastreams.
- The site registration form will have a map that the user can click on to specify the site location. Latitude, longitude, elevation, state, county, and country will automatically be extracted from the location selected on the map.
- Users with edit permissions for a registered site will see a button to “Edit Site Information” on the site’s landing page, which will load the metadata for the site into the same form used for the site creation page for editing.
- Users with edit permissions for a registered site will see an option on the site’s landing page enabling them to make the site’s location and landing page publicly viewable.
- Users with delete permissions for a site will see a button to “Delete Site” on the site’s landing page, which will delete the site, all of its metadata, and all associated data from the system. There should be multiple verification steps and warnings prior to actually doing the delete to make sure the user really wants to delete the site and all of its data.

### 4.3 Datastream Functionality


- Once a monitoring site is registered, the owner of the site will see an option to “Add New Datastream” on the site’s landing page. When the user clicks this option, they will see a web form that allows them to:
- Create a datastream at the selected site. Any number of datastreams can be created for a site.
- Specify metadata about the datastream, including a name, description, observed property, units, sampled medium, processing level, status, aggregation statistic, nodata value, time aggregation interval and units, intended time spacing and units, and Sensor information (e.g., information about the sensor or method used to create the data) - consistent with the HydroServer implementation of the SensorThings data model.
- Specify whether the datastream should be publicly viewable on the site’s landing page. Users with view access or greater will see all configured datastreams on the site’s landing page, regardless of this setting.
- The form to configure observed variable metadata will use controlled vocabularies derived from Version 2 of the Observations Data Model (ODM2) for metadata elements where possible.
- The form will include options for auto-generating the datastream name and description from the other specified metadata elements. Or, the user will be ablel to type them into a text box.
- Once a datastream is configured for a registered site, a user with edit permissions for the site will be able to:
- Edit the configured datastream’s metadata - datastream metadata will be loaded into a form to edit the metadata for the configured datastream. The user will have the option of making the datastream publicly viewable on the site’s landing page or not.
- Delete configured datastream - the datastream and any associated data will be deleted from the database. The user should be prompted and warned to make sure they really want to delete the datastream and all of its associated metadata.
- Link a data source to a datastream - This will allow the user to link the datastream to a data source that is provided by an instance of the HydroServer Streaming Data Loader app.

### 4.4 Data Archival Functionality


- A user with owner permissions for a registered site will see an option on the site’s landing page to archive data for the site to HydroShare - this will provide options for the user to archive their data to HydroShare.
- See the separate functional specifications for the HydroServer data archival service.
- Users will be able to authorize their HydroServrer user account in the Data Management web application to archive data to HydroShare using HydroServer’s Data Archival Service.

### 4.5 Data Visualization Functionality


- Users will be able to visualize all public data and all data to which they have at least view permissions for via a “Visualize Data” page. The following functionality will be available on the “Visualize Data” page:
- A filter tool will enable users to filter a table of datastreams to limit the list of datastreams that can be selected for visualization (limit the list of datastreams shown in the table for selection).
- Filters will be collapsible to maximize real estate available to the plot window.
- There will also be a single button to “clear filters” that clears all filter criteria that have been selected.
- Filters may also include search boxes within filters to help users find the specific filter items they want to select.
- Search boxes will accept a text string and will limit items shown within the filter to items that match those terms.
- Filters will include the ability to select datastreams that have matching:
- Sites.
- Processing Levels.
- Observed properties.
- The Visualize Data page will provide a table listing datastreams that meet the criteria the user has selected in the filters and that that allows the user to:
- Select up to five datastreams to plot at one time.
- View metadata related to a specific datastream by clicking on the datastream’s row in the table.
- Click a button to download selected datastreams as comma separated values (CSV) files.
- When a single CSV is selected, the user will be provided with a single CSV file for download.
- When multiple datastreams are selected, each datastream will be written to a separate CSV and then compiled into a zipped file for download.
- Select the columns to be shown in the table - the attributes of the datastream shown as columns in the table.
- Show selected rows or show all rows meeting the filter criteria.
- A search box that further filters the list of datastreams in the table based on an input text search term.
- A control near the plot will enable users to select the time range for data to be visualized in the plot, including the following options:
- Last week
- Last month
- Last year
- A date picker control will be used to enable the user to input a custom data range to be returned and plotted.
- A plotting window will be included that provides the following functionality:
- Zoom - users will be able to zoom in and out on the plot using a zoom control or by using their mouse zoom control (zoom wheel).
- Context brush - the plot will provide a context brush that will allow users to slide the plot in time and limit the period of data shown.
- Data point highlight - The plot will have a hover tooltip that shows the individual datavalues and their corresponding date/time values when the user is hovering over specific data points.
- Export an image of the current plot
- A switch between the plot visualization and a table showing summary statistics (minimum, maximum, arithmetic mean, geometric mean, standard deviation, number of observations, coefficient of variation, 10th percentile, 25th percentile, 75th percentile, 90th percentile)
- A button near the plot to copy the current state of the visualize data page as a URL that can relaunch the visualize data page using the URL.

### 4.6 Browse Monitoring Sites Functionality


- A Browse Monitoring Sites page will provide a map-based display of all monitoring sites within the HydroServer instance.
- Unauthenticated users will see only publicly available sites via this page.
- Logged in users will see all publicly available sites and sites to which they have been given at least view access.
- Clicking on a site on the map will provide a pop up a bubble with basic metadata for the site and a link to “View data for this site” which will take the user to the landing page for that site.
- The Browse Monitoring Sites page will include filters to the left of the map display that allow users to filter sites shown on the map.
- Filters will include:
- Organizations
- Site types
- A Clear Filters button will be available to remove any filter settings
- The filters panel will be collapsible to maximize the viewing area of the map display.
- HydroServer admins will have a configuration setting that enables zooming the map display to a default zoom extent when the page loads the first time.

### 4.7 Data Management Functionality


- A Data Management menu will enable HydroServer users to manage metadata for Sensors, Observed Properties, Processing Levels, Units, and Result qualifiers.
- Users will select an option to “Manage Metadata”.
- They will be presented with a page where they can view existing, created new, and edit existing metadata resources for which they have edit access.
- A button will be added to each metadata resource type to create a new instance of that resource type (e.g., Add New Sensor, Add New Observed Property).
- Clicking on this button will present the user with a form to create a new instance of the specific metadata type.
- Users will be able create all required and optional metadata attributes for the resource on this form.
- Where possible, controlled vocabularies from Version 2 of the Observations Data Model (ODM2) will be used in these forms.
- Each metadata resource (i.e., a Sensor, Observed Property, Processing Level, etc.) will be shown in a table/list and will have options for editing the resource or deleting the resource.
- Choosing the option to edit a resource will load the metadata attributes for that resource into a form where the user will be able to edit the attribute values.
- If a user chooses to delete the metadata resource, HydroServer must first check to make sure that the metadata resource is not being used.
- If a metadata resource is being used by a datastream in the database, the datastream must first be deleted before the metadata resource can be deleted.
- Where this is the case, the user will be alerted with a message stating that the metadata resource is being used and cannot be deleted.
- The Data Management Menu will provide a view of any data loaders that have been added to the HydroServer instance.
- These include instances of the HydroServer Streaming Data Loader that have been configured to load data to the HydroServer instance, and may include other types of data loaders configured using future functionality.
- This view will also provide links to download the HydroServer Streaming Data Loader software.
- The Data Management Menu will provide a view of data sources that have been configured for loading data into datastreams that have been configured in the HydroServer instance.
- Data sources will be shown in a table/list that provides status information about when the jobs have or will be run.
- Actions will be available for each data source to:
- View data source details
- Edit the data source
- Delete the data source
- Pause the data source (pause the execution of the data source via its configured execution tool - e.g., the Streaming Data Loader)
- A button will be available to “Add Data Source”
- Clicking this button will present a web form with the options required to configure a new data source for loading using the HydroServer Streaming Data Loader (SDL). For the SDL, these will be CSV files containing time series data that are available to the SDL either as local files or as files available via HTTP or FTP.
- See separate functional specifications document for the HydroServer Streaming Data Loader software application.
- See separate functional specifications document for the Automated Jobs Orchestration Sysgtem.

Appendix A - Access Control and Permissions

The following are general permissions for what users of the web application can and can’t do:

Any User can:
- Delete their account
- System warns the user what will happen when they do this
- System offers to archive data to HydroShare first
- System deletes any data associated with their account
- View and access data for a public site

Any Site Owner can:
- Access, view, and download all of their data
- Update metadata for any Site they own
- Delete any Site they own
- Will be warned that data loss will cascade and be lost for all site owners
- System will offer to Archive data in HydroShare before deleting
- System will delete site and any associated data
- Hide/Not hide Datastreams for sites they own
- Delete Datastream for any site they own
- Remove themselves as an owner of any site they own (Unless they're the primary owner - primary ownership must be transferred before removing themselves)
- Make a site private or public
- Warn a user what will happen when a site goes private
- Warn a user what will happen when a site goes public

Primary Site Owner can:
- Everything above for “Any Site Owner”
- Add secondary owner
- Remove secondary owner
- Transfer primary ownership to a secondary owner
- For each datastream metadata property
- If the new owner DOESN’T have a property where ALL the fields are the same
- Create a copy of the property
- Set the datastream property ID to the new owner's related property id
- If the new wonder DOES have a property where ALL the fields are the same
- Set the datastream property ID to the new owner’s related property ID
- Update metadata for any Datastream

System Admin User (v1.1) can:
- Access Django Admin panel which gives CRUD for all tables
- Edit controlled vocabulary fixtures
- Access a statistics page for viewing active users, site usage, etc.?
- Message information to all/select users
