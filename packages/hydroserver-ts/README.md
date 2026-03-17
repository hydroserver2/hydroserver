# HydroServer TypeScript Client

This package is published from the HydroServer monorepo.

`npm run gen` exports the current backend OpenAPI schemas from `django`,
regenerates the TypeScript types, and rebuilds the generated contract files.

`npm run check:contract` is the CI guard that fails when the committed client
artifacts drift from the latest backend API contract.
