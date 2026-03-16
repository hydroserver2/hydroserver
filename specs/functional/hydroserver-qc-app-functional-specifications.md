# HydroServer QC Client Web Application

_Functional Specifications_

Last Updated: June 4, 2025

## 1 Introduction


The HydroServer QC client web application is a tool that enables quality control (QC) of time series of sensor observations stored in a HydroServer operational database. It is the primary web user interface for creating new, quality controlled versions of datastreams (a time series of observations for an observed variable at a monitoring location). In the HydroServer architecture, the QC web application operates through the HydroServer application programming interfaces (APIs) to read data from the operational database and to write data back to the operational database.

Figure 1. HydroServer architecture highlighting the Data Quality Control (QC) Client web application, data ingestion and query web services, and operational observations database.

## 2 Requirements


The following are requirements that must be met by the QC Client web application:

- It must be a web application.
- It must enforce authentication and authorization using HydroServer’s authentication and authorization system. For the Utah Division of Water Rights, this will use UtahID.
- It must use a reusable package of functions for performing quality control procedures.
- It must communicate with HydroServer’s operational observations database through HydroServer’s web service APIs (i.e., the Data Management Service and/or the SensorThings API).
- It must support the base set of corrections needed to manually QC process time series of observational data from aquatic and terrestrial monitoring sites.
- It must produce an executable record (e.g., a script or “history” record that can be executed) that defines the set of changes made to a datastream to produce a quality-controlled version. The “history” must include a timestamp of the change, the identity of the person who made the change, and an option to add/show a comment about the change made by the person who made the change.
- It must allow selecting and color coding raw data based on rules (e.g., color outliers or negative values plotted in red).
- It must preserve all raw data as a source datastream and save all modified data as a new, destination datastream.
- It must support retrieving datastreams as they were on a specific date/time as defined by the history of edits that have been made.
- It must allow tabular editing of data values for a selected time period.
- It must have the capability to provide a summary comparison between two processing levels for the same datastream (i.e, show or list what has changed).

## 3 Supported Functionality


The following describes specific functionality that will be provided by the QC Client web application. Screenshots from the old ODMTools application (an older desktop application that had much of the functionality desired for the QC Client web application) are included as a reference for functionality. These screenshots are for reference only and should not constrain the potential design or functionality of the final product.

### 3.1 Access Control


The QC Client web application will enforce the same access control rules implemented by the main HydroServer Data Management web application:
- Account creation will be handled via the main HydroServer Data Management web application and not the QC Client application. Users will only sign into the QC Client application using an existing HydroServer account.
- The QC Client web application will use the same login service for authentication as is used with the HydroServer Data Management web application. For DWRi, this will be UtahID.
- Requests to HydroServer’s APIs from the QC Client web application will be authorized based on a user’s HydroServer account.
- Datastreams will only be editable in the QC Client web application by users who have edit access to the workspace within which the datastream resides. Monitoring sites and their datastreams belong to a workspace. Any user with edit permission on a workspace can perform QC on a datastream within that workpace.
- The list of data series shown to the user in the series selector of the QC Client web application will be those associated with a workspace to which the user has been given at least viewer role. Users will only be able to edit datastreams within a workspace to which they have been given at least an editor role.
- The QC Client web application will be configured at deployment to connect to a specific HydroServer instance.

### 3.2 Data Visualization Functionality


- Main application view: The main application view area will be a plot screen showing time series plots of selected data. The only necessary plot type is time series. Ignore the other plot types in the screenshot below as they are not needed for QC. Individual data values must be shown in the time series as points connected by a line as shown.

- Datastream selection: Users will be presented with a list of datastreams (time series) within a workspace on which they can operate (view and/or edit).
- Datastreams will present basic metadata about the datastream, most likely in a tabular view, so users can select the correct datastream(s) for display and selection for editing.
- A tabular structure could include sortable columns with some useful filters:
- Show datastreams for a selected site.
- Show datastreams for a selected observed property.
- Show datastreams for a selected processing level.
- Each datastream needs to be selectable. Selection of a datastream in this view will add the datastream to the plot visualization.
- The user needs to be able to select datastreams for plotting (may be multiple at once) and for editing (only one at a time).

