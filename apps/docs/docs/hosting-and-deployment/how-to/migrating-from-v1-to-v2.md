# Migrating from HydroServer v1 to v2

HydroServer v2 restructures much of the v1 data model. Upgrading runs a set of database migrations that convert your
v1 data to the v2 schema. This guide covers what you need to do to your data **before** upgrading, and what the
migrations will change, drop, or transform along the way.

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
4. Upgrade to v2 and run the migrations.

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
