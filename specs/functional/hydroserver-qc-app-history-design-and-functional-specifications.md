# HydroServer QC App History Design and Functional Specifications

Last Updated: September 15, 2025

## 1 Introduction


The HydroServer data quality control (QC) web application is intended to provide a web-based graphical user interface (GUI) within which a user can select a HydroServer datastream for editing/correction and then perform manual edits on that datastream to produce a new, quality controlled datastream. Edits may include deleting erroneous values, inserting values, interpolating values, adjusting values, drift corrections, etc. Edited data are saved to a new HydroServer datastream that is a version of the original, raw data.

The main GUI includes a time series plot of the data where the user can interact with, select, and modify the data values. A tabular view of the data selected for editing will also be provided so users can interact with individual data values in a tabular view. Users may optionally tell the QC app to generate a QC history for the datastream that provides a saved record of all the edits that have been made to the datastream through any instance of the QC app. The history also defines a source datastream that allows users to view changes over time from the source datastream to the quality controlled datastream. This document describes the design and functional specifications for data QC histories. A separate functional specifications document describes the functionality and user interface for the HydroServer data QC App.

## 2 Definitions


Datastream: A time series of data values for a particular observed property, at a particular monitoring site, observed using a particular sensor, recorded using a particular unit of measure, and having a particular processing level.

Managed Datastream: The datastream being managed by the QC app. QC history is associated with this datastream, and edited data are saved to it. All observations in a managed datastream must be created through the QC App via an edit session - or through a separate app that creates and manages edit sessions in the same way the QC App does.

Source Datastream: A datastream that contains the original observations of the managed datastream without any QC edits applied. Typically, this is a raw datastream recorded by a sensor in the field but could be any datastream from which a new, quality controlled datastream is to be derived while tracking and saving a history of edits.

Edit Event: An edit event is an individual action taken by a user that performs a specific operation on a selected set of data values. Examples include delete, interpolate, adjust, etc. Edit events correspond to a QC function in the hydroserverpy package (HydroServer’s Python client package) and in the corresponding JavaScript functions within the HydroServer QC Web App.

Edit Session: A set of Edit Events performed within a selected Datastream or within a subset of data selected from a datastream by an individual HydroServer user.

History: A recorded set of edit sessions and their corresponding edit events that have been performed on a datastream to move it from one processing level to another. The history is represented as a directed acyclic graph (DAG), where each node is an edit session. Edges in the graph are created when edit sessions apply to overlapping phenomenon time ranges in the managed datastream. A history records how transformations on a source datastream have produced the managed datastream in its current state.

Processing Level: An attribute of a datastream indicating the level of quality control or processing to which a datastream has been subjected (e.g., “raw” data versus “quality controlled” data).

Selection Event: A selection event is an individual action taken by a user that selects a set of individual data values on which an edit will be performed. Selections may or may not include contiguous data values. Selections may be made by clicking on points, by using box or lasso selection tools, or by running filters that select data values based on rules created by a user.

Version: A copy of a datastream produced from a source datastream having a different processing level than the source datastream.

## 3 Constraints


HydroServer’s data model uses processing levels to indicate the level of quality control applied to a datastream and to support datastream versioning. A common convention is to use processing level 0 for raw data and processing level 1 for quality-controlled data, but HydroServer does not constrain the processing levels that organizations can define. Thus, the HydroServer QC App cannot make assumptions about the meaning of processing levels in the QC workflow or that there is a numeric progression of processing levels.

To address this, the QC App will adopt the concepts of a “managed datastream” and a “source datastream”. A managed datastream is the datastream the QC app edits. If QC history tracking is enabled, this is also where the QC history and edit session files are attached. The source datastream provides an unedited, reference copy of the managed datastream. It allows the QC app to traverse the QC history and reconstruct the managed datastream at any point in that history.