- Tooltips and plot coordinates: In the plot window, at appropriate scales, hovering over data value points will display values including the date/time value and the numeric value. This may require selection of an “active” datastream if/when multiple datastreams are plotted.
- Visualizing data qualifiers: The plot view will illustrate data qualifiers (flags or data qualifying comments that have been added to data values). Showing qualifiers on the plot could be done by highlighting data points to which qualifiers have been applied or by displaying markers or bars at the bottom of the plot area near the x-axis corresponding to data values or ranges of data values with qualifiers applied to them. Bars or points/markers at the bottom of the plot might be better because they could be stacked in the case of multiple qualifiers.
- Date/time range selection: The user should be able to adjust the time range of data that are selected for visualization and editing via a control available on the user interface. This could also be done dynamically via buttons for particular periods (last day, week, month, year, etc.).

- Plot zooming and navigation: The plot should contain basic zoom/navigation options. These include the following, but may be constrained by the available functionality of the specific plotting tool selected:
- Zoom to full extent: Zoom the plot to the full extent of the selected datastream(s) and selected time period.
- Zoom in: Zoom in to an area selected by the user
- Zoom previous: Zoom to whatever extent the user was previously at
- Zoom next: Zoom back to the extent from which the user clicked zoom previous
- Move left: Move the entire plot some distance to the left
- Move right: Move the entire plot some distance to the right
- Pan: Allow the user to grab the plot and pull it in any direction to pan the view
- Zooming in and out should also be available via a mouse scroll while hovered over the plot window.

- Tabular data view: Users will also have the option to access a tabular view of the datastream selected for editing. The tabular view will:
- Load data for the datastream selected for editing.
- The tabular view will display data values and their timestamp.
- Numeric data values in the table will be editable when a series is selected for editing. Edits to values in the tabular view will be recorded as edits in the “history”.

### 3.3 Data Editing Tools


- Data value selection: The interface will present the user with a tool or set of tools for selecting data values using the mouse.
- This tool should allow selection of individual data values by clicking on the point on the plot. This could also be accomplished by drawing a box around an individual data point.
- The tool should enable selecting a range of data values by dragging a box around points to be selected.
- The tool will also allow Shift + Click type selection to allow adding points to an existing selection.
- The user will need to switch between a selected zooming tool and the data selection tool to control mouse behavior. Zooming should not affect the data selection.
- A “lasso select” may be available depending on the specific plotting tool selected.
- Editing functions: The interface will feature a set of manual data editing tools/functions. These are likely best presented via a toolbar at the top or side of the plot. Functions include:
- Edit datastream: Start editing a selected datastream. Points can only be selected on a datastream that is in edit mode.
- Restore datastream: Start over by querying the original selected datastream from the database and restore the original values.
- Save datastream: Commit all changes to the database as a new or modified datastream.
- Filter points: Apply filter(s) to select specific points. Options for filters include:
- Value thresholds (select values above or below a threshold).
- Rate of change threshold (select values where the rate of change from one point to the next is greater than some threshold).
- Data gaps (select the points before and after a gap longer than a specified threshold).
- Persistence (select data points where the recorded value is exactly the same for longer than a specified threshold).
- Reset selection: Clear all selected data values.
- Change values: Modify selected data values by choosing an operator (add, subtract, multiply, divide, equals) and a numeric constant value to apply (e.g., add 10.12345 to all selected datavalues, or set all values equal to 9.0).
- Interpolate values: Linearly interpolate selected data values using the previous and next data value that are outside the selected range.
- Linear drift correction: Apply a linear drift correction to selected data values
- Flag: Add data qualifying comments to selected data values.
- Add data value: Insert a data value into the datastream at a date/time location.
- Delete data value: Delete selected data values.
- Fill gap: Fill missing data values between two existing data values. This could include a toggle to fill the gap with a constant, use a table where the user can fill in individual missing values, or it could allow the user to insert interpolated values.
- Undo (not shown): Undo the last edit made.

