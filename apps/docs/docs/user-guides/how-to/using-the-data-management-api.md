# Using the Data Management API

The HydroServer Data Management API is HydroServer's primary API for creating, managing, and retrieving data and metadata. It implements [OGC API - Features](https://ogcapi.ogc.org/features/), so each type of resource (monitoring sites, datastreams, observations, units, tasks, and so on) is an OGC API collection of items. Every HydroServer instance serves it at `/api/ogc`, with interactive documentation of every endpoint at `/api/ogc/docs`.

This guide covers the patterns the API shares across its collections: finding collections, reading items, filtering and paging, choosing a response format, and creating, updating, and deleting records. For an overview of HydroServer's APIs and the full list of authentication methods, see [HydroServer APIs](/references/hydroserver-apis.md). If you work in Python, the [Python client](/user-guides/how-to/using-the-python-client.md) wraps this API for you.

The examples use `curl` against the HydroServer playground. Set these variables first, replacing the API key with your own:

```sh
HS=https://playground.hydroserver.org/api/ogc
API_KEY=your-api-key
```

## Exploring the API

The API is self-describing. Its landing page links to the API definition, the documentation, the conformance declaration, and the list of collections:

```sh
curl "$HS/"
curl "$HS/conformance"
curl "$HS/collections"
```

Each collection is described at `/collections/{collectionId}`, and its items are at `/collections/{collectionId}/items`. For example:

```sh
curl "$HS/collections/monitoring-sites"
curl "$HS/collections/monitoring-sites/items"
```

These are the collections you'll use most often:

| Collection | Contains |
| --- | --- |
| `workspaces` | Workspaces, which own all other data and control access to it |
| `monitoring-sites` | Monitoring sites and their locations |
| `datastreams` | Time series of observations of one observed property at a site |
| `observations` | Individual timestamped results in datastreams |
| `methods`, `observed-properties`, `processing-levels`, `units`, `result-qualifiers` | Datastream metadata |
| `etl-data-connections`, `etl-tasks`, `etl-mappings` | Data ingestion with the [Job Orchestration System](/user-guides/how-to/using-job-orchestration.md) |
| `data-product-tasks`, `data-product-transformations`, `data-product-rating-curves` | Derived data products |
| `monitoring-tasks`, `monitoring-rules` | Data quality monitoring |

The `/collections` response lists all of them, including the controlled vocabularies such as `monitoring-site-types` and `unit-types`.

## Authenticating