For this approach to work, observations in the source datastream must remain unchanged after they are created and referenced in a QC session. To help prevent unintended editing of source datastreams, the QC app will mark source datastreams with a tag pointing to the managed datastream. The presence of this tag will cause the QC app to disallow editing of that datastream through the app. The QC app will also require that a source datastream and a managed datastream must have different processing levels. HydroServer will provide a method to verify datastream integrity using checksums generated from datastream observations. The QC app will use these checksums to detect if changes have occurred to a datastream over a specified phenomenon time range and warn the user if the raw data was edited at any point since it was referenced in a session, or if a managed datastream was edited without being recorded in the QC history.

These constraints are intended to help prevent users from unintentionally breaking QC history tracking by editing source datastreams, however, neither the QC app nor HydroServer can enforce or guarantee datastream immutability, especially by other apps or users with permissions to do so. Ensuring QC history integrity also depends on appropriate workspace permissions being assigned to users and apps, and organizational policies being put in place for users to follow with respect to editing datastreams.

## 4 Session-Based History Design


A history is represented as a directed acyclic graph (DAG) with the raw source datastream at the beginning of the graph and the current state of the managed, quality-controlled datastream at the end (Figure 1). Edit sessions (the green and yellow boxes in Figure 1) represent nodes in the graph. Like code changes within the Git version control system used for software development, edit sessions represent “commits” of changes made to a managed datastream. Edges in the graph represent directed relationships and dependencies between the source datastream, edit sessions, and the managed datastream. The managed datastream represents the result of applying all the edit sessions (“commits”) stored in the QC History to the source datastream.

Every observation in a managed datastream needs to be associated with at least one QC edit session. Managed datastreams start empty and have no data in them until a user commits an edit session. When a user begins an edit session over a time period that doesn't already have a committed edit session associated with it, the QC app will fetch observations from the source datastream for the user to perform edit operations on in their browser. When the user is finished, the resulting data from those edit operations is then saved to the managed datastream; the source datastream's observations are never edited or changed by the QC app.

The blue arrows in Figure 1 represent the flow of data (divided into one month chunks for this example) from the source datastream through one or more QC edit sessions towards the managed datastream where the output of those edit sessions are saved. Each edit session in the diagram depends on all edit sessions to the left of it that any of the arrows feeding it passes through, as well as all upstream dependencies of those edit sessions. For example, edit session 5 depends on edit sessions 2, 3, and 4 because they modify overlapping data, represented by the blue arrows for April, May, and June. However, edit session 5 also depends on edit session 1, even though they do not directly overlap in time, because edit session 1 is a dependency of edit session 4.

Edit session 6, which covers data from July and August (represented by the orange arrows), represents an edit session that is currently in progress but not committed. Because it has not been committed, the managed datastream representing the quality-controlled version of the data only contains data through the end of June, which was committed to the managed datastream with edit session 5. Once edit session 6 is completed and committed, the managed datastream will be extended to the end of August using data generated from edit session 6.

All QC history and the files that define the edit sessions represented in the diagram (everything in the white box) belong to the managed datastream as datastream file attachments. The managed datastream’s observations and all QC history and session file attachments should only be created and modified by the QC App (or other apps that correctly manage QC history) to maintain the integrity of the QC history.

Figure 1. HydroServer QC history DAG design example.

Depending on the selected time range of an edit session, the QC App may need to construct the local copy of the data the user sees in their edit session within the QC App from both the source datastream and the managed datastream. The left-side DAG in Figure 2 shows a source datastream containing three months of data, with two months (January and February) committed to a managed datastream. Blue arrows in the diagram represent the flow of committed data from the source datastream to the managed datastream. Orange arrows represent the flow of data from the source and managed datastreams to the local copy of the datastream being edited by the user in the QC App for the in-progress edit session 2. The in-progress edit session (edit session 2) covers February and March data. No March data has been committed to the managed datastream, so the QC App must fetch March data from the source datastream. Because February data has already been committed to the managed datastream in edit session 1, the QC App must pull February data from the managed datastream, not the source datastream to ensure that edits made in prior edit sessions are brought into the data to be edited in edit session 2.

