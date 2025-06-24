# Introduction

## What is HydroServer?

HydroServer is a data management system designed to store, manage, and
share a diverse range of environmental time-series data. The following is a list of HydroServer's main parts:

### A Django REST API

This is the “server” in HydroServer. Most organizations using HydroServer will fork our [hydroserver-ops GitHub repository](https://github.com/hydroserver2/hydroserver-ops) and use it to spin up their own server, whether on Google Cloud Platform, Amazon Web Services, or a local machine. Throughout this documentation, we often refer to “an instance of HydroServer.” This means you've copied our source code and deployed it as your own live instance.

### Client-side applications and packages which include:

1. The Data Management Web App. This will be the main website for your HydroServer instance where you can register and manage your sites, define their metadata, and view and download your data.

2. Orchestration systems. Orchestration software can be downloaded onto a computer or data logger to be put to work extracting data from field sensors or URLs, transforming those files into a standard format HydroServer can read, and loading those data into HydroServer via the REST API. Custom schedules can be set for each dataset.

3. A Python package named hydroserverpy. This is a wrapper around the REST API which makes managing data in HydroServer much easier for those interesting in doing so programmatically.

## Next Steps

If you'd like a hands-on tutorial for setting up a monitoring site and streaming data to a playground instance of Hydroserver, head over to [HydroServer 101.](/tutorials/hydroserver-101.md)

If you'd like to read more about our system, we recommend starting with [Key Concepts](/introduction/key-concepts/sites).
