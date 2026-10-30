# Migrating Apps and Scripts from v1 to v2

HydroServer v2 changes the Data Management API, the Python and TypeScript clients, and how apps sign users in. This
guide lists what changed for scripts, apps, dataloggers, and other tools that use HydroServer's APIs or client
libraries, and what you need to update. Each section links to the page that describes the v2 behavior in full.

If you only use HydroServer through the Data Management App in your browser, you don't need to change anything. Your
data is migrated when your HydroServer administrator upgrades the instance.

## What Keeps Working

- **API keys:** keys created in v1 keep working. Each one is now a [service account](/user-guides/how-to/managing-access-control.md#service-accounts-and-api-keys)
  with the same key and the same access to its workspace.
- **SensorThings API:** reading data and posting observations work as before, with the property changes listed in
  [SensorThings API](#sensorthings-api).
- **IDs:** workspaces, monitoring sites (Things in v1), datastreams, observations, methods (Sensors in v1), observed
  properties, units, processing levels, and result qualifiers keep their IDs. File attachments and controlled
  vocabulary terms get new IDs.

## What to Upgrade

| Tool | Upgrade to | Details |
| --- | --- | --- |
| hydroserverpy | 2.x: `pip install "hydroserverpy>=2.0,<3"` | [hydroserverpy](#hydroserverpy) |
| hydroserver-ts (`@hydroserver/client`) | 2.x: `npm install @hydroserver/client@^2` | [hydroserver-ts](#hydroserver-ts) |
| Streaming Data Loader | The latest release | [Streaming Data Loader](#streaming-data-loader) |

## Authentication

- **API keys:** send them in the `X-Api-Key` header, as before. Keys now belong to service accounts, which you manage
  under the workspace. See [Service Accounts and API Keys](/user-guides/how-to/managing-access-control.md#service-accounts-and-api-keys).
- **Email and password:** HTTP Basic authentication works as before. The v1 sign-in API at
  `/api/auth/{client}/session`, and the `Authorization: Bearer` session tokens it returned, are removed. Scripts that
  used them should send email and password with HTTP Basic, or preferably switch to a service account's API key.
- **Apps that sign users in:** the rest of the v1 account API under `/api/auth/`, including sign-up, password reset,
  email verification, and third-party provider connections, is also removed. Apps now sign users in with OpenID
  Connect (OIDC), send `Authorization: Bearer <access token>`, and send users to HydroServer's account pages to sign up
  or edit their account. Your HydroServer administrator must register each app as an OIDC client.

See [Authenticating](/references/hydroserver-apis.md#authenticating) and
[Using OIDC Scopes](/developing-and-contributing/how-to/using-oidc-scopes.md).

## Data Management API

The Data Management API moved from `/api/data` to `/api/ogc` and now implements OGC API - Features. Each type of
resource is a collection, with its items at `/api/ogc/collections/{collectionId}/items`. See
[Using the Data Management API](/user-guides/how-to/using-the-data-management-api.md) for how to use it.

### Paths

All v1 paths below are under `/api/data`, and all v2 paths are under `/api/ogc/collections`. Paths under an item, such
as a task's `runs` and `trigger` endpoints, follow the same pattern: `/etl/tasks/{id}/runs` becomes
`/etl-tasks/items/{id}/runs`.

| v1 path | v2 path |
| --- | --- |
| `/workspaces` | `/workspaces/items` |
| `/workspaces/{id}/collaborators`, `/workspaces/{id}/transfer` | `/workspaces/items/{id}/collaborators`, `/workspaces/items/{id}/transfer` |
| `/workspaces/{id}/api-keys` | `/workspaces/items/{id}/service-accounts` |
| `/roles` | `/roles/items` |
| `/things` | `/monitoring-sites/items` |
| `/datastreams` | `/datastreams/items` |
| `/things/{id}/tags`, `/datastreams/{id}/tags` | The item's `tags` field, changed with `PATCH` |
| `/things/{id}/file-attachments`, `/datastreams/{id}/file-attachments` | `/monitoring-sites/items/{id}/linked-resources`, `/datastreams/items/{id}/linked-resources` |
| `/datastreams/{id}/observations` | `/observations/items?datastreamId={id}` |
| `/datastreams/{id}/observations/bulk-create`, `.../bulk-delete` | `/observations/bulk-create`, `/observations/bulk-delete`, with `datastreamId` in the request body |
| `/sensors` | `/methods/items` |
| `/observed-properties`, `/units`, `/processing-levels`, `/result-qualifiers` | `/observed-properties/items`, `/units/items`, `/processing-levels/items`, `/result-qualifiers/items` |
| `/things/site-types`, `/sensors/method-types`, `/units/types`, `/observed-properties/variable-types` | `/monitoring-site-types/items`, `/method-types/items`, `/unit-types/items`, `/observed-property-types/items` |
| `/datastreams/statuses`, `/datastreams/sampled-mediums`, `/datastreams/aggregation-statistics` | `/datastream-statuses/items`, `/sampled-mediums/items`, `/aggregation-statistics/items` |
| `/things/file-attachment-types`, `/datastreams/file-attachment-types` | `/linked-resource-types/items` |
| `/things/sampling-feature-types`, `/sensors/encoding-types` | Removed |
| `/etl/data-connections`, `/etl/tasks` | `/etl-data-connections/items`, `/etl-tasks/items` |
| An ETL task's `mappings` | `/etl-mappings/items`, filtered by `etlTaskId` |
| `/products/rating-curves`, `/products/tasks` | `/data-product-rating-curves/items`, `/data-product-tasks/items` |
| `/products/tasks/{id}/transformations/{type}` | `/data-product-transformations/items`, with `taskId` and `transformationType` |
| `/monitoring/tasks` | `/monitoring-tasks/items` |
| `/monitoring/tasks/{id}/rules` | `/monitoring-rules/items`, with `taskId` |
| `/quality-control/histories` | `/quality-control-histories/items` |

Controlled vocabularies are now collections of items with a `name` and `description`, rather than lists of strings.

### Requests and Responses

- **Query parameters** use camelCase, such as `monitoringSiteId` instead of `thing_id`, and the API rejects parameters
  it doesn't recognize with `400`. See [Filtering](/user-guides/how-to/using-the-data-management-api.md#filtering).
- **Paging** uses `limit` and `offset` instead of `page` and `page_size`. Lists are returned in a `data` array with
  the total count in `meta.numberMatched` and page links in `links`, instead of a bare array with `X-Total-Count` and
  `X-Total-Pages` headers. See [Paging](/user-guides/how-to/using-the-data-management-api.md#paging).
- **Single items** are returned in `data`, instead of as the bare object.
- **Sorting** uses `sortby` instead of `order_by`. See [Sorting](/user-guides/how-to/using-the-data-management-api.md#sorting).
- **Related records:** use `include` instead of `expand_related`. Related records are returned once each in
  `included`, instead of nested in each item. See
  [Including Related Records](/user-guides/how-to/using-the-data-management-api.md#including-related-records).
- **Time filters:** use `datetime` instead of the `*_min` and `*_max` time parameters, such as
  `phenomenon_time_min` and `phenomenon_time_max` on observations. See
  [Filtering by Time](/user-guides/how-to/using-the-data-management-api.md#filtering-by-time).
- **Observation formats:** use the `profile` parameter with the row or column profile instead of `format=row` or
  `format=column`. See [Compact Observation Responses](/user-guides/how-to/using-the-data-management-api.md#compact-observation-responses).
- **Creating** an item returns `201` with only the new item's `id`, instead of the full item.
- **Updating** uses [JSON Merge Patch](https://www.rfc-editor.org/rfc/rfc7396). `null` clears an optional field, and
  objects such as `tags` are merged key by key. See [Updating](/user-guides/how-to/using-the-data-management-api.md#updating).
- **Errors** return their explanation in `message` instead of `detail`. See
  [Errors](/user-guides/how-to/using-the-data-management-api.md#errors).

### Fields

The main renamed and restructured fields are listed below. See the [Data Dictionary](/references/data-dictionary.md)
for every field in v2.

| Resource | v1 | v2 |
| --- | --- | --- |
| Monitoring sites (Things) | `samplingFeatureCode`, `siteType` | `code`, `type` |
| | `samplingFeatureType` | Removed |
| | `location` object | `latitude`, `longitude`, `elevationM`, `elevationDatum`, `adminArea1`, `adminArea2`, and `country` on the site |
| | `fileAttachments` | `linkedResources` |
| Monitoring sites and datastreams | `tags` as a list of `key` and `value` objects | `tags` as an object of keys and values |
| Datastreams, data product tasks, monitoring tasks, rating curves | `thingId` | `monitoringSiteId` |
| Datastreams | `sensorId`, `fileAttachments` | `methodId`, `linkedResources` |
| Methods (Sensors) | `methodCode`, `methodType`, `methodLink` | `code`, `type`, `definition` |
| | `manufacturer`, `model`, `modelLink` | `sensorModelManufacturer`, `sensorModel`, `sensorModelDefinition` |
| | `encodingType` | Removed |
| Processing levels | `code`, `definition`, `explanation` | `code`, `name`, `definition` (a URL), `description` |
| Result qualifiers | `code` | `name` |
| Observations | `resultQualifierCodes` | `resultQualifiers` |
| Workspaces | `owner`, `pendingTransferTo`, `collaboratorRole` | `ownerEmail`, `pendingTransferToEmail`, `collaboratorRoleId` |
| Service accounts (API keys) | `expiresAt`, `lastUsed` | `keyExpiresAt`, `lastUsedAt` |
| | `roleId` | Set when creating the account. Change it afterwards through the workspace's collaborators. |
| Data product transformations | `inputDatastream` | `inputDatastreams` |

## SensorThings API

The SensorThings API's paths and query options haven't changed, but its entities now come from v2's data model. See
[Retrieving Data with the SensorThings API](/user-guides/how-to/retrieving-data-with-sensorthings.md).

- **Things:** in each Thing's `properties`, `samplingFeatureCode` and `siteType` are now `code` and `type`,
  `samplingFeatureType` is removed, and `fileAttachments` is now `linkedResources`.
- **Locations:** each monitoring site's Location now has the same ID, name, and description as the site, so update
  anything that stored v1 Location IDs.
- **Sensors:** each Sensor is a method. Its `encodingType` is always `application/json`, and its `metadata` keeps the
  same keys as v1.
- **Datastreams:** in each Datastream's `properties`, `fileAttachments` is now `linkedResources`, and
  `processingLevelCode` can be `null`. An ObservedProperty's `variableCode` can also be `null`.

## hydroserverpy

Install hydroserverpy 2.x, which works with HydroServer v2. See the
[Python Client Reference](/user-guides/how-to/using-the-python-client.md) for every class and method.

- **Connecting:** create the client with `apikey`, `email` and `password`, or the new `access_token` option. The
  `auth_route` parameter and the `login()` and `logout()` methods are removed, and `base_route` now defaults to
  `/api/ogc`. See [Connection](/user-guides/how-to/using-the-python-client.md#connection).
- **Paging:** `list()` methods take `offset`, `limit`, and `sortby` instead of `page`, `page_size`, and `order_by`,
  and collections have matching attributes in place of `page`, `page_size`, and `total_pages`. See
  [Common list() parameters](/user-guides/how-to/using-the-python-client.md#common-list-parameters).
- **Renamed services and models:**

  | v1 | v2 |
  | --- | --- |
  | `hs.things`, `Thing` | `hs.monitoring_sites`, `MonitoringSite` |
  | `hs.sensors`, `Sensor` | `hs.methods`, `Method` |
  | API keys (`workspace.apikeys`, `create_api_key()`, ...) | Service accounts (`workspace.serviceaccounts`, `create_service_account()`, ...) |
  | The `mappings` argument of `hs.etltasks.create()` and `update()` | `hs.etlmappings`. `task.mappings` still lists a task's mappings. |
  | `thing`, `thing_id`, `sensor`, `sensor_id` arguments and attributes | `monitoring_site`, `monitoring_site_id`, `method`, `method_id` |

- **Renamed fields:** model attributes follow the API's [field changes](#fields), in snake_case. For example,
  `site_type` is now `type`, `observed_property_type` and `unit_type` are now `type`, and a result qualifier's `code`
  is now `name`.
- **Tags and files:** `add_tag()` and `update_tag()` are replaced by `set_tag()`, and `delete_tag()` takes only the
  key. File attachment methods are replaced by linked resource methods such as `add_linked_resource()`. See
  [Tags](/user-guides/how-to/using-the-python-client.md#tags) and
  [Linked resources](/user-guides/how-to/using-the-python-client.md#linked-resources).
- **Transformations and rules:** data product transformation and monitoring rule methods no longer take a `task_id`
  when you get, update, or delete one by its ID. See
  [Data Product Transformations](/user-guides/how-to/using-the-python-client.md#data-product-transformations) and
  [Monitoring Rules](/user-guides/how-to/using-the-python-client.md#monitoring-rules).
- **Observations:** `get_observations()` takes `result_qualifiers` instead of `result_qualifier_code`, and
  `load_observations()` adds `phenomenon_time_start` and `phenomenon_time_end` for `replace` mode.

## hydroserver-ts

Install `@hydroserver/client` 2.x, which works with HydroServer v2. See
[Using the TypeScript Client](/developing-and-contributing/how-to/using-the-typescript-client.md) for every service.

- **Signing in:** `hs.session.login(email, password)` is replaced by `hs.session.login(returnTo)`, which opens
  HydroServer's sign-in page. Use the `oidc` option to sign users in with OIDC, or `accessTokenProvider` if your app
  already has access tokens. Account features that used the v1 account API, such as password reset and email
  verification, now happen on HydroServer's account pages. See
  [Authentication and session](/developing-and-contributing/how-to/using-the-typescript-client.md#authentication-and-session).
- **Renamed services:** `hs.things` is now `hs.monitoringSites`, `hs.sensors` is now `hs.methods`, and
  `hs.thingFileAttachments` is replaced by linked resource methods on `hs.monitoringSites` and `hs.datastreams`.
  New services cover ETL mappings, monitoring rules, data product transformations, and each controlled vocabulary.
- **Query parameters:** `list()` takes `offset`, `limit`, and `sortby` instead of `page`, `page_size`, and `order_by`,
  and filters use camelCase, such as `isAssociated` instead of `is_associated`. See
  [Collections and CRUD helpers](/developing-and-contributing/how-to/using-the-typescript-client.md#collections-and-crud-helpers).
- **Models:** model fields follow the API's [field changes](#fields).

## Streaming Data Loader

Update the Streaming Data Loader to its latest release, which works with HydroServer v2. See
[Using the Streaming Data Loader](/user-guides/how-to/using-streaming-data-loader.md).