A user may want to see what operations were performed in session 1, to "undo" an erroneous operation applied to February data for example. To do so, the QC App must fetch January and February data from the source datastream and apply all edit operations from edit session 1 to January and February before the user can view the outputs of edit session 1 operations applied to the February data.

When edit session 2 is completed and committed, the QC App will perform a single replace operation to the managed datastream containing the new February and March data generated by the session. Existing February data in the managed datastream will be replaced, and new March data will be appended at the same time. The session is then marked as committed and the updated resulting DAG is shown on the right side of the diagram in Figure 2.

 Figure 2. HydroServer QC history DAG before and after a commit.

## 5 Creating and Modifying a QC History for a Datastream


A QC history can be created for a datastream in the HydroServer QC App using the following steps:

- From the QC App’s “Select” tab, a user selects one or more datastreams (up to five) to plot. Any datastream for which the user has view permission can be plotted. Existing source and managed datastreams will be clearly marked.
- To create a new managed datastream, users will click “Create Datastream for Editing” which will open a form to create a new managed datastream.
- Users must first choose a source datastream for the managed datastream to inherit metadata and source data from.
- Once selected, all form fields will be populated with the source datastream’s metadata.
- Users must select a new processing level for the managed datastream. They may optionally edit any other metadata as well.
- Once finished, users will click “Create datastream”
- The QC App will create the datastream in HydroServer, add an empty QC History to it, and tag the chosen source datastream. The new managed datastream will be added to the plot view (initially empty).
- Once added to the plot, up to one managed datastream from the list of plotted datastreams can be selected for editing. Once selected, the user may switch over to the “Edit” tab of the QC App.
- On the “Edit” tab, all edits to the managed datastream selected for editing must occur within an edit session.
- If an in-progress edit session already exists for the managed datastream, that session will be opened.
- If no active edit session exists, the user must click “Start New Edit Session”. This will open a form where the user selects the datetime range of their session and a description/comment explaining the purpose of the session. Once confirmed, the QC App will save the in-progress session to the QC History, and the user can begin editing.
- New managed datastreams will be empty by default. Thus, the QC App will provide an operation to “Copy data from source” that copies observations from the source datastream into memory within the edit session’s time range. For new edit sessions that cover time ranges that exist in the source datastream, but not in the managed datastream, this operation could be automated.
- The user’s edit session will record the set of edits made by the user to the managed datastream within the selected phenomenon time range.
- Each time a user selects a set of data values and then clicks an edit tool (e.g., interpolate, delete, flag, etc.), the data in the plot is modified to reflect the edit, and a new edit event is added to the edit session within the history logging the following information:
- The user that created the edit event (this may be stored at the edit session level given that a single user will perform an edit session).
- The datetime that the edit event was performed.
- The function that was executed (insert, delete, adjust, interpolate, flag, etc.).
- The list of data values that was affected (the selection).

## 6 Saving Histories and Edit Sessions


A QC history is created by the QC App when a user initiates QC for a datastream (see section above). Edit sessions may occur over time as new data become available in the source datastream or as previous edit sessions are reviewed. The section above describes how an edit session is created. The QC App will support the following states for saving an edit session:

- In Progress: The edit session is recorded in the QC history but observations have not been saved to the managed datastream. The purpose of this state is to enable a technician to perform QC editing on a set of data values and then have those edits reviewed and potentially approved by another user. Only one in progress session is allowed per managed datastream at a time.
- Committed: The edit session is recorded in the QC history and materialized in the managed datastream.

## 7 Business Rules


The following business rules must be enforced by the QC App when generating and editing QC histories and sessions. It is important to note that HydroServer’s general functionality will not enforce these business rules. Thus, it is important that organizations using the QC App to record QC histories use not only the technical constraints established by the QC App but also develop QC rules and procedures to ensure these business rules are consistently applied by people.

### 7.1 Datastream Relationships


