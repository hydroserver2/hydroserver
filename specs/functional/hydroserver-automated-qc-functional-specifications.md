# HydroServer Automated Data Monitoring and Quality Control

_Functional Specifications_

## 1 Introduction


The HydroServer platform includes front-end web applications and back-end operational database and web services for collection, retrieval, management, and sharing of time series of hydrologic and water management measurements made at stream, diversion, reservoir, climate, and other monitoring stations. A major component of HydroServer is a Job Orchestration System that is used for extracting, transforming, and loading data from various data sources external to the HydroServer system. Many of these data sources may deliver data values for continuous time series measurement data in near real-time. Given the volume of data that can be scraped/harvested in this way, it can be difficult for humans to monitor the quality of incoming data and to detect issues in a timely manner.

This document describes requirements and functional specifications for automated, rules-based data monitoring and quality control (QC) that will operate on data loaded to HydroServer via its Job Orchestration System to identify potential errors in incoming data, flag them for further review and potential exclusion from downstream automated data aggregation or analysis tasks, and send notifications to appropriate people who can review and fix problems.

## 2 Definitions


Datastream: A time series of data values for an observed property collected at a monitoring site having a specific processing level.

Data QC monitoring task: A specific type of task configured within HydroServer’s Job Orchestration system that monitors the data values for a datastream and applies specific data monitoring rules.

Data monitoring rule: A logical test used to determine whether new data values received for a datastream meet defined criterion value(s). For example, are new data values within a value range defined by a plausible minimum and maximum value?

Orchestration System: A software or software system that executes scheduled extract, transform, and load (ETL) tasks and data QC monitoring tasks.

## 3 Requirements


The following are requirements that must be met by the HydroServer automated data monitoring and quality control functionality:

- The functionality must be configurable for adding data monitoring rules for any datastream within a HydroServer instance.
- The functionality must honor HydroServer’s access control.
- Any user with at least “edit” functionality on a HydroServer workspace should be able to configure data monitoring tasks for datastreams within that workspace.
- See separate functional specifications for HydroServer’s Identity and Access Management
- The functionality must be integrated with and deployed with HydroServer’s Job Orchestration system for executing data monitoring tasks. HydroServer’s Job Orchestration system will provide the user interface for this functionality.
- Configuration and status information must be integrated with the Job Orchestration page of HydroServer’s Data Management App where data monitoring jobs can be created, monitored, edited, and deleted.
- It must support the following specific data monitoring rules:
- Automated range checks – detection of out-of-range data values based on user-specified maximum and minimum values for a datastream. Battery voltage checks can be defined as range checks.
- Rate of change checks – detection of a value that changes from a previous value by an amount greater than a user-specified threshold.
- Persistence checks – detection of a persistent data value for longer than a user-specified threshold time period for a datastream.
- Missing data checks – detection of periods of missing data longer than a user-specified threshold time period for a datastream (i.e., datastreams that have not reported new data for longer than a threshold time period).
- Zeros checks – detection of time periods where the value of zero is reported for longer than a specified threshold.
- It must enable configurable notifications to a designated list of recipients for data QC monitoring tasks.
- It must communicate with HydroServer’s operational database through HydroServer’s APIs.
- The Orchestration System must automatically and efficiently run data QC monitoring tasks within a process queue according to the schedule that has been set for each task.
- Individual data QC monitoring tasks must be independent.
- The Orchestration System must keep a log of success information and errors encountered for each data QC monitoring task for reference during debugging.
- The Orchestration System must follow HydroServer’s dev, test, and production deployments to enable development and testing of data QC monitoring tasks prior to implementing them in the production instance.
- The Orchestration System must store in the configuration for a scheduled data QC monitoring task the date on which they were last updated and by whom. This information will be displayed when the configuration for a task is accessed.

## 4 Supported Functionality


The following describe specific functionality that will be provided by the HydroServer automated data monitoring and quality control functionality.

### 4.1 User Interface


- Users will be able to create, edit, and delete data QC monitoring tasks via HydroServer’s Job Orchestration page within HydroServer’s Data Management web application.
- Users with “read” permissions to a workspace will be able to view data monitoring tasks on the Job Orchestration page for that workspace.
- Users with at least “edit” permissions to a workspace will be able to create, edit, and delete data QC monitoring tasks within a workspace.
- Users will be able to monitor the status of configured tasks via HydroServer’s Job Orchestration page within HydroServer’s Data Management web application
- The Job Orchestration page will display tasks in a list
- Filters on the page will enable users to display tasks by type (e.g., data QC monitoring tasks)
- Data QC monitoring tasks will show status messages indicating:
- When the task was last un
- When the task will next run
- Visual indication of whether the task is behind schedule or on schedule.
- Visual indication of whether any data monitoring rules configured within the task have been violated.
- A “details” view for a task will provide log information for users to help with debugging.
- Similar to ETL tasks, users will be able to pause a data QC monitoring task or click a button to immediately run a task.

### 4.2 Task Configuration


- Each data QC monitoring task will be configurable to run one or more data monitoring rules on one or more assigned datastreams.
- Users will determine the granularity of tasks to be run by adding data monitoring rules and datastreams to a task.
- Additional configuration options for individual tasks will include:
- Data monitoring rule settings - specific settings for data monitoring rules added to a data QC monitoring task:
- Min and max values for range checks
- Threshold value for rate of change checks
- Threshold time period for persistence checks
- Threshold time period for missing data checks
- Threshold time period for zero value checks
- Flags - specific data qualifying comments to be added to data values that violate data monitoring rules.
- Schedule - when and how often a task will run
- Start time
- End time
- Execution interval
- Notifications - email addresses for people that will receive notifications when a rule within a task has been violated
- Each task will have a configuration view that allows users to add data monitoring rules, set configuration settings, and add datastreams to be monitored by that task.

### 4.3 HydroServer API and hydroserverpy functionality


- HydroServer’s APIs will support scripting of data QC monitoring tasks
- The hydroserverpy Python client package will provide convenience functions for basic create, read, update, and delete (CRUD) functions on data QC monitoring tasks.
- HydroServer’s Job Orchestration task management framework should be the same for extract, transform, and load (ETL) tasks and data QC monitoring tasks.

### 4.4 Error Handling, Logging, and Notifications


- Error handling for configured data QC monitoring tasks will use existing logging capabilities of HydroServer’s Job Orchestration page.
- Failed data QC monitoring tasks will send notifications via email to a designated set of workspace collaborators notifying them that the task was unable to run.
- This functionality will be the same across all task types - i.e., ETL, data QC monitoring
- Individual data QC monitoring tasks will be independent. Failure of one task will not impact other tasks.
- Notifications for violations of data monitoring rules configured within a data QC monitoring task will be sent via email to the list of email addresses configured in the settings of the task.
- Email notifications will be sent in a daily digest to reduce the number of emails sent by the system and received by users
