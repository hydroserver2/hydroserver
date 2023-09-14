# Introduction

## What is HydroServer?

HydroServer is a data management system designed to store, manage, and
share a diverse range of environmental and water data. It builds on the
Open Geospatial Consortium (OGC) SensorThings API to provide a standard
and reliable way for you to manage your data. It consists of two major parts:

- A data management [web application](http://hydroserver-dev.ciroh.org/) where you can register and manage your 
  observational sites, define their metadata, and view and download everyone else's hydrological data.
- A Streaming Data Loader (SDL) desktop application that will take your preferences as specified in the web application 
  and automatically transform and upload your data from CSV files to HydroServer's database.