- Each managed datastream will have a single source datastream defined (e.g., a raw datastream). Source datastreams will be tagged with downstream managed datastreams using HydroServer’s tagging system.
- A history must encode the identifier for the source datastream. The history file will be attached to the managed datastream using HydroServer’s file attachment system. The managed datastream and its history file will be created by the QC App when a user selects a source datastream to perform quality control on. All metadata for the managed datastream will be copied from the source datastream selected by the user by default, but the QC App will require the user to select a different processing level for the new managed datastream. The user may choose to modify other metadata for the managed datastream as well. The form will be similar to the “create datastream from template” functionality of the HydroServer data management app.
- The source datastream needs to be treated as a source of truth and must be immutable once QC has been initiated. The QC App will not allow editing of datastreams tagged as source datastreams. New observations can be streamed in and appended to the source datastream, but existing observations within any period that have been subject to a QC session must not be altered or deleted. HydroServer’s API will provide an observation checksum utility that the QC App can use to determine whether a source datastream’s observations have been edited over the phenomenon time range of the corresponding managed datastream, but datastream immutability cannot be enforced or guaranteed by HydroServer.
- Managed datastreams output from the QC process must only be updated through QC edit sessions committed to the history. Any external data streaming or direct modifications to the datastream outside the context of the QC history, especially to portions of the data that already have QC applied, may break data provenance. It would be possible for other software applications to modify the history for a datastream, but all software creating modifications to a datastream for which a history exists must create edit sessions and commit them to the history.
- A source datastream can serve as the source for any number of managed datastreams.

### 7.2 Edit Sessions and History


- A history contains one or more chronologically ordered edit sessions and encodes the QC history DAG.
- An edit session represents a unit of work by a user and encodes all edit operations performed in that edit session.
- The end date of selection for an edit session cannot extend past the end of the source datastream. This prevents the selected data from changing as new data are appended to the source datastream.
- The QC history must be contiguous in time:
- There cannot be a gap between the start date of a new edit session and the current end date of the history.
- If a new edit session is being created before the start date of the history (e.g., to perform QC on recently inserted historical data), there cannot be a gap between the end date of the edit session and the start date of the history.
- Edit sessions must be executed in chronological order to transform the source datastream (e.g., raw data) to the managed datastream (quality-controlled data).
- Each edit event within an edit session has the following attributes:
- Is created by and attributed to the user who created the session.
- Event type (e.g., interpolate, adjust, drift correct, flag).
- Operates on a set of user-selected data values defined as an attribute of the event.
- Is timestamped.
- An optional comment by the user as to the purpose of the edit event (e.g., “Interpolated these values after consulting the field notes”).
- Edit events defined within an edit session must be executed in order.

### 7.3 Data Value and “Undo” Constraints


Modifying the source datastream independent of a recorded history that has been created for that datastream will invalidate the input data and potentially all downstream selection and edit events. Similarly, modifying the steps of an intermediate edit session within a history (e.g., deleting an edit event from an intermediate edit session) would impact and potentially invalidate all downstream edits that follow. Thus, the following constraints are required to preserve the integrity of a QC editing history:

- Data values in source datastreams must be immutable over the time ranges of each linked managed datastream. In other words - source datastream observations that have participated in an edit session cannot be editable. Performing edits to observations within a source datastream that have participated in an edit session (including inserting data values within a time period for which an edit session has been conducted) will invalidate all downstream QC operations. The following are exceptions:
- New data can be appended to the end of the source datastream.
- Historical data can be appended to the beginning of the source datastream.
- Rolling back (undoing) changes made during the QC process will be possible using two methods:
- Undoing changes sequentially from the end of a history until the user reaches the operation that must be undone. Users would then have to perform the subsequent set of operations again. Users will also be able to roll changes back to any edit session within the recorded history and then start editing from there. This will effectively delete any edit sessions downstream of the edit session the user chooses to roll back to.
- Create a new edit session at the end of an editing history that makes the desired edits so that the undo/delete does not have to be done. This preserves the full history and is the encouraged solution (rather than rolling back a bunch of edit sessions and having to redo them).

### 7.4 Datastream Checksums and Conflict Management


A datastream checksum is a value that can be generated by HydroServer for a subset of observations in a datastream. The checksum will be generated from a combination of the value count of the subset of observations and the ID of the most recently inserted value in those observations.

