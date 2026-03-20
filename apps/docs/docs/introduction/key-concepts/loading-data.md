# Loading Data

The main use case for HydroServer is continuously streaming ongoing data from a source data logger into the database. HydroServer provides the following options for accomplishing this.

## Via an Orchestration System

HydroServer provides two built-in orchestration options for scheduled ETL: the Streaming Data Loader (SDL) desktop app and the Django Celery orchestration system that runs with your HydroServer deployment. Both use data connections and tasks to define how data is extracted, transformed into a standard format, and loaded automatically through the HydroServer API. Once an orchestration system is registered, its jobs can be configured from the Data Management App's `Job Orchestration` page or via the API.

## Via a Client

You can write your own scripts or full on orchestration systems that use the API directly. To make this significantly easier, HydroServer provides client applications such as hydroserverpy: a Python client package that wraps the API so it can be used in straightforward Python one liners: hydroserver.login(), hydroserver.load_data(), etc.

## Via the API

You can always call the API directly. [Go to the API section for more information](/references/api/data-management-api).