- Editing history: The interface will record the set of edits created by a user through applying the editing functions to a datastream. The record of these edits will be recorded in an executable “history” that enables generation of a quality controlled datastream from a raw source datastream. While the design and functional specifications for “histories” is contained in a separate functional specifications document, the following basics are included her for completeness:
- The QC App will include an accompanying Python client library/package (hydroserverpy) that contains functions for running all of the QC corrections listed above.
- The QC Client web application will record the sequence of edits made to a datastream by the user as a “history” that records the operations executed and will make them viewable with the QC Client web application via a “history” editor.
- The user of the QC Client web application will be able to open and view the “history” of all QC changes that have been made to a datastream.
- The user will be able to modify and save the “history” - e.g., open a datastream for editing, view its existing QC “history”, and then add another year of edits to the raw data that get saved in the “history”.
- The resulting “history” will be an executable record of the transformations made to the input datastream to create a resulting quality controlled datastream.
- “Histories” will be stored and managed by HydroServer with access to “histories” available via HydroServer’s data management API.
- Saving QC edits: Saving an edited datastream will initiate a process to save the edits that have been made to the selected datastream.
- The user will be able to select options for saving output. Two options will be provided based on whether a user is ready to create a new datastream or not:
- Save for review: A “save for review” function will save the QC editing “history”, but not the resulting datastream. This will allow a second person to open the datastream for editing, view/review the history of edits, review the output, and then approve the history and finally save the quality controlled datastream to the database.
- Save edited datastream: The QC steps are complete and ready to be saved to the database as a new or existing datastream.
- Users will have the option to select an “Existing datastream” to save as an existing datastream or “New datastream” to create a new datastream.
- If the user selects saving as an “Existing datastream”, they will select a datastream to replace and be warned that the existing datastream will be overwritten in the database.
- If the user selects saving as a “New datastream”, they will need to specify the metadata for the new datastream to be created. Much of this metadata can be determined from the existing datastream that is being edited; however, the following metadata will need to be set. Some of these values could be pre-set from the datastream being edited but then the user would have the ability to change them:
- Observed Property/variable
- Units
- Sensor/Method
- ProcessingLevel
- The app should present the user with a summary of the metadata for the datastream to be saved that the user can review prior to saving.
- Users will be prevented from saving over the datastream that is being edited. For example if a user selects a raw datastream for QC editing, they can save the result as a new datastream or they can overwrite an existing datastream if a QC datastream has already been created for the raw datastream. The user will not be able to select a datastream for QC editing and then save by overwriting the same datastream.

Additional functionality for subsequent versions:
- When the option is selected to save as a new datastream, the tool could allow the user to create new observed properties, units, sensors, quality control levels, etc. dynamically from the QC Client app rather than those having to exist in the HydroServer database prior to saving the datastream. The first version of the QC App will not have this capability.

## 4 Anticipated Software Stack


To the extent possible, the QC Client web application will be implemented using the same software technology stack used by the HydroServer Data Management web application for consistency.

### 4.1 Front-end


The front-end will be built with established Vue and data visualization frameworks that most developers will be familiar with, likely using the following frameworks/tools:

- Vue 3 (https://vuejs.org/): Single Page Application framework.
- Vite (https://vitejs.dev/): Vue scaffolding and development tools.
- Plotly (https://plotly.com/javascript/): Data Visualization library.
- Vuetify (https://vuetifyjs.com/en/): Theming library. Implements Google's Material Design.
- TypeScript (https://www.typescriptlang.org/): Strongly typed JavaScript.
- Pinia (https://pinia.vuejs.org/): Handles app's state and local storage.

### 4.1 Back-end


The app will consume HydroServer’s APIs and will not need its own backend server.
