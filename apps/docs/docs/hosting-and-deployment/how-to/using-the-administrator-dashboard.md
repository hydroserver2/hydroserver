# Using the Django Admin Dashboard

Once HydroServer is running and accessible, instance administrators can use the Django admin dashboard to manage
deployment-wide settings, default metadata, controlled vocabularies, authentication providers, and selected maintenance
actions.

## Access the Admin Dashboard

Log in to the administrator dashboard at:

```
https://<your-hydroserver-domain>/admin
```

Only users with **Staff status** can access the dashboard. Users with **Superuser status** can manage all admin models
and run privileged admin actions. To create an administrator account programmatically, run the following command and
follow the prompts to set an email and password:

```bash
python manage.py createsuperuser
```

Admin users can also upgrade other user accounts to administrators through the admin dashboard by clicking on
**Identity and Access Management** > **Users**, selecting a user, then toggling both **Superuser Status** and
**Staff Status** to `true`.

## User Accounts and Access

HydroServer can be configured to limit access to certain features for new users by default via the
`ACCOUNT_OWNERSHIP_ENABLED` setting. If this setting is not enabled, new users are assigned limited accounts. Limited
accounts cannot create or own workspaces, but they can be added as collaborators to existing workspaces.

Administrators can manually upgrade a limited account to a standard account by clicking on
**Identity and Access Management** > **Users**, selecting a user, and changing **Owned workspace limit** from `0` to a
positive number. Leaving the field blank allows unlimited workspace ownership.

The **Identity and Access Management** section also exposes the following admin models:

| Model                | Purpose                                                                                                                                                                      |
| --- | --- |
| **Users**            | Manage user profile fields, account status, staff/superuser access, and workspace ownership limits.                                                                          |
| **Organizations**    | Manage organizations that can be associated with users and workspaces.                                                                                                       |
| **Workspaces**       | Review or edit workspace ownership, privacy, and workspace metadata.                                                                                                         |
| **Roles**            | Configure reusable permission bundles for user and service-account collaborators.                                                                                            |
| **Permissions**      | Review the resource-level permissions that belong to roles.                                                                                                                  |
| **Collaborators**    | Review or edit user and service-account access to workspaces.                                                                                                                |
| **Service Accounts** | Review service-account metadata and activate or deactivate accounts. API keys are created and regenerated from Workspace Management, where the new secret can be shown once. |

## HydroServer Configuration

To update the HydroServer domain used in emails and notifications, go to **Sites** > **example.com** and change the
domain to match your HydroServer domain.

The following website settings can be configured under **Website Configuration**:

| Model | Purpose |
| --- | --- |
| **Instance Configuration** | Configure instance-wide website content and legal links. |
| **Analytics Configuration** | Enable or disable Microsoft Clarity analytics. |
| **Map Configuration** | Configure the default map view, default map layers, and map service providers. |
| **Map Layers** | Create the map layers available to users in HydroServer map controls. |
| **Contact Information** | Add contact cards shown on the About page. |
| **Site Type Icons** | Customize which icons are used for different monitoring site types. |

### Instance Configuration

Use **Website Configuration** > **Instance Configuration** to manage general website settings:

| Field | Purpose |
| --- | --- |
| **Show about information** | Shows or hides the About page information block. |
| **About page title** | Sets the heading for the About page information block. |
| **About page text** | Sets the body content for the About page information block. |
| **Terms of use link** | Sets the Terms of Use link exposed by the web application. |
| **Privacy policy link** | Sets the Privacy Policy link exposed by the web application. |
| **Copyright** | Sets the copyright notice shown by the web application. |

### Analytics Configuration