The checksum can be queried from HydroServer’s Data Management API at any time for any subset of datastream observations and will remain unchanged unless any observations are deleted or inserted within the specified subset. If the checksum is recorded at a point in time and then later changes, the QC App will know that one or more observations were inserted or deleted at some point since the original checksum was recorded without needing to compare all of the individual values within the selection.

Each QC history will store two checksums over the time range covered by the history, one for the managed datastream and a second for the source datastream. A checksum will also be associated with each new edit session for the source data over its time range. These checksums are represented in Figure 3.

In the example shown in Figure 3, checksum A is used to verify the integrity of all source observations referenced by the history. Checksum B is used to verify the integrity of the managed datastream. Checksum C is used to verify the integrity of uncommitted source data referenced by the in-progress edit session 3. When edit session 3 is committed, checksums A and B will be extended to include the newly committed March data.

Integrity checks using these checksums are performed when a new edit session is created or committed, and can also be performed on demand. If an integrity check on checksum C fails, it indicates to the user that the source data they were referencing has changed. They will need to fetch the updated source data and verify it against their uncommitted changes before attempting to commit the session again. If an integrity check on checksum B fails, it indicates that an unrecorded modification was made to the managed datastream. If an integrity check on checksum A fails, it indicates that the source datastream was modified.

Figure 3. Checksums used to verify QC history and session integrity

Datastream checksums allow the QC App to quickly verify data integrity, but they do not identify the cause of a failed check. If an external process modifies the source datastream for example, a user will need to review affected sessions and fix any issues resulting from the unrecorded edit by either changing the value back if possible or modifying downstream edit sessions to account for changes.

## 8 Data Model for Histories and Storage in HydroServer


Histories will be stored in HydroServer as datastream file attachments linked to the managed datastream. The QC history file’s type will be “hsqc_history”, and the QC App will ensure no more than one file of this type is attached to a datastream. The history file will be created in JSON format and will include the following:
- The ID of the source datastream.
- The date/time that the history was created.
- The session ID and commit date/time of the last committed session.
- The session ID and creation date/time of the currently in progress session, if there is one.
- The full time range of the committed history. This should match the phenomenon time range of the managed datastream.
- The most recent checksum of the source datastream over the full time range of the history recorded during the most recent commit.
- The checksum of the full managed datastream recorded during the most recent commit.
- A list of all edit sessions committed to the history with the following summary attributes for each:
- The ID of the edit session.
- The date/time that the edit session was created.
- The date/time that the edit session was committed.
- The start and end phenomenon times covered by the edit session.
- The edit session IDs of all direct dependencies of the session (used to generate the DAG).

Edit sessions will be stored separately in HydroServer as datastream file attachments linked to the managed datastream, also in JSON format. A managed datastream can have any number of QC edit sessions associated with it. Each QC edit session file’s type will be “hsqc_session”. The QC edit session file’s name will include the session ID so the QC App can retrieve any QC edit session referenced in the QC history file. Each edit session file will contain the following:
- A unique ID.
- The user that created the edit session.
- The date/time that the edit session was created.
- A selected set of data values from a source and/or managed datastream defined by a begin phenomenon time and an end phenomenon time.
- Where there are no upstream edit sessions, this selection is made from the original source datastream.
- Where there are upstream edit sessions, this selection is made from the managed datastream.
- The selection may be made from a combination of the managed datastream and source datastream if only part of the new edit session has committed upstream edit sessions.
- A set of ordered edit events initiated by the user during the edit session on the set of selected data.
- A status for the edit session (i.e., in progress or committed) and a date/time at which that status was assigned.
- An optional comment by the user as to the purpose of the edit session (e.g., “Data QC edits for the year 2007” or “QC edits for January 2025”).

It is important that QC history and session files only be created and managed by the QC App, or other apps designed to interact with them properly. HydroServer cannot prevent users with permission to modify datastream attachments from editing or deleting these files manually, so it is important that any users with those permissions know not to modify these files. Each file will include a statement at the top with a warning not to manually delete or modify the files.

