# Using the Administrator Dashboard

Once HydroServer is running and accessible, additional configuration settings can be managed through the admin 
dashboard.

## Access the Admin Dashboard

You can log in to the administrator dashboard at: 

```
https://<your-hydroserver-domain>/admin`
```

Only administrators and staff accounts can access the dashboard. To create an administrator account programmatically, 
run the following command and follow the prompts to set an email and password:

```bash
python manage.py createsuperuser
```

Admin users can also upgrade other user accounts to administrators through the admin dashboard by clicking on 
**Identity and Access Management** → **Users**, selecting a user, then toggling both **Superuser Status** and 
**Staff Status** to `true`.

## HydroServer User Accounts

HydroServer can be configured to limit access to certain features to new users by default via the 
**ACCOUNT_OWNERSHIP_ENABLED** setting. If not enabled, all new users will automatically be assigned a limited account. 
Limited accounts cannot create or own workspaces, however, they can be added as collaborators to existing workspaces. 

Administrators can manually upgrade a limited account to a standard account by clicking on 
**Identity and Access Management** → **Users**, selecting a user, and toggling **Is Ownership Allowed** to `true`.

## HydroServer Configuration

To update the HydroServer domain used in emails and notifications, go to **Sites** → **example.com** and change the 
domain to match your HydroServer domain.

The following website settings can be configured under **Website Configuration**:

- **Instance Configuration**: Customize the `About` page with information about your organization.  
- **Analytics Configuration**: Optionally enable [Microsoft Clarity](https://clarity.microsoft.com/).  
- **Map Configuration**: Define default map layers, view, geospatial, and elevation services.  
- **Map Layers**: Add additional map layer options for pages that use maps.  
- **Contact Information**: Add organization contact information for display on the `About` page.  

## Third-Party Identity Providers

To enable authentication through third-party identity providers, do the following:

- Navigate to **Social Applications** → **Add Social Application**.  
- Select a supported provider (e.g., Google, HydroShare).  
- Enter a unique ID, name, client ID/key, and secret key from the provider.  
- (Optional) Add JSON settings, for example:  
  ```json
  {
    "allowSignUp": true,
    "allowConnection": true
  }
  ```  
  - **allowSignUp**: (true/false) — whether users can sign up and log in with this provider.  
  - **allowConnection**: (true/false) — whether users can connect the provider to an existing HydroServer account.  
- Assign the default site that the provider can authenticate against.  

## HydroServer Default Data

Several HydroServer models can be populated with default data, or be customized through the admin dashboard. The 
following models have a **Load Default Data** option that can be used to populate the model with default 
data:

- **Identity and Access Management** → **Roles** (Default data must be loaded before users can add collaborators or API keys to workspaces)
- **Measurement Data** → **Observed Properties**
- **Measurement Data** → **Processing Levels**
- **Measurement Data** → **Result Qualifiers**
- **Measurement Data** → **Sensors**
- **Measurement Data** → **Units**

## HydroServer Vocabularies

There are several user forms throughout HydroServer that can be populated with custom values. These values can be 
added through the admin dashboard by populating the following models:

- **Identity and Access Management** → **User Types**
- **Identity and Access Management** → **Organization Types**
- **Measurement Data** → **Datastream Aggregations**
- **Measurement Data** → **Datastream Statuses**
- **Measurement Data** → **Method Types**
- **Measurement Data** → **Sampled Mediums**
- **Measurement Data** → **Sampling Feature Types**
- **Measurement Data** → **Sensor Encoding Types**
- **Measurement Data** → **Site Types**
- **Measurement Data** → **Unit Types**
- **Measurement Data** → **Variable Types**
