## Possible Needs Attention states:

These are the most important end-user messages the ETL system can return for a task run
that needs user action.

### Configuration / Setup

- Invalid extractor configuration. Tell the user exactly which field is missing or invalid.
- Invalid transformer configuration. Tell the user exactly which field is missing or invalid.
- A required configuration value is missing.
- A required configuration value is null where a value is expected.
- Missing required per-task extractor variable "<name>".
- Extractor source URI contains a placeholder "<name>", but it was not provided.
- Task configuration is missing required daylight savings offset (when using daylightSavings mode).

### Data Source (Connectivity / Authentication)

- Could not connect to the source system.
- The source system did not respond before the timeout.
- Authentication with the source system failed; credentials may be invalid or expired.
- The requested payload was not found on the source system.
- The source system returned no data.

### Source Data Did Not Match The Task

- The source returned a format different from what this job expects.
- The payload's expected fields were not found.
- One or more timestamps could not be read with the current settings.
- This job references a resource that no longer exists.
- The file structure does not match the configuration.

For CSV:
- The header row contained unexpected values and could not be processed.
- One or more data rows contained unexpected values and could not be processed.
- Timestamp column "<key>" was not found in the extracted data.
- A mapping source index is out of range for the extracted data.
- A mapping source column was not found in the extracted data.

For JSON:
- The timestamp or value key could not be found with the specified query.
- Transformer did not receive any extracted data to parse.

### Targets / HydroServer

- HydroServer rejected some or all of the data.
- The target data series (datastream) could not be found.
  - This may happen if the datastream was deleted or the mapping points to the wrong target.

### Unexpected System Error

- An internal system error occurred while processing the job.
- The job stopped before completion.

## Possible OK states:

These are the most important end-user messages the ETL system can return for a successful run.

- Load completed successfully.
- Load completed successfully (<n> rows loaded).
- Load completed successfully (<n> rows across <m> datastreams).
- Already up to date - no new observations loaded.
- No new observations were loaded.
- Already up to date - no new observations loaded (all timestamps were at or before <cutoff>).
- No data returned from the extractor. Nothing to load.
- Transform produced no rows. Nothing to load.
