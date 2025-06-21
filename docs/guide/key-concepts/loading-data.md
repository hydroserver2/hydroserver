# Loading Data

The main use case for HydroServer is continuously streaming ongoing data from a source data logger into the database. HydroServer provides the following options for accomplishing this.

## Via an Orchestration System

The first option is to download our orchestration software onto a computer to allow it to function as an Orchestration System - a machine that's able to interpret a configuration file that tells it how to extract data from a source location, transform that data into a standard format, and load that data automatically to HydroServer's API. HydroServer allows a wide range of remote systems to register themselves as 'Orchestration Systems'. Once a system is registered, various jobs can be configured for it from the Data Management App's 'Job Orchestration' page or via the API. Orchestration systems are discussed in detail [in their own section.](/orchestration/orchestration-overview)

## Via a Client

You can write your own scripts or full on orchestration systems that use the API directly. To make this significantly easier, HydroServer provides client applications such as hydroserverpy: a Python client package that wraps the API so it can be used in straightforward Python one liners: hydroserver.login(), hydroserver.load_data(), etc. [Go here for in depth discussion on clients.](/applications/hydroserverpy/overview)

## Via the API

If you're not interested in using HydroServer's helper packages, you can always call the API directly. [Go to the API section for more information](/api/data-management-api).
