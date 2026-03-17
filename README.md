# HydroServer

This repository contains the core HydroServer apps, services, deployment assets, and shared packages.

- Access the [HydroServer issue tracker](https://github.com/hydroserver2/hydroserver/issues)
- Access [HydroServer documentation](https://hydroserver2.github.io/hydroserver/)

HydroServer is a software cyberinfrastructure platform created to support collection, management, and sharing of time series of observations from hydrologic and evironmental monitoring sites. Under development at the [Utah Water Research Laboratory](https://uwrl.usu.edu/) at [Utah State University](https://www.usu.edu/), HydroServer is designed to be an open platform that enables research groups, agencies, organizations, and practitioners to more easily collect and manage streaming observations from environmental sensors.

HydroServer is organized as follows:

**Apps** (`apps/`)

- `apps/docs`: the VitePress documentation site for HydroServer.
- `apps/data-management`: the end-user web application for creating and managing monitoring sites, datastreams, metadata, and orchestration settings.

**Backend**

- `django`: the Django backend that owns the HydroServer API contract and runtime behavior, including SensorThings, data management, and orchestration.

**Packages** (`packages/`)

- `packages/hydroserver-ts`: the shared TypeScript client used by browser-based HydroServer applications.
- `packages/hydroserverpy`: the shared Python client used by HydroServer Python integrations and tooling.
- `packages/etl-core`: the reserved package boundary for the ETL framework that will be extracted from `hydroserverpy` in a later migration step.

**Specifications** (`specs/`)

- `specs/functional`: Markdown copies of HydroServer functional specification documents kept in the repo for planning, implementation, and review.

**Deployment** (`deploy/`)

- `deploy/dev`: local development deployment assets.
- `deploy/prod`: production deployment assets.

**System Tests** (`tests/`)

- `tests/e2e`: end-to-end tests for the HydroServer product as a whole.
  The Playwright suite boots the API and data-management app automatically against an isolated `hydroserver_e2e` database, and `tests/e2e/release-matrix.yaml` maps the standard release checklist into Playwright, pytest, and manual/external coverage buckets.

**Scripts** (`scripts/`)

- `scripts/e2e`: canonical local and CI entrypoint for the browser E2E suite.
- `scripts/release-test`: root runner for API, Python-client, and browser release regression suites.

## History

HydroServer builds on prior efforts and systems established by Utah State University and the Consortium of Universities for the Advancement of Hydrologic Science, Inc. (CUAHSI) [Hydrologic Information System (HIS) project](http://his.cuahsi.org), including the original HydroServer software stack that was created by that project (lovingly referred to a HydroServer 1). The legacy HydroServer (HydroServer 1) software is [archived by CUAHSI](https://github.com/CUAHSI/HydroServer). To acknowledge this legacy, the GitHub organization for this work was called HydroServer 2.

## Cite HydroServer

The following are the recommended citations for HydroServer:

Horsburgh, J. S., Lippold, K., Slaugh, D. L., Ramirez, M. (2024). HydroServer: A software stack supporting collection, communication, storage, management, and sharing of data from in situ environmental sensors, Environmental Modelling & Software, 106637, [https://doi.org/10.1016/j.envsoft.2025.106637](https://doi.org/10.1016/j.envsoft.2025.106637).

Horsburgh, J. S., Lippold, K., Slaugh, D. L. (2025). Adapting OGC’s SensorThings API and data model to support data management and sharing for environmental sensors, Environmental Modelling & Software, 183, 106241, [https://doi.org/10.1016/j.envsoft.2024.106241](https://doi.org/10.1016/j.envsoft.2024.106241).

## Funding and Acknowledgements

Funding for this project was provided by the National Oceanic & Atmospheric Administration (NOAA), awarded to the Cooperative Institute for Research to Operations in Hydrology (CIROH) through the NOAA Cooperative Agreement with The University of Alabama (NA22NWS4320003). Utah State University is a founding member of CIROH and receives funding under subaward from the University of Alabama. Additional funding and support have been provided by the State of Utah Division of Water Rights, the World Meteorological Organization, and the Utah Water Research laboratory at Utah State University.
