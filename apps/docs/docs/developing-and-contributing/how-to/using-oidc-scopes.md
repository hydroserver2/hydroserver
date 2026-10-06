# Using OIDC Scopes

Third-party apps can call the HydroServer Data Management API and SensorThings API on a user's behalf with an OIDC
access token. The scopes an app requests decide which endpoints that token can reach. Request only the scopes your app
needs: each one appears on the consent screen the user approves.

An administrator must register your app as an OIDC client and allow each scope it requests. See
[Registering OIDC Clients](/hosting-and-deployment/how-to/using-the-administrator-dashboard#registering-oidc-clients).
Scopes a client isn't allowed are silently dropped from its tokens.

## Scopes

| Scope | Grants | Consent screen |
| --- | --- | --- |
| `data:read` | `GET` on monitoring sites, datastreams, observations, metadata vocabularies (methods, units, processing levels, observed properties, result qualifiers, and system types), quality control histories, and the SensorThings API | View your monitoring sites, datastreams, observations, and quality control history |
| `data:write` | `POST`, `PATCH`, `PUT`, and `DELETE` on the same resources | Create, change, and delete your monitoring sites, datastreams, observations, and quality control edits |
| `workspace:read` | `GET /api/ogc/collections/workspaces/items` and `GET /api/ogc/collections/workspaces/items/{workspace_id}`, including owner and pending transfer details | See your workspaces, including owner and pending transfer details |
| `workspace:write` | Create, update, and delete workspaces, including changing whether a workspace is private | Create, rename, and delete workspaces, and change their privacy, including making a workspace public |
| `iam:read` | `GET` on collaborators, service accounts, and roles | See who can access your workspaces: collaborators, roles, and service accounts |
| `iam:write` | Add, edit, and remove collaborators; create, update, delete, and regenerate keys for service accounts; transfer workspace ownership and accept or reject transfers | Manage access to your workspaces: collaborators, service accounts, and ownership transfers (shown with a warning) |
| `task:read` | `GET` on ETL tasks, data connections, ETL mappings, monitoring tasks and rules, data product tasks, transformations, rating curves, task runs, and monitoring site task summaries | View your data loading, monitoring, and data product tasks, their settings, and run history |
| `task:write` | `POST`, `PATCH`, and `DELETE` on the same task resources | Create, change, and delete tasks and data connections (shown with a note) |
| `task:run` | `POST /api/ogc/collections/{collection}/items/{task_id}/trigger`, where `{collection}` is `etl-tasks`, `monitoring-tasks`, or `data-product-tasks` | Run your tasks on demand |

Scopes don't imply each other. A token with `data:write` can't read, and a token with `task:run` can't read the runs
it starts, so request each scope your app uses. Scopes only decide which endpoints a token can call. The user's
workspace roles still decide which records it can see and change.

## Warnings on the consent screen

`iam:write` is shown with a warning. A token with this scope can create service accounts and add collaborators, and
both keep working after the user revokes your app: a service account's API key doesn't expire with the token that
created it. HydroServer allows this so that apps can automate access management, and tells the user before they
approve. Workspace users whose role lets them manage service accounts and collaborators can review and delete them
from the workspace's access control settings in the Data Management app.

`task:write` is shown with a note that tasks can write observations to the user's datastreams and send email.

Request these scopes only if your app manages access or tasks.

## Missing scopes

A request with a valid token that lacks the endpoint's scope gets a `403` response:

```json
{ "detail": "Access token is missing the required scope: workspace:read" }
```

This applies even to resources that anonymous users can read, such as public workspaces. A token is never treated as
anonymous, so an app that sends a token must hold the scope for every endpoint it calls.

The API's landing page (`/api/ogc/`), conformance declaration (`/api/ogc/conformance`), and collection metadata
(`/api/ogc/collections` and `/api/ogc/collections/{collection_id}`) need no scope. They return the same response to
every caller, with or without a token.

## Included resources

The `include` query parameter isn't checked against scopes. A request can include related records from another
scope's resources, for example `include=targetDatastream` on ETL mappings with only `task:read`, or `include=owner` on
workspaces with only `workspace:read`. Included records are still limited to ones the user can view.
