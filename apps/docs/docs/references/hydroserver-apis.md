# HydroServer APIs

HydroServer provides two web APIs: the HydroServer Data Management API and the SensorThings API. Both are served by your HydroServer instance under `/api/`.

## Data Management API

The interactive documentation for this API is available at:

https://playground.hydroserver.org/api/ogc/docs

### About

The HydroServer Data Management API is HydroServer's primary API for creating, managing, and retrieving data and metadata. It is an OGC-compliant API that currently implements [OGC API - Features](https://ogcapi.ogc.org/features/). Its landing page is at `/api/ogc/`, its conformance declaration is at `/api/ogc/conformance`, and each type of resource is a collection listed at `/api/ogc/collections`. Items in a collection are available at `/api/ogc/collections/{collectionId}/items`.

The API covers everything you can manage in HydroServer: workspaces, roles, collaborators, and service accounts; monitoring sites, datastreams, and observations; metadata such as methods, units, processing levels, observed properties, result qualifiers, and controlled vocabularies; tags and linked resources; and Job Orchestration System tasks for data ingestion, data products, and quality monitoring. It returns your own data along with data that others have shared with you or made public.

## SensorThings API

The interactive documentation for this API is available at:

https://playground.hydroserver.org/api/sensorthings/v1.1/docs

### About

HydroServer implements the [OGC SensorThings API](https://www.ogc.org/standard/sensorthings/) standard, an open specification for connecting Internet of Things (IoT) sensors and their observations to the web. It provides a standardized REST interface for working with Things, Locations, Datastreams, Sensors, Observed Properties, and Observations — enabling interoperability with SensorThings-compliant clients and tools.

HydroServer derives these standard entities from its own data model: each monitoring site is exposed as a Thing and its Location, and each method is exposed as a Sensor. See [Monitoring Sites](/introduction/key-concepts/monitoring-sites.md) for details.

## Authenticating

Public data can be read from both APIs without authenticating. To read private data or to create, change, or delete anything, authenticate each request with one of the following methods. Both APIs accept all of them.

| Method | How to send it | When to use it |
| --- | --- | --- |
| API key | `X-Api-Key: <key>` header | Scripts, dataloggers, and other automated clients. Create a [service account](/user-guides/how-to/managing-access-control.md#service-accounts-and-api-keys) for the workspace, assign it the minimum role it needs, and use its API key. |
| OIDC access token | `Authorization: Bearer <access token>` header | Third-party apps acting on a user's behalf. The token's scopes decide which endpoints it can call. See [Using OIDC Scopes](/developing-and-contributing/how-to/using-oidc-scopes.md). |
| Email and password | HTTP Basic authentication | Quick personal scripts. Prefer an API key for anything long-running or shared, because a password grants all of your permissions. |
| Browser session | Session cookie, with a CSRF token on write requests | HydroServer's own web apps and apps served from the same origin. |

Whichever method you use, your workspace roles decide which records you can see and change.

### OIDC Identity Provider

HydroServer includes a built-in OpenID Connect identity provider that issues the access tokens described above. Its discovery document is at `/.well-known/openid-configuration`. An administrator must register each app as an OIDC client before it can request tokens. See [Registering OIDC Clients](/hosting-and-deployment/how-to/using-the-administrator-dashboard#registering-oidc-clients).

User accounts are managed through HydroServer's account pages under `/accounts/` (sign up, sign in, profile, and password management) rather than through an API.