You can read public data without authenticating. To read private data, or to create, change, or delete anything, authenticate each request. For scripts, use a [service account](/user-guides/how-to/managing-access-control.md#service-accounts-and-api-keys) API key in the `X-Api-Key` header:

```sh
curl -H "X-Api-Key: $API_KEY" "$HS/collections/datastreams/items"
```

The API also accepts OIDC access tokens, HTTP Basic authentication with your email and password, and browser sessions. See [Authenticating](/references/hydroserver-apis.md#authenticating) for when to use each. Whichever you use, your workspace roles decide which records you can see and change.

## Reading Items

A request for a collection's items returns a page of items in `data`, with paging details in `meta` and links in `links`:

```sh
curl "$HS/collections/monitoring-sites/items?limit=2&properties=id,name"
```

```json
{
  "data": [
    {
      "id": "01a18907-0ef8-7034-99aa-a01d5fd35a5f",
      "name": "Logan River at the Utah Water Research Laboratory"
    },
    {
      "id": "01a18907-0f06-72ae-8d9e-9e577879a9c1",
      "name": "Logan River at the Utah Water Research Laboratory west bridge"
    }
  ],
  "meta": {
    "limit": 2,
    "offset": 0,
    "numberMatched": 9,
    "numberReturned": 2
  },
  "links": [
    {
      "href": "https://playground.hydroserver.org/api/ogc/collections/monitoring-sites/items?limit=2&properties=id,name",
      "rel": "self",
      "type": "application/json"
    },
    {
      "href": "https://playground.hydroserver.org/api/ogc/collections/monitoring-sites/items?limit=2&properties=id%2Cname&f=geojson",
      "rel": "alternate",
      "type": "application/geo+json"
    },
    {
      "href": "https://playground.hydroserver.org/api/ogc/collections/monitoring-sites/items?limit=2&properties=id%2Cname&offset=2",
      "rel": "next",
      "type": "application/json"
    }
  ]
}
```

To get one item, add its ID to the path. A single item comes back as an object in `data`:

```sh
curl "$HS/collections/monitoring-sites/items/01a18907-0f06-72ae-8d9e-9e577879a9c1"
```

### Paging

Use **limit** to set the page size and **offset** to skip items. The default page size is 100 and the maximum is 100,000. `meta.numberMatched` is the total number of matching items, and the `next` and `prev` links give the URLs of the neighboring pages, so you can follow `next` until it's no longer returned. To count matching items without fetching them, set `limit=0`:

```sh
curl "$HS/collections/datastreams/items?limit=0"
```

### Selecting Properties

Use **properties** to return only the fields you need, as a comma-separated list. Items include only the listed properties, so list `id` too if you need it:

```sh
curl "$HS/collections/datastreams/items?properties=id,name,valueCount"
```

### Including Related Records

Use **include** to return related records in the same response. They're returned once each, grouped by type, in an `included` member alongside `data`, and items keep referring to them by ID. For example, this returns datastreams with their monitoring sites and units:

```sh
curl "$HS/collections/datastreams/items?properties=id,name,monitoringSiteId,unitId&include=monitoringSite,unit"
```

```json
{
  "included": {
    "monitoringSites": [
      { "id": "01a18907-0f06-72ae-8d9e-9e577879a9c1", "name": "Logan River at the Utah Water Research Laboratory west bridge", "...": "..." }
    ],
    "units": [
      { "id": "01a18907-0f0c-707a-b15a-4b84b1b0959d", "name": "milligrams per liter", "symbol": "mg/L", "...": "..." }
    ]
  },
  "data": [
    {
      "id": "01a18907-0f22-7229-928d-237d3ae39587",
      "monitoringSiteId": "01a18907-0f06-72ae-8d9e-9e577879a9c1",
      "unitId": "01a18907-0f0c-707a-b15a-4b84b1b0959d",
      "name": "Oxygen, dissolved (mg/L) - Raw data"
    }
  ],
  "meta": { "...": "..." },
  "links": [ "..." ]
}
```

Each collection's interactive documentation lists the relations it can include.

## Filtering

Each collection has its own filter parameters, named after the fields they filter on. For example, this returns the datastreams at one monitoring site:

```sh
curl "$HS/collections/datastreams/items?monitoringSiteId=01a18907-0f06-72ae-8d9e-9e577879a9c1"
```

- **Several values:** repeat a parameter to match any of its values, such as `?monitoringSiteId={id1}&monitoringSiteId={id2}`.
- **Empty values:** where a field can be empty, the value `null` matches items without one, such as `?status=null`.
- **Tags:** use **tag** with `{key}:{value}` to filter monitoring sites or datastreams by tag. Repeat it to require several tags.
- **Text search:** use **q** to search names, descriptions, and other text fields. Words separated by spaces must all match, and comma-separated terms match any of them. For example, `?q=oxygen%20raw` matches items containing both words, and `?q=oxygen,temperature` matches items containing either.

The API rejects parameters it doesn't recognize instead of ignoring them, so a misspelled filter returns an error rather than unfiltered results:

```sh
curl "$HS/collections/datastreams/items?monitoring_site_id=01a18907-0f06-72ae-8d9e-9e577879a9c1"
```

```json
{"message": "Unknown query parameter(s): monitoring_site_id. Allowed: bbox, datetime, f, include, isPrivate, limit, methodId, monitoringSiteId, ..."}
```

### Filtering by Location

Collections with locations (workspaces, monitoring sites, datastreams, and observations) accept a **bbox** in WGS 84 longitude and latitude, as `min_lon,min_lat,max_lon,max_lat`:

```sh
curl "$HS/collections/monitoring-sites/items?bbox=-112.0,41.6,-111.7,41.8"
```

### Filtering by Time

The same collections accept a **datetime** in RFC 3339 format with a UTC offset. It can be an instant (`2025-01-01T00:00:00Z`), an interval (`2025-01-01T00:00:00Z/2025-02-01T00:00:00Z`), or an interval open at one end with `..` (`2025-01-01T00:00:00Z/..`). Interval ends are inclusive. What it matches depends on the collection:

- **Observations** match on their `phenomenonTime`.
- **Datastreams** match when the period from their first to last observation overlaps the interval.
- **Monitoring sites and workspaces** match when they have a datastream you can see that matches.

```sh
curl "$HS/collections/observations/items?datastreamId=01a18907-0f22-7229-928d-237d3ae39587&datetime=2025-01-01T00:00:00Z/2025-02-01T00:00:00Z"
```

## Sorting

Use **sortby** with a comma-separated list of fields. Prefix a field with `-` to sort it in descending order. Fields are applied in the order you list them. For example, this returns a site's datastreams in reverse order by name:

```sh
curl "$HS/collections/datastreams/items?monitoringSiteId=01a18907-0f06-72ae-8d9e-9e577879a9c1&sortby=-name"
```

Observations are sorted by `datastreamId` and then `phenomenonTime` unless you choose otherwise, so `sortby=-phenomenonTime` returns the newest observations first.

## Choosing a Response Format

Responses are JSON by default. Workspaces, monitoring sites, datastreams, and observations can also be returned as GeoJSON, with each item as a feature at its site's location. Choose the format with the **f** parameter or the `Accept` header. If you send both, `f` wins.

```sh
curl "$HS/collections/monitoring-sites/items?f=geojson"
curl -H "Accept: application/geo+json" "$HS/collections/monitoring-sites/items"
```

Each response's `alternate` links give the same request in the collection's other formats.

## Compact Observation Responses

By default, each observation is returned as a full item. For time series, you can ask for a more compact representation with the **profile** parameter. Both profiles group a page of observations by datastream:

| Profile | Returns |
| --- | --- |
| `https://hydroserver.org/profiles/observations/row` | A `fields` list and a `rows` array of values in that order, like a table |
| `https://hydroserver.org/profiles/observations/column` | A `columns` object with one array per field |

Combine a profile with **properties** to choose the fields. For example, this returns one hour of a datastream's observations as columns:

```sh
curl "$HS/collections/observations/items?datastreamId=01a18907-0f22-7229-928d-237d3ae39587&datetime=2025-01-01T00:00:00Z/2025-01-01T01:00:00Z&properties=phenomenonTime,result&profile=https://hydroserver.org/profiles/observations/column"
```

```json
{
  "data": [
    {
      "datastreamId": "01a18907-0f22-7229-928d-237d3ae39587",
      "columns": {
        "phenomenonTime": [
          "2025-01-01T00:00:00+00:00",
          "2025-01-01T00:15:00+00:00",
          "2025-01-01T00:30:00+00:00",
          "2025-01-01T00:45:00+00:00",
          "2025-01-01T01:00:00+00:00"
        ],
        "result": [11.57, 11.55, 11.55, 11.54, 11.54]
      }
    }
  ],
  "meta": { "limit": 100, "offset": 0, "numberMatched": 5, "numberReturned": 5 },
  "links": [ "..." ]
}
```

With the row profile, the same request returns `"fields": ["phenomenonTime", "result"]` and `"rows": [["2025-01-01T00:00:00+00:00", 11.57], ...]`. Paging works the same way in both profiles, counting observations rather than datastreams.

## Creating, Updating, and Deleting

You need a role in the workspace that permits the change. See [Managing Access Control](/user-guides/how-to/managing-access-control.md).

### Creating

`POST` a JSON body to a collection's items. A successful request returns `201 Created` with the new item's ID:

```sh
curl -X POST "$HS/collections/units/items" \
  -H "X-Api-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workspaceId": "01a18907-2a05-73ca-882d-65af6f2f9e05",
    "name": "cubic feet per second",
    "symbol": "cfs",
    "type": "Hydrology"
  }'
```

```json
{"id": "01a18d8a-da11-714e-8130-f04d2f19a268"}
```

### Updating

`PATCH` an item with only the fields you want to change, as a [JSON Merge Patch](https://www.rfc-editor.org/rfc/rfc7396). Send it as `application/merge-patch+json`. A successful request returns `204 No Content`.

```sh
curl -X PATCH "$HS/collections/units/items/01a18d8a-da11-714e-8130-f04d2f19a268" \
  -H "X-Api-Key: $API_KEY" \
  -H "Content-Type: application/merge-patch+json" \
  -d '{"symbol": "ft³/s", "definition": null}'
```

- **Omitted fields** are left as they are.
- **`null`** clears an optional field. Required fields can't be cleared.
- **Objects** such as `tags` and an ETL task's `taskVariables` are merged key by key, so `{"tags": {"station": "A"}}` adds or changes one tag and leaves the others, and `{"tags": {"station": null}}` removes it.
- **Arrays** are replaced in full.

### Deleting

`DELETE` an item. A successful request returns `204 No Content`.

```sh
curl -X DELETE "$HS/collections/units/items/01a18d8a-da11-714e-8130-f04d2f19a268" \
  -H "X-Api-Key: $API_KEY"
```

### Sub-resources

Some records belong to an item and are managed under its path rather than as their own collection:

| Path | Manages |
| --- | --- |
| `/collections/workspaces/items/{workspaceId}/collaborators` | The workspace's collaborators and their roles |
| `/collections/workspaces/items/{workspaceId}/service-accounts` | The workspace's service accounts and their API keys |
| `/collections/monitoring-sites/items/{siteId}/linked-resources` | Files and links attached to a monitoring site |
| `/collections/datastreams/items/{datastreamId}/linked-resources` | Files and links attached to a datastream |

Linked resources are created with a `multipart/form-data` body, so you can upload a file or give a link:

```sh
curl -X POST "$HS/collections/monitoring-sites/items/01a18907-2a07-7190-8331-1140a4be92c1/linked-resources" \
  -H "X-Api-Key: $API_KEY" \
  -F name="Site photo, May 2026" \
  -F type="Photo" \
  -F file=@site-photo.jpg
```

## Loading Observations in Bulk

To load many observations at once, `POST` them to `/collections/observations/bulk-create`, either as rows with a `fields` list or as one array per field:

```sh
curl -X POST "$HS/collections/observations/bulk-create" \
  -H "X-Api-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "datastreamId": "01a18907-2a0b-732f-8d6f-3fa205936324",
    "fields": ["phenomenonTime", "result"],
    "data": [
      ["2026-06-01T00:00:00Z", 12.4],
      ["2026-06-01T00:15:00Z", 12.6]
    ]
  }'
```

```sh
curl -X POST "$HS/collections/observations/bulk-create" \
  -H "X-Api-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "datastreamId": "01a18907-2a0b-732f-8d6f-3fa205936324",
    "phenomenonTime": ["2026-06-01T00:30:00Z", "2026-06-01T00:45:00Z"],
    "result": [12.7, 12.5]
  }'
```

The **mode** query parameter controls where new observations may go:

| Mode | Behavior |
| --- | --- |
| `append` (default) | Observations must be later than the datastream's latest observation. |
| `backfill` | Observations must be earlier than the datastream's earliest observation. |
| `insert` | Observations can be at any time. A timestamp that already exists returns `409 Conflict`. |
| `replace` | Deletes the existing observations in the range of the new ones, then inserts the new ones. Add `phenomenonTimeStart` and `phenomenonTimeEnd` to replace a different range. |

```sh
curl -X POST "$HS/collections/observations/bulk-create?mode=insert" ...
```

To delete a range of a datastream's observations, `POST` to `/collections/observations/bulk-delete`. Leave out both times to delete all of them.

```sh
curl -X POST "$HS/collections/observations/bulk-delete" \
  -H "X-Api-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "datastreamId": "01a18907-2a0b-732f-8d6f-3fa205936324",
    "phenomenonTimeStart": "2026-06-01T00:00:00Z",
    "phenomenonTimeEnd": "2026-06-01T01:00:00Z"
  }'
```

The built-in Data Loader role can load observations but not delete them, so a service account with that role gets `403 Forbidden` from `bulk-delete`.

## Running Tasks

To run an ETL, data product, or monitoring task now instead of waiting for its schedule, `POST` to its `trigger` endpoint. The API returns `202 Accepted` with the new task run, which the Job Orchestration System then carries out in the background:

```sh
curl -X POST "$HS/collections/etl-tasks/items/{taskId}/trigger" \
  -H "X-Api-Key: $API_KEY"
```

The same endpoint exists under `data-product-tasks` and `monitoring-tasks`. If the instance's Job Orchestration System is turned off, the request returns `501 Not Implemented`.

## Errors

Errors return an HTTP status and, for most errors, a JSON body with a `message` explaining the problem:

```json
{"message": "MonitoringSite does not exist"}
```

| Status | Common causes |
| --- | --- |
| `400 Bad Request` | An unknown or invalid query parameter, or an invalid request body |
| `401 Unauthorized` | Missing or invalid credentials on a create, update, or delete request. The body is `{"detail": "Unauthorized"}`. |
| `403 Forbidden` | Your role doesn't permit the change |
| `404 Not Found` | The item doesn't exist, or you can't see it |
| `406 Not Acceptable` | The `Accept` header asks for a format the collection doesn't offer |
| `409 Conflict` | The change conflicts with existing data, such as a duplicate observation timestamp |
| `501 Not Implemented` | A task was triggered or created while the Job Orchestration System is turned off |
