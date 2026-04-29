# Observations

HydroServer uses the term 'Observations' to describe the actual time-series data values being collected at a monitoring site. Each Observation is a record of what was measured at a specific time and place, along with an optional list of result qualifiers for that data point.

## HydroServer's Timestamps

HydroServer stores all data within it's database using UTC timestamps. This is important to ensure unambiguous recording of the date/time values associated with each Observation. This has important implications for data loading and data access workflows to ensure that it is understood how data are being entered into HydroServer and what the timestamps for retrieved data mean.
