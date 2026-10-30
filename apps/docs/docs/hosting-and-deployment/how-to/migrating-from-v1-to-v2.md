# Migrating from HydroServer v1 to v2

HydroServer v2 restructures much of the v1 data model. Upgrading runs a set of database migrations that convert your
v1 data to the v2 schema. This guide covers what you need to do to your data **before** upgrading, what the
migrations will change, drop, or transform along the way, and the configuration and infrastructure changes your
deployment needs.

Users don't need to do anything to their own data. If your users have scripts, apps, or other tools that use
HydroServer's APIs or client libraries, point them to
[Migrating Apps and Scripts from v1 to v2](/user-guides/how-to/migrating-apps-and-scripts-from-v1-to-v2.md).

These migrations apply to deployments running **HydroServer v1.12**. If you are on an earlier v1 release, upgrade to
v1.12 first.

::: danger Back up your database first
The v2 migrations are one-way. They cannot be reversed, and some v1 data is dropped or rewritten. Take a full backup of
your database (and your media storage if you host file attachments) before upgrading. Restoring that backup is the
only way to roll back to v1.
:::

## Before You Upgrade

1. Back up your database and media storage.
2. While still running v1, work through [Blocking Changes](#blocking-changes) and fix any data that doesn't meet the
   new requirements. The fixes described below use the v1 Django admin dashboard
   (`https://<your-hydroserver-domain>/admin`), which you can still access before you upgrade.
3. Review [Data Loss and Transformations](#data-loss-and-transformations) and save copies of anything listed there
   that you need to keep.
4. Update your environment variables as described in [Configuration Changes](#configuration-changes). In particular,
   set `DEBUG`, generate an OIDC signing key, and replace v1's storage settings.
5. Make the infrastructure changes in [Infrastructure Changes](#infrastructure-changes).
6. Deploy the v2 image for your web server, Celery worker, and Celery scheduler, then run the migrations and collect
   static files:

   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

The first v2 migration checks your v1 data for every blocking problem listed below before it changes anything. If it
finds problems, the upgrade stops with an error that lists each problem, the affected table and field, and up to ten
example record IDs, for example:

```
RuntimeError: The HydroServer v2 migrations cannot run until the following v1 data problems are fixed.
None of the HydroServer v2 migrations have been applied.
  - sta_location: every Thing must have a Location. Things without one: '0190a1b2-...'
  - sta_observedproperty.code: values must be at most 255 characters. Rows over the limit: '0190a1b3-...'
```

When this happens, your HydroServer data has not been modified. Switch back to your v1 deployment, fix the listed
problems, and run the upgrade again.

## Blocking Changes

The migrations will not run until all the following are fixed.

### Every Thing must have a Location

**Table:** `sta_location` (`thing` field)

In v2, sites store their coordinates directly, so a site's location is required. Every Thing must have at least one
Location before upgrading.

**To fix:** In the admin dashboard, go to **Measurement Data** > **Locations** and add a Location for each Thing listed
in the error. Alternatively, delete Things that are no longer needed from **Measurement Data** > **Things**.

### Observed property codes and types are limited to 255 characters

**Table:** `sta_observedproperty` (`code` and `observed_property_type` fields)

Both fields were previously limited to 500 characters.

**To fix:** In the admin dashboard, go to **Measurement Data** > **Observed properties** and shorten the **Code** and
**Observed property type** of each listed observed property to 255 characters or fewer.

### Definitions are limited to 2,000 characters

**Tables:** `sta_observedproperty` (`definition` field), `sta_unit` (`definition` field), and `sta_processinglevel`
(`definition` field)

Definitions were unlimited text fields in v1. In v2 they are URL fields limited to 2,000 characters.

For processing levels, this only applies when the definition is a URL. Non-URL processing level definitions are moved
to other fields instead (see [Processing levels are restructured](#processing-levels-are-restructured)).

**To fix:** In the admin dashboard, go to **Measurement Data** > **Observed properties**, **Units**, or
**Processing levels** and shorten each listed definition to 2,000 characters or fewer.

### File attachments must reference a file

**Tables:** `sta_thingfileattachment` and `sta_datastreamfileattachment` (`file_attachment` field)

In v2, each linked resource must have either a file or a URL. A v1 file attachment with an empty file path can't be
migrated. HydroServer doesn't create these records, so you should only see this error if attachments were created or
edited outside HydroServer.

**To fix:** In the admin dashboard, go to **Measurement Data** > **Thing file attachments** or
**Datastream file attachments** and upload a file to, or delete, each listed attachment.

### Role names must be unique

**Table:** `iam_role` (`name` field)

Global roles (roles without a workspace) must have unique names, and roles within the same workspace must have unique
names.

**To fix:** In the admin dashboard, go to **Identity and Access Management** > **Roles** and rename or delete the
duplicate roles listed in the error.

### API keys must use HydroServer's key format

**Table:** `iam_apikey` (`hashed_key` field)

In v2, API keys become service accounts and are identified by the 12-character prefix of their key. API keys created by
HydroServer always use this format. An API key with a different format can only come from data loaded outside
 HydroServer and can't be used to authenticate anyway.

**To fix:** In the admin dashboard, go to **Identity and Access Management** > **API Keys** and delete the listed API
keys.

### A datastream can be the target of only one ETL mapping

**Table:** `etl_etlmapping` (`target_datastream` field)

**To fix:** In the admin dashboard, go to **ETL Orchestration** > **Etl mappings** and delete or re-target mappings so
that each datastream listed in the error is the target of at most one mapping.

### Placeholder variables must be unique per data connection

**Table:** `etl_placeholdervariable` (`name` and `variable_type` fields)

Each combination of name and variable type can only be used once per data connection.

**To fix:** In the admin dashboard, go to **ETL Orchestration** > **Placeholder variables** and rename or delete the
listed duplicates.

### Rating curve input values must be unique

**Table:** `products_ratingcurvepoint` (`input_value` field)

Each input value can only appear once in a rating curve.

**To fix:** In the admin dashboard, go to **Derived Data Products** > **Rating curve points** and delete or change the
duplicate points listed in the error.

## Data Loss and Transformations

The migrations make the following changes without stopping the upgrade. Review them before upgrading, and save copies
of any data you need to keep.

### Locations are merged into sites

**Tables:** `sta_location` (dropped), `sta_thing` (renamed to `sta_monitoringsite`)

Things are renamed to monitoring sites, and each site's Location is merged into the site.

- **Data loss:** If a Thing has more than one Location, only the Location with the lowest ID is kept. All others are
  deleted.
- **Data loss:** Location **name**, **description**, and **encoding type** are dropped. Coordinates, elevation,
  elevation datum, administrative areas, and country are kept.
- Location IDs no longer exist. Anything that referenced a Location by ID should use the monitoring site instead.

### Sampling feature types are dropped

**Tables:** `sta_thing` (`sampling_feature_type` field), `sta_samplingfeaturetype` (dropped)

- **Data loss:** Each Thing's **sampling feature type** is dropped, along with the sampling feature type vocabulary.
- **Sampling feature code** becomes the site's **code**, and **site type** becomes the site's **type**.

### Sensors become methods

**Tables:** `sta_sensor` (renamed to `sta_method`), `sta_sensorencodingtype` (dropped)

Sensors are renamed to methods. **Method code**, **method type**, and **method link** become **code**, **type**, and
**definition**. **Manufacturer** and **sensor model link** become **sensor model manufacturer** and
**sensor model definition**.

- **Data loss:** Each sensor's **encoding type** is dropped, along with the sensor encoding type vocabulary.

### Tags are consolidated

**Tables:** `sta_thingtag` and `sta_datastreamtag` (dropped)

Tags are now stored directly on each site and datastream as a set of key/value pairs, and each key can only appear
once.

- **Data loss:** If a Thing or datastream has more than one tag with the same key, only the most recently created tag's
  value is kept.
- Tags with an empty value are migrated, but v2 requires tag values to be non-empty. You'll need to fix those tags
  before you can edit the site or datastream they belong to. To avoid this, fill in or delete empty tag values in the
  admin dashboard under **Measurement Data** > **Thing tags** and **Datastream tags** before upgrading.

### File attachments become linked resources

**Tables:** `sta_thingfileattachment` and `sta_datastreamfileattachment` (renamed to
`sta_monitoringsitelinkedresource` and `sta_datastreamlinkedresource`), `sta_fileattachmenttype` (renamed to
`sta_linkedresourcetype`)

File attachments are renamed to linked resources, which can now point to either an uploaded file or an external URL.
Existing files are kept.

- File attachments get new IDs. Their v1 numeric IDs are replaced with UUIDs, so anything that referenced an attachment
  by its v1 ID will no longer work.

### Vocabulary tables get new IDs

**Tables:** `sta_sampledmedium`, `sta_datastreamaggregation` (renamed to `sta_aggregationstatistic`),
`sta_datastreamstatus`, `sta_methodtype`, `sta_unittype`, `sta_variabletype` (renamed to `sta_observedpropertytype`),
`sta_sitetype` (renamed to `sta_monitoringsitetype`), and `sta_fileattachmenttype` (renamed to `sta_linkedresourcetype`)

- Vocabulary terms get new IDs. Their v1 numeric IDs are replaced with UUIDs. Term names are unchanged, and records that
  use a term (for example, a datastream's status) store the name, so they aren't affected.

### Processing levels are restructured

**Table:** `sta_processinglevel`

v1 processing levels have a **code**, **definition**, and **explanation**. v2 processing levels have a **code**,
**name**, **definition** (a URL), and **description**. Each processing level is converted as follows:

- **Explanation** becomes **description**. An empty explanation becomes an empty description.
- If the **definition** is a URL, it stays the definition, and the **code** becomes the **name**.
- If the **definition** is 255 characters or fewer and isn't a URL, it becomes the **name**, and the definition is
  cleared.
- If the **definition** is longer than 255 characters and isn't a URL, it's added to the start of the **description**
  (followed by a blank line and the explanation), the **code** becomes the **name**, and the definition is cleared. To
  control the name and description yourself, shorten these definitions before upgrading.

When a processing level has no definition or code to use as its name, its ID is used as its name. You can rename these
processing levels after upgrading.

### Result qualifier codes become names

**Table:** `sta_resultqualifier`

Each result qualifier's **code** becomes its **name**. Observations that reference result qualifiers are unchanged.

### Definitions that aren't URLs are kept but no longer valid

**Tables:** `sta_observedproperty`, `sta_unit`, and `sta_sensor` (`definition`, `method_link`, and `sensor_model_link`
fields)

Observed property, unit, and method definitions (and method sensor model definitions) must be URLs in v2. Existing
values that aren't URLs are migrated unchanged, but you'll need to replace or clear them before you can edit those
records. To avoid this, update them in the admin dashboard before upgrading.

### API keys become service accounts

**Tables:** `iam_apikey` (renamed to `iam_serviceaccount`), `iam_collaborator`

Each API key becomes a service account. Existing keys keep working.

- In v1, an API key held a role directly. In v2, the role is assigned through a workspace collaborator record, which
  the migration creates for each API key.
- Each service account gets a generated email address in the form
  `<key prefix>@service-accounts.<SERVICE_ACCOUNT_EMAIL_DOMAIN>`.

### Permissions are consolidated

**Tables:** `iam_permission`, `iam_role`

In v1, each permission row granted one action (view, create, edit, delete, or all) on one resource type. In v2, each
role has a single permission row per resource type, with a flag for each action. Duplicate rows for the same role and
resource type are merged, and the granted actions are combined, so no access is lost.

- The resource types **Thing**, **Sensor**, and **APIKey** are renamed to **MonitoringSite**, **Method**, and
  **ServiceAccount**.
- The role **is API key role** and **is user role** flags are dropped. Any role can now be assigned to both users and
  service accounts.

### Workspace ownership settings are converted

**Table:** `iam_user` (`is_ownership_allowed` field)

The **is ownership allowed** flag is replaced by an **owned workspace limit**. Users who were allowed to own workspaces,
and all superusers, get an unlimited limit. All other users get a limit of `0`.

### Pending workspace confirmations

**Tables:** `iam_workspacedeleteconfirmation` (dropped), `iam_workspacetransferconfirmation`

- **Data loss:** Pending workspace delete confirmations are dropped.
- **Data loss:** The **initiated** timestamp of pending workspace transfers is dropped. The transfers themselves are
  kept.

### Audit log tables are no longer used

**Tables:** `easyaudit_crudevent`, `easyaudit_loginevent`, and `easyaudit_requestevent`

HydroServer v2 no longer includes the Django Easy Audit package. Its tables and data are left in your database, but
HydroServer no longer reads or writes them. Export any audit history you need before upgrading. You can drop these
tables after upgrading.

### Job Orchestration System tasks are kept

**Tables:** `orchestration_*`, `etl_*`, `products_*`, and `monitoring_*`

ETL, data product, and monitoring tasks, their schedules, and their run history are migrated as they are, and they
keep running on their existing schedules after the upgrade. Only the blocking changes above affect these tables, and
users don't need to change their tasks.

## Configuration Changes

v2 changes how HydroServer reads its settings. Review your environment variables against the tables below before you
start the v2 containers. For the full list of v2 settings, see
[HydroServer Production Environment Variables](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md#hydroserver-production-environment-variables).

### Settings to Check First

These settings behave differently in v2, and getting them wrong can stop HydroServer from starting or leave it running
in debug mode.

| Variable | What to do |
| --- | --- |
| `DEBUG` | Set to `False`. In v1, `DEBUG` defaulted to `False` unless `DEPLOYMENT_BACKEND` was `dev`. In v2, it defaults to `True`. |
| `STRICT_SECURITY` | New. Must be `True` in production. The published Docker image already sets it. |
| `IDP_OIDC_PRIVATE_KEY` or `IDP_OIDC_PRIVATE_KEY_FILE` | New. Generate an RSA key for HydroServer's OIDC identity provider and keep it the same across restarts. HydroServer doesn't start without it while `STRICT_SECURITY` and `IDP_OIDC_ENABLED` (the default) are `True`. |
| `MEDIA_STORAGE_ENABLED` | New, defaults to `False`. Set it to `True` if your v1 instance has uploaded file attachments. Otherwise, HydroServer rejects new uploads and, with local storage, stops serving existing files. |
| `SERVICE_ACCOUNT_EMAIL_DOMAIN` | New. The migrations use it to build an email address for each service account created from a v1 API key, so set it before running the migrations if you don't want the default, `hydroserver.local`. |

### Replaced Settings

| v1 variable | v2 replacement |
| --- | --- |
| `DEPLOYMENT_BACKEND` | Removed. Configure storage with `MEDIA_STORAGE_BACKEND`, `MEDIA_STORAGE_OPTIONS`, `STATIC_STORAGE_BACKEND`, and `STATIC_STORAGE_OPTIONS`, and set `DEBUG` and `STRICT_SECURITY` explicitly. If you relied on the JSON logs v1 wrote on GCP, set `LOG_FORMAT` to `json`. |
| `MEDIA_BUCKET_NAME`, `STATIC_BUCKET_NAME`, `GS_PROJECT_ID` | The `bucket_name` and `project_id` options in `MEDIA_STORAGE_OPTIONS` and `STATIC_STORAGE_OPTIONS`. |
| `AWS_CLOUDFRONT_KEY`, `AWS_CLOUDFRONT_KEY_ID` | Removed. Configure media storage through `MEDIA_STORAGE_BACKEND` and `MEDIA_STORAGE_OPTIONS`, and use `STATIC_HOST` to serve static files through a CDN. See [Serving Static and Media Files](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md#serving-static-and-media-files). |
| `TRUSTED_ORIGINS` | `CSRF_TRUSTED_ORIGINS`. Whether browsers may send cookies with cross-origin requests is now set separately, by `CORS_ALLOW_CREDENTIALS`. See [Hosts, Origins, and Cookies](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md#hosts-origins-and-cookies). |
| `APP_CLIENT_URL` | `WEB_CLIENT_URL`. You can leave it unset with the published Docker image, which serves the Data Management App from the same origin. |
| `ANON_THROTTLE_RATE`, `AUTH_THROTTLE_RATE` | `API_RATE_LIMITS`. v1 limited both to `20/s` by default, but v2 doesn't limit API requests unless you set it, for example to `{"anonymous": "20/s", "authenticated": "20/s"}`. See [Rate Limiting](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md#rate-limiting). |
| `ACCOUNT_RATE_LIMITS_DISABLED` | `ACCOUNT_RATE_LIMITS`. Set it to `false` to turn off account rate limits. |
| `DEFAULT_SUPERUSER_EMAIL`, `DEFAULT_SUPERUSER_PASSWORD` | Removed. Existing admin accounts are migrated. To create a new one, run `python manage.py createsuperuser`. |
| `LOAD_DEFAULT_DATA` | Removed. Load default vocabularies and roles from the admin dashboard. See [Default Data](/hosting-and-deployment/how-to/using-the-administrator-dashboard.md#default-data). |
| `ENABLE_AUDITS` | Removed, along with the audit log. See [Audit log tables are no longer used](#audit-log-tables-are-no-longer-used). |
| `DATA_CONNECTION_NOTIFICATION_CRONTAB` | Removed. Each data connection's notification emails follow that connection's own schedule. |

### Other New Settings

v2 also adds optional settings for caching, OIDC token lifetimes, task run retention, cookies, and log format. Their
defaults suit most deployments. If you don't set `CACHE_URL`, HydroServer uses a cache table in your database, which
the migrations create. See
[Preparing for Production Deployment](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md#preparing-for-production-deployment)
for each setting.

## Infrastructure Changes

- **Reverse proxy routes:** HydroServer's OIDC identity provider serves pages under `/identity/` and
  `/.well-known/`. If your reverse proxy only forwards some paths to HydroServer, add these two, and make sure it sends
  the `X-Forwarded-Proto` header.
- **Container commands:** the Gunicorn, Celery worker, and Celery scheduler commands are unchanged. Run all three on
  the v2 image, and set `CELERY_ENABLED` to the same value on each. See
  [Enabling Celery for HydroServer](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md#enabling-celery-for-hydroserver).
- **Setup commands:** the `setup_admin_user` and `load_default_data` management commands are removed. Use
  `createsuperuser` and the admin dashboard instead, as described in
  [HydroServer Management Commands](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md#hydroserver-management-commands).
- **Python version:** the image now runs Python 3.14 instead of 3.11. This only matters if you
  [build the image from source](/hosting-and-deployment/how-to/building-the-docker-image-from-source.md) or extend it.
- **Apps that sign users in:** apps that sign users in to HydroServer now use OIDC, so an admin must register each one
  as an OIDC client. See
  [Registering OIDC Clients](/hosting-and-deployment/how-to/using-the-administrator-dashboard.md#registering-oidc-clients).
