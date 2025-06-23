# Datastreams

If a site is the location at which data events happen, a datastream is all the metadata describing exactly one stream of data at that location.

For example, you could have a datastream of:

- Temperature (the observed property)
- having units of Degree Celsius
- at The Quad by Old Main (the site's location)
- with processing level 0, Raw data (the processing level)
- a sampled medium of air
- measured using the Onset HOBO: SD‑TEMP sensor

A datastream acts as the hub for understanding what's being measured at a given location. For example, if you want to know what's being measured, you'll ask the API for datastream.observed_property which will return 'temperature' along with metadata describing exactly what 'temperature' means to your organization. If you want to know what kind of physical hardware is making the measurements, you'd ask for datastream.sensor which will return the make and model of the sensor along with links and other metadata if provided. If you want the actual data, you'll call datastream.observations.

## Metadata types

In HydroServer, we describe datastream metadata in two groups:

1. Direct metadata are simple text fields that describe the datastream and are unique to this particular stream of data.

2. Linked metadata are groups of metadata that can be reused across many datastreams. For example, if you were managing a large group of weather stations, you'd likely want to measure temperature at each location, but you'd probably only want to define the unit 'degree celsius' once and reuse it. Linked metadata lets you define certain metadata once (units, sensors, observed properties, processing levels) and simply link your datastreams to them.

Below is a brief definition of each available linked metadata group a datastream can be linked to:

**- Unit** refers to the measurement units of the data (like liters, meters, etc.). Each unit has a name, description, symbol (like 'C' for degrees celsius), and type.
[ODM2's Units controlled vocabularies list](http://vocabulary.odm2.org/units/)

**- Processing Level** indicates the degree of processing or analysis that the data has undergone, which includes a code, definition, and explanation. Users are free to use their own conventions, but a new HydroServer instance provides the following defaults that can be loaded from templates like the other linked metadata:

- 0: Raw data
- 1: Quality controlled data
- 2: Derived products
- 3: Interpreted products
- 4: Knowledge products
- 9999: Unknown

**- Observed Property** is the specific characteristic or attribute being observed, like temperature or flow rate.
[ODM2's Observed Property controlled vocabularies list](http://vocabulary.odm2.org/variablename/)

**- Sensor** is the device or methodology used to collect the data. The Sensor model captures details like type, manufacturer, and model, essential for understanding data collection methods.

**- Result Qualifier** provides additional information about the result of an observation, like its accuracy or reliability. Each Result Qualifier has a code and a description to clarify its meaning. For instance, if ice affects a sensor, impacting the observation's reliability, a user can add a Result Qualifier with the code 'ICE' to denote this specific condition. This helps in understanding and interpreting the data accurately, especially when external factors influence the measurements.

## Observations

HydroServer uses the term 'Observations' to describe the actual time-series data being collected at the site. Each observation is a record of what was measured at a specific time and place, along with an optional list of result qualifiers for that data point.
