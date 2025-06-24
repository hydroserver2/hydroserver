# Overview of the `hydroserverpy.etl` Package

The `hydroserverpy.etl` package provides a set of tools and classes to facilitate Extract, Transform, and Load (ETL) operations for time series data. It helps you move data from external sources (such as remote APIs, files, or HTTP endpoints), transform it into a consistent format, and then load it into a HydroServer instance. By leveraging the patterns and interfaces defined in this package, you can quickly build ETL pipelines.

## What is `hydroserverpy.etl`?

Data often come from a variety of disparate sources, each with different formats, structures, and data retrieval methods. The `hydroserverpy.etl` package offers:

- **Extractors** that know how to pull data from external sources (e.g., an HTTP endpoint or a local file).
- **Transformers** that convert raw, extracted data into a standardized Pandas DataFrame format, ready for loading.
- **Loaders** that push transformed data into the HydroServer datastore.
- **Orchestration** that integrates all three steps—extract, transform, load—into a single seamless process.

## Key Components

### Extractors

**Extractors** are responsible for connecting to, authenticating with, and retrieving data from a system. For example, the `HTTPExtractor` class is designed to fetch data from an HTTP/HTTPS endpoint. It can dynamically inject URL variables and set query parameters based on the target system’s data requirements.

**Example:**

```python
from hydroserverpy.etl.extractors import HTTPExtractor

extractor = HTTPExtractor(
    url="https://api.example.com/data/{customer_id}",
    url_variables={"customer_id": 555},
    params={"sensor_id": 123},
)

extracted_data = extractor.extract()
```

### Transformers

**Transformers** convert the raw extracted data into a standardized format. A common transformer is the JSONTransformer, which uses JMESPath queries to parse JSON responses and turn them into a Pandas DataFrame, ready for loading into HydroServer.

Example:

```python
from hydroserverpy.etl.transformers import JSONTransformer

transformer = JSONTransformer(
    query_string="data_array",
    source_target_map={"water_level": "waterlevel_id", "discharge": "discharge_id"}
)

transformed_dataframe = transformer.transform(extracted_data)
```

The standardized format transformers return is a Pandas dataframe where the first column is timestamps in the ISO 8601 format and the rest of the columns are data values where the headers are the unique identifiers for the target system's datastreams.

For example, if we extract a JSON file from the the source system like this:

```JSON
{
  "data_arrary": [
    {
        "timestamp": "2025-01-01T00:00:00Z",
        "water_level": 22.5,
        "discharge": 0.8
    },
    {
        "timestamp": "2025-01-01T01:00:00Z",
        "water_level": 22.8,
        "discharge": 0.85
    },
    {
        "timestamp": "2025-01-01T02:00:00Z",
        "water_level": 23.0,
        "discharge": 0.9
    }
  ]
}
```

The JSONTransformer will use the source_target_map parameter to return a Pandas DataFrame like this:

```text
            timestamp       waterlevel_id     discharge_id
0  2025-01-01T00:00:00Z                22.5            0.80
1  2025-01-01T01:00:00Z                22.8            0.85
2  2025-01-01T02:00:00Z                23.0            0.90
```

### Loaders

**Loaders** take the transformed DataFrame and load it into the target system instance. For instance, the HydroServerLoader class extends the base HydroServer client to meet ETL-specific needs. It checks what data is needed, filters the DataFrame accordingly, and then writes the observations to the appropriate datastreams in HydroServer.

Example:

```python
from hydroserverpy.etl.loaders import HydroServerLoader

loader = HydroServerLoader(
    host="https://my-hydroserver.com",
    username="myuser",
    password="mypassword"
)

loader.load(transformed_dataframe)
```

### Running the ETL Process

The **HydroServerETL** class orchestrates the entire process: it obtains data requirements from the Loader, prepares Extractor parameters, retrieves raw data, transforms it, and finally loads it.

Example:

```python
from hydroserverpy.etl import HydroServerETL

source_target_map={"water_level": "waterlevel_id", "discharge": "discharge_id"}

etl = HydroServerETL(
    extractor=extractor,
    transformer=transformer,
    loader=loader,
    source_target_map=source_target_map
)

etl.run()
```
