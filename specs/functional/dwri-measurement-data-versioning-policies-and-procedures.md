# DWRi Measurement Data Versioning Policies and Procedures

Last Updated: December 18, 2025

## 1 Introduction


The Technology Modernization Roadmap developed by Utah State University for the Utah Division of Water Rights (DWRi) (Horsburgh et al., 2024b) recommended in Task Group 2 that DWRi establish and maintain formal data versioning along with standard policies, rules, and procedures for quality control (QC) review of important dataset types. The Technology Modernization Roadmap was based on recommendations from an earlier Hydroinformatics gap analysis study (Horsburgh et al., 2024a). Quality Control (QC) refers to evaluating the collected data by reviewing measurements after collection to identify errors, anomalies, or gaps in the dataset. QC also includes applying necessary corrections—such as interpolation or other adjustment methods—to ensure the final data is accurate and ready for analysis.

DWRi’s operational goal is to apply established policies and data QC procedures to ensure that data used in DWRi’s analyses, distribution accounting, and operations are accurate, reliable, and consistent. It also supports DWRi’s desire to have transparency and traceability from raw observations through data versions used for specific analyses, including processes used for computing the data records used in distribution accounting procedures and data records that become the “approved” data of record.

The following additional recommendations related to data versioning and QC from the Hydroinformatics Gap Analysis are also relevant:
- Ensure that DWRi’s database serves as a source of truth, including storing raw data along with quality controlled datasets in ready-for-analysis forms.
- Establish data governance practices that ensure data quality, security, and provenance are maintained.
- Formally define, document, and standardize data cleaning and processing workflows and associated policies.
- Establish standardized policies, rules, and procedures for QC review of important dataset types.
- Standardize the data QC review process through adoption of standardized data presentation, tools, and training.
- Establish and maintain formal data versioning.
- Enhance DWRi’s existing automated data monitoring/notification system to implement simple, rules-based quality assurance/QC.
- Develop a software application that integrates with HydroServer to enable data visualization and manual data QC for DWRi’s data managers based on policies provided by DWRi.

The purpose of this document is to formally define DWRi’s measurement data versioning policies and procedures in response to these recommendations from the Gap Analysis. Given that DWRi has adopted the HydroServer software stack for storing and managing measurement data time series, this document describes how DWRi will use HydroServer’s data model and software tools for data versioning and QC procedures.

## 2 Data Processing Levels


HydroServer stores time series of observational data as “datastreams” that represent a time series of observations for an observed variable (diversion flow, reservoir storage, etc.) measured at a particular measurement station. HydroServer uses the concept of a “processing level” (PL), which is an attribute of a datastream that is used to clearly indicate the degree of Quality Control (QC) or processing that a datastream has undergone. It serves as a version indicator, allowing users to distinguish between raw measurements and reviewed or processed, final datasets. Processing levels are defined by three attributes, including code (e.g., “0” or “Raw”), definition (e.g., “Raw data”), and explanation (e.g., “Raw data streamed from the field that have not been subject to quality control review.”). HydroServer allows users to define the specific processing levels to be used, and, in practice, different organizations may adopt different processing level schemes.

This document describes how DWRi defines and uses processing levels within HydroServer. Specifically, it details how HydroServer software tools transform a source datastream (input) into a destination datastream (output), based on specific QC rules, policies, processes, and procedures established by DWRi.

DWRi adopted the following three operational processing levels based on the recording interval of the data (sub-daily or daily) and whether the data have been reviewed by a DWRi employee (raw or reviewed): P0 for raw sub-daily data, PL for computed daily data, and PL2 for reviewed daily data (Table 1). These processing levels are also illustrated in Figure 1.

Table 1. DWRi’s measurement data processing levels.
Code
Definition
Explanation
PL0
Raw sub-daily data or instantaneous field measurements
Raw sub-daily data are either: (1) collected directly from a datalogger in the field that records sub-daily data; or (2) manually read or measured by a DWRi staff at a certain time. Raw sub-daily data is archived as-is and will not be changed or deleted by anyone.
PL1
Automatically generated or scraped daily data
Automatically computed daily data are produced by aggregating raw sub-daily data (PL0) to a daily recording interval after auto-applying basic outlier removal. Field Services will set the min and max thresholds to remove out of range values before computing the daily average.

DWRi may receive already aggregated daily data from data providers which will also be designated as PL1. The aggregated and scraped daily data is archived as-is and will not be changed by anyone.

Migrated old daily data that has an untracked mix of raw and reviewed data will be stored as PL1 and given a qualifier “Migrated”
PL2
Reviewed daily data
Reviewed and quality controlled daily data from PL1 (aggregated daily data.)