Use **Website Configuration** > **Analytics Configuration** to optionally enable
[Microsoft Clarity](https://clarity.microsoft.com/) analytics:

| Field | Purpose |
| --- | --- |
| **Enable clarity analytics** | Turns Microsoft Clarity tracking on or off. |
| **Clarity project id** | Stores the project ID from the Microsoft Clarity project settings. |

### Map Configuration

Use **Website Configuration** > **Map Configuration** to control the initial map state and map service providers:

| Field | Purpose |
| --- | --- |
| **Default latitude** | Sets the latitude used when a map first loads without a more specific site extent. |
| **Default longitude** | Sets the longitude used when a map first loads without a more specific site extent. |
| **Default zoom level** | Sets the initial map zoom level. |
| **Default base layer** | Selects the default basemap from the configured **Map Layers**. |
| **Default satellite layer** | Selects the default satellite imagery layer from the configured **Map Layers**. |
| **Elevation service** | Selects the elevation lookup provider. Available options are **Open Elevation** and **Google**. |
| **Geo service** | Selects the geocoding/search provider. Available options are **Nominatim** and **Google**. |

If a Google-backed service is selected, make sure the deployment has the required Google service credentials or API key
configuration before relying on that option in production.

### Map Layers

Use **Website Configuration** > **Map Layers** to add basemap and overlay options:

| Field | Purpose |
| --- | --- |
| **Name** | Sets the display name shown to users. |
| **Type** | Classifies the layer as a **Basemap** or **Overlay**. |
| **Priority** | Controls layer ordering when multiple layers are available. |
| **Source** | Stores the map tile or layer source URL used by the frontend map. |
| **Attribution** | Sets the attribution text required by the layer provider. |

After creating a basemap or satellite layer, return to **Map Configuration** to select it as a default layer.

### Contact Information

Use **Website Configuration** > **Contact Information** to add organization contact options to the About page:

| Field | Purpose |
| --- | --- |
| **Title** | Sets the contact option title. |
| **Text** | Adds supporting details for the contact option. |
| **Action** | Sets the call-to-action text shown for the contact option. |
| **Icon** | Stores the icon identifier used by the web application. |
| **Link** | Sets the URL or address opened by the contact action. |

Contact information is only visible when About page information is enabled in **Instance Configuration**.

### Site Type Icons

Use **Website Configuration** > **Site Type Icons** to customize monitoring site icons in the Data Management app. The
available icon records are fixed, but administrators can edit the site type names and keywords associated with each icon.

Enter one site type name or keyword per line. Matching ignores case and punctuation, and longer matching keywords take
precedence. For example, a site type of `Stream Gage` can map to the gauge icon while `Stream` maps to the water icon.
Each keyword can be assigned to only one icon. Leave an icon's keyword list empty if it should not be used.

If no configured keyword matches a site's type, the Data Management app uses the default outlined map marker icon.

## Data and Metadata Administration

The **Measurement Data** section exposes the core HydroServer data models. Most data entry should happen through the
HydroServer web application, API, or client libraries, but the Django admin can be useful for reviewing records and
performing administrator-only maintenance.

Additional vocabulary models also appear in this admin section and are documented under **Controlled Vocabularies**
below.

| Model | Purpose |
| --- | --- |
| **Things** | Manage monitoring sites and their workspace/privacy metadata. |
| **Locations** | Review or edit site location records. |
| **Methods** | Manage reusable method metadata, including optional instrument details. |
| **Observed Properties** | Manage reusable observed property metadata. |
| **Units** | Manage reusable unit metadata. |
| **Processing Levels** | Manage reusable processing level metadata. |
| **Datastreams** | Review datastream metadata and run selected maintenance actions. |
| **Result Qualifiers** | Manage result qualifier codes. |
| **File Attachment Types** | Manage file attachment type vocabulary values. |
| **Monitoring Site File Attachments** | Review files attached to monitoring sites. |
| **Datastream File Attachments** | Review files attached to datastreams. |
| **Monitoring Site Tags** | Review key/value tags attached to monitoring sites. |
| **Datastream Tags** | Review key/value tags attached to datastreams. |

The **Datastreams** admin page includes two actions for selected datastreams:

- **Populate with test observations**: Generates test observations for selected datastreams. This is intended for
  development and demonstration environments.
- **Delete datastream observations**: Deletes observations for selected datastreams and resets the datastream
  phenomenon/result time ranges and value count.

Use these actions carefully. They change observation data directly and should not be used on production data unless that
is the intended administrative operation.

## Default Data

Several HydroServer models can be populated with bundled default data through the admin dashboard. Open one of the
models below and click its **Load Default ...** button in the upper-right corner of the changelist page:

| Section | Model | Default data |
| --- | --- | --- |
| **Identity and Access Management** | **Roles** | Default workspace roles and permissions. Load these before users add collaborators or API keys to workspaces. |
| **Identity and Access Management** | **User Types** | Default user type vocabulary values. |
| **Identity and Access Management** | **Organization Types** | Default organization type vocabulary values. |
| **Measurement Data** | **Observed Properties** | Default observed property metadata. |
| **Measurement Data** | **Processing Levels** | Default processing level metadata. |
| **Measurement Data** | **Units** | Default unit metadata. |
| **Measurement Data** | **Site Types** | Default monitoring site type vocabulary values. |
| **Measurement Data** | **Sampling Feature Types** | Default sampling feature type vocabulary values. |
| **Measurement Data** | **Method Types** | Default method type vocabulary values. |
| **Measurement Data** | **Variable Types** | Default variable type vocabulary values. |
| **Measurement Data** | **Unit Types** | Default unit type vocabulary values. |
| **Measurement Data** | **Datastream Aggregations** | Default aggregation statistic vocabulary values. |
| **Measurement Data** | **Datastream Statuses** | Default datastream status vocabulary values. |
| **Measurement Data** | **Sampled Mediums** | Default sampled medium vocabulary values. |
| **Measurement Data** | **File Attachment Types** | Default file attachment type vocabulary values. |

The load action imports fixture data into the database. It does not replace the need to review locally customized
metadata after upgrades.

## Controlled Vocabularies

HydroServer forms use several administrator-managed vocabularies. Add or edit these records to control the choices users
see in metadata forms:

| Section | Models |
| --- | --- |
| **Identity and Access Management** | **User Types**, **Organization Types**, **Roles** |
| **Measurement Data** | **Datastream Aggregations**, **Datastream Statuses**, **File Attachment Types**, **Method Types**, **Sampled Mediums**, **Sampling Feature Types**, **Site Types**, **Unit Types**, **Variable Types** |

Workspace-scoped metadata such as observed properties, units, processing levels, methods, and result qualifiers can also
be reviewed in the admin dashboard. When a record has no workspace, it is available as system-level metadata.

## Third-Party Identity Providers

To enable authentication through third-party identity providers, do the following:

- Navigate to **Social Applications** > **Add Social Application**.
- Select a supported provider, such as Google or HydroShare.
- Enter a unique ID, name, client ID/key, and secret key from the provider.
- Optionally add JSON settings, for example:
  ```json
  {
    "allowSignUp": true,
    "allowConnection": true
  }
  ```
- Use **allowSignUp** to control whether users can sign up with this provider.
- Use **allowConnection** to control whether users can connect the provider to an existing HydroServer account.
- When omitted, **allowSignUp** defaults to enabled, but **allowConnection** is enabled only when explicitly set to
  `true`.
- Assign the default site that the provider can authenticate against.