## 9 Committing Sessions to Managed Datastreams


When a user commits a session, the QC App will need to perform several operations to commit the session to HydroServer. It is expected that these operations should generally not take longer than several seconds. To commit a session, the QC App will first perform the three data integrity checks described in Section 7.4. After data integrity has been verified, the QC App will perform a replace operation through HydroServer’s Data Management API to save the edited dataset to the managed datastream. Depending on the number of observations being replaced, the QC App may need to upload the data in several chunks. Then, the QC App will generate an updated QC history file and edit session file for the newly committed edit session and upload them to HydroServer. The updated QC history file will include updated source and managed datastream checksums that include the newly inserted data.

## 10 Data Management API Endpoints


The HydroServer QC App will retrieve and manage history and session files via the HydroServer data management API. Thus, other software tools that require access to datastream QC histories can also access them through the data management API. HydroServer’s data management API will be updated with the following general enhancements needed to support the QC App and any other apps with similar functionality.

### 10.1 Datastream Attachments


The datastream attachments endpoints will allow users to attach files to specific HydroServer datastreams, mirroring the existing “photo” attachments for sites. The QC App will use these endpoints to store QC history and session files in HydroServer associated with a managed datastream.

#### 10.1.1 DatastreamAttachments


Endpoint: /datastreams/{datastream_id}/attachments
Methods: GET, POST
Description:
- GET: Retrieve all file attachment references for a given datastream. These will be filterable by type.
- POST: Create a new file attachment reference.

#### 10.1.2 DatastreamAttachment


Endpoint: /datastreams/{datastream_id}/attachments/{attachment_id}
Methods: GET, PATCH, DELETE
Description:
- GET: Retrieve a file attachment reference with the given ID.
- PATCH: Update a file attachment reference. Editable fields are “name”, "type", and "description". The file attachment can also be replaced.
- DELETE: Delete a file attachment reference.

### 10.2 Datastream Tags


The datastream tags endpoints will allow the QC app to tag source datastreams, mirroring the existing site tagging functionality. No changes from the existing site tags are required; site tagging functionality will simply be extended to also cover datastreams.

### 10.3 Observation


Additional observation endpoints will provide more granular functionality related to quality control outside the context of histories and sessions if needed. All observation functionality will be provided in the context of one datastream at a time.

Endpoints that return collections of observations will also include a checksum value in their response headers for the subset of observations being returned. The QC App will use these checksum values to check for changes to source datastreams and identify commit conflicts, but they can be used by any app that needs to be able to verify datastream integrity.

#### 10.3.1 Observations


Endpoint: /datastreams/{datastream_id}/observations
Methods: GET, POST
Description:
- GET: Retrieve observations of a datastream. Observations can be paginated, ordered, and filtered. Users can choose to retrieve observations in either row-oriented, column-oriented, or verbose record formats.
- POST: Create a single observation for a datastream.

#### 10.3.2 BulkCreateObservations


Endpoint: /datastreams/{datastream_id}/observations/bulk-create
Methods: POST
Description:
- POST: Creates one or more observations for a datastream, provided in a compact row-oriented format. Several modes are supported.
- append: Only allows observations after the last recorded observation in the datastream. (default)
- insert: Inserts new observations anywhere in the datastream, as long as the phenomenon times are unique.
- backfill: Only allows observations before the first recorded observation in the datastream.
- replace: Inserts new observations anywhere in the datastream. All existing observations within the phenomenon time range of the new observations will first be deleted.

#### 10.3.3 BulkDeleteObservations


Endpoint: /datastreams/{datastream_id}/observations/bulk-delete
Methods: POST
Description:
- POST: Deletes all observations for a datastream in a given phenomenon time range.

#### 10.3.4 Observation


Endpoint: /datastreams/{datastream_id}/observations/{observation_id}
Methods: GET, PATCH, DELETE
Description:
- GET: Retrieve a specific observation of a datastream.
- PATCH: Edit a specific observation of a datastream.
- DELETE: Delete a specific observation of a datastream.
