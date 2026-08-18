# Datastreams

A `datastream` is a time series of observations for a particular observed property created at a monitoring site. The datastream concept encompasses all of the metadata describing exactly one time series or "stream" of data at that monitoring site.

For example, you could have a datastream of:

- Water temperature (the observed property)
- having Units of Degree Celsius
- in the Logan River at Mendon Road (the monitoring site's location)
- with Processing Level 0, Raw data (the processing level)
- a Sampled Medium of Surface Water
- measured using A YSI EXO2 Multiparameter Water Quality Sonde sensor

A datastream acts as the hub for understanding what's being measured at a given location. For example, if you want to know what's being measured, you'll ask the API for `datastream.observed_property` which will return 'Water temperature' along with metadata describing exactly what 'Water temperature' means to your organization. If you want to know how the observations are produced, you'd ask for `datastream.method`, which may include instrument details when applicable. If you want the actual data, you'll call `datastream.observations`.

## Metadata Types

In HydroServer, we describe datastream metadata in two groups:

1. Direct metadata are simple text fields that describe the datastream and are unique to this particular stream of data.

2. Linked metadata are groups of metadata that can be reused across many datastreams. For example, if you were managing a large group of weather stations, you'd likely want to measure air temperature at each location, but you'd probably only want to define the unit 'degree celsius' once and reuse it. Linked metadata lets you define certain metadata once (units, methods, observed properties, processing levels) and simply link your datastreams to them.

Below is a brief definition of each available linked metadata group a datastream can be linked to:

**- Unit** refers to the measurement units of the data (like liters, meters, etc.). Each unit has a name, symbol (like 'C' for degrees Celsius), type, and optional external definition URI. Units for HydroServer are derived from
[ODM2's Units controlled vocabularies list for Units](http://vocabulary.odm2.org/units/).

**- Processing Level** indicates the degree of processing or analysis that the data within that datastream has undergone, which includes a code, name, description, and optional external definition URI. Users are free to use their own conventions, but a new HydroServer instance provides the following defaults that can be loaded from templates like the other linked metadata:

- 0: Raw
- 1: Quality controlled data
- 2: Derived products
- 3: Interpreted products
- 4: Knowledge products
- -9999: Unknown

**- Observed Property** is the specific characteristic or attribute being observed, like temperature or flow rate. As with Units, we have adopted
[ODM2's Observed Property controlled vocabularies list](http://vocabulary.odm2.org/variablename/).

**- Method** describes how observations are produced by an instrument, technician, laboratory procedure, simulation, or computation. Instrument methods can optionally record the sensor model, manufacturer, and a model definition link. The SensorThings API maps Method records to the standard Sensor entity for interoperability.

**- Result Qualifier** provides additional information about the result of an observation, like its accuracy, reliability, or field conditions that may have impacted the observation result. Each result qualifier has a code and a description to clarify its meaning. For instance, if ice affects a sensor, impacting the observation's reliability, a user can add a result qualifier with the code 'ICE' to denote this specific condition. This helps in understanding and interpreting the data accurately, especially when external factors influence the measurements.

## Data Support and Spacing

It is important to specify both the support and spacing of the data to ensure proper interpretation by users. Each datastream has a time aggregation interval that serves as a definition of the measurement support – i.e., the temporal window over which each data value is measured and aggregated (if aggregation is implemented). Each datastream also has an intended time spacing that defines the intended amount of time between each data value within that datastream. 
