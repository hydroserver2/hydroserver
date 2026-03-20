# etl-core

`etl-core` is the reserved package boundary for HydroServer's reusable ETL framework.

Per the monorepo architecture proposal, generic ETL code should move here from `packages/hydroserverpy` so that the API service and external runtimes can depend on ETL code without depending on the Python client package.