Re-scraped daily data after providers have reviewed and approved their provisional daily data.

Reviewed data (PL2) is a copy from the original raw data (PL1) that will contain QC edits made by DWRi staff. Changes will be tracked via the HydroServer QC app and recorded in a “history” that defines all changes made to move from raw to reviewed processing levels. Design and functional specifications for the HydroServer data QC App and the design and functional specifications for histories stored and managed by that app are provided in separate documents.

Figure 1 shows that PL1 aggregated raw daily data is automatically computed from raw sub-daily data (PL0). PL1 data may also be scraped from data providers with provisional data that is already aggregated to a daily time step. PL2 is aggregated corrected daily data that have been reviewed in the QC process.

Figure 1. Processing levels for DWRi’s measurement data.

## 3 Data Versioning Using Processing Levels


The following data versioning rules will be enforced as shown in Table and Figure 1:

- Raw sub-daily datastreams having ProcessingLevel = PL0 will have ONE corresponding daily datastream with ProcessingLevel = PL1 that is auto generated from the raw sub-daily datastream and is stored-as-is.
- Computed and aggregated daily data, regardless of source (i.e., USGS, USBR, Utah Water Conservancy District, etc.) will be designated with ProcessingLevel = PL1 (all data sources with daily data). There will be ONE datastream with ProcessingLevel = PL1 for each observed property from each data source having daily data. Each daily datastream with ProcessingLevel = PL1 will have ONE corresponding reviewed daily datastream with ProcessingLevel = PL2 (reviewed daily data).

## 4 Automated Data Versioning


Some of DWRi’s data versions will be created automatically. The following procedures will be used for automated data versioning:

- DWRi’s automated data scraping system (the job Orchestration System) will be used to generate PL0 and PL1  datastream versions. This system automatically retrieves data and writes it to HydroServer’s database for these datastreams.

## 5 Data QC Review Policies


The following policies will be followed for data QC:

- Data QC review of PL1 raw daily dataset will be conducted by DWRi employees with a frequency as defined by DWRi’s QC policy, which is yet to be established.
- Data QC review will be conducted only by DWRi employees who have been designated for this task and who have been given “editor” access to the HydroServer workspace within which the sites and data for which they are responsible are stored.
- Data QC review will be conducted by DWRi employees according to DWRi’s policy defining standardized procedures and best practices documented for each observed property (e.g., stage, discharge, reservoir storage, etc.). The QC policy, which is under development, will define how staff will perform QC and which procedures to apply under which circumstances. The QC policy will describe QC procedures for each observed property describing how to approach QC for that particular observed property.
- DWRi employees will complete data QC review, editing, and flagging using the HydroServer QC App.
- All QC edits made to a datastream will be recorded in the HydroServer QC App and will be part of a formal, recorded “history” that defines the edits required to transition a datastream from raw to reviewed status.
- Changes to PL2 are only allowed through the QC App or any other HydroServer QC API compliant apps. Any changes outside them may compromise the integrity of the history of a datastream. Any edits made to a “managed datastream” (a quality controlled datastream managed by the QC App (i.e., PL2) outside of the data QC App that impact data values within time ranges for which a QC History exists must be recorded in the QC History for that datastream. Otherwise the QC history for the “managed datastream” will be broken. This means that any software that enables changes to data for which a QC history exists must use HydroServer’s API to record those changes in the history in the same way the QC App records changes made by users in the history. Details of how managed datastreams and QC histories are handled are covered in the design and functional specifications for QC histories document.

## 6 Data Versioning Policies


The following data versioning policies will apply to DWRi’s measurement data:

Distribution accounting will be conducted using the “best available data” which should prioritize PL2 data that is already reviewed where it exists and default to recent PL1 data where PL2 data does not yet exist. All distribution accounting is based on daily data. Modifications may continue to be made to PL2 data in cases where the distribution accounting process reveals issues with the measurement data. These changes will be recorded in the QC history for the PL2 data to ensure that the provenance of these changes is saved.
PL2 reviewed data represent DWRi’s best measurement value (or estimation) of what actually occurred at a measurement station on a daily time step and is considered the official “data of record”.
References

Horsburgh, J. S., D. Slaugh, K. Lippold (2024a). Utah Division of Water Rights: Hydroinformatics and Technology Gap Analysis Report, HydroShare, https://doi.org/10.4211/hs.9d02ff3c946249fe9cbc39b2a16c829e

Horsburgh, J. S., D. Slaugh, K. Lippold (2024b). Utah Division of Water Rights: Technology Modernization Roadmap, HydroShare, https://doi.org/10.4211/hs.6bb192887d474555a75f1df86e9a9f66
