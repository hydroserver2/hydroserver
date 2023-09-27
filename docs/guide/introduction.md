# Introduction

## What is HydroServer?

HydroServer is a data management system designed to store, manage, and
share a diverse range of environmental and water data. It builds on the
Open Geospatial Consortium (OGC) SensorThings API to provide a standard
and reliable way for you to handle your data. It consists of three major parts:

- A [web application](web-application.md) where you can register and manage your
  observational sites, define their metadata, and view and download public hydrological data.
- A [Streaming Data Loader (SDL)](loading-data.md) desktop application that will take your preferences as specified in the web application
  and automatically transform and upload your data to HydroServer's database. As long as you have an
  internet enabled sensing device, you should be able to automatically stream your data into our database in real-time.
- [APIs](/api/data-management-api.md) that provide endpoints which allow you to work with HydroServer's data directly. Our web application
  actually uses most of the API endpoints, so users should be able to do most of what they want through that user interface, but we've provided
  documentation for our APIs in case you'd like to build your own application that uses our services or need a specific data query not provided by the app.

## Why HydroServer?

The primary motivation behind HydroServer was a desire for a fast and flexible way to manage
large amounts of data. This is why we built our APIs using TimescaleDB, an extension to PostgreSQL
specialized in retrieving time series data quickly.

We also wanted a system that took a formal approach on how the data was organized so that anyone using the same
standards could more or less plug and play with our services. HydroServer follows the Open Geospatial Consortium (OGC) SensorThings
standards as closely as possible. Among our APIs is a [Django implementation of the SensorThings API](/api/sensor-things-api.md)
as well as a [Django Data Management API](/api/data-management-api.md) which extends these standards to create a fully-fledged data management system.

In every design decision, we aimed for the balance between using stable time-tested tools like Django and PostgreSQL, and modern tools
that claimed significant performance and ease of use improvements like Django Ninja, timescaleDB, and Vue3 in order to get the
best possible data management experience.

## Where to go from here?

If you'd like a hands-on tutorial for setting up a monitoring site and streaming data to a playground verison of the Hydroserver database, head over to the
[Getting Started Guide](getting-started.md)

If you'd like to read some more about our system, feel free to skip around the documentation as most of the sections are fairly self-contained.
We recommend starting with the [SensorThings API](/api/sensor-things-api.md) which will explain more about HydroServer's architecture then moving on to
the other major parts of HydroServer listed at the beginning of this page
