---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: "HydroServer"
  text: "Advanced Water Data Management"
  image:
    src: /logo.png
    alt: HydroServer Logo
  tagline: Empowering Hydrologic Research with Efficient Data Streaming and Sharing
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: Introduction
      link: /guide/introduction
    - theme: alt
      text: GitHub
      link: https://github.com/hydroserver2/hydroserver

features:
  - icon: 💻
    title: Sensor Data Streaming
    details: Stream sensor data directly from your Internet connected datalogger or load data using our Streaming Data Loader software.
  - icon: 💽
    title: Performant Data Storage
    details: Using TimescaleDB with PostgreSQL, we provide a performant data store for your operational data.
  - icon: 🌐
    title: Open Standards Data Sharing
    details: Our services are built in alignment with the latest Open Geospatial Consortium SensorThings standard.
  - icon: 🔓
    title: Public Access to Your Data
    details: Provide convenient and simple access to the data from your monitoring sites via our web user interface and APIs.
  - icon: 💧
    title: Operational Data for Modeling
    details: Contribute your streamflow data to NOAA's National Water Model to enhance continental-scale hydrologic predictions and forecasting.
  - icon: ⚙️
    title: Easy Web Configuration
    details: Create new monitoring locations, observed variables, sensors, and data streams through our web user interface.
---
