# HydroServer Identity and Access Management

_Functional Specifications_

## 1 Introduction


This document outlines requirements for a proposed update to HydroServer’s identity and access management system. The goal of updating HydroServer’s access control system is to provide more secure, flexible, and user-friendly functionality for managing user permissions and access uniformly across all user-managed HydroServer resources. This update includes the addition of role-based collaboration that will enable larger organizations to delegate data management responsibilities to multiple users based on the principle of least privilege, meaning individual users should only have access to the specific data they need to perform their tasks. The update also includes the addition of HydroServer workspaces, which provide a simple and scalable organizational structure within which users can organize and manage access to all their HydroServer data in a uniform way rather than needing to manage individual resources independently from each other. In other words - this specification moves access control to the workspace level rather than having it specified at the individual Thing (site), Observed Property, Units, etc. level. This specification describes the key features, requirements, and workflows necessary to implement these improvements.

## 2 Definitions


User: An individual with a HydroServer account.

Federated Identity: A third-party authentication provider (e.g., Google, ORCID, HydroShare, UtahID) that allows a user to create or log in to their HydroServer account. A single HydroServer user account can be associated with multiple federated identities as long as the associated email address is the same.

Account Type: Each user account in HydroServer has one of the following three types: Admin, Standard, or Limited. Account types control site-wide permissions and access level.

Organization: An optional piece of metadata users can associate with their account representing the organization a user works for or is affiliated with. For the purposes of HydroServer, an organization is descriptive metadata about a user but not used to group users for the purpose of access control.

Resource: Any user-managed entity/object within HydroServer to which access is controlled. These include Things, Locations, Historical Locations, Tags, Photos, Datastreams, Observations, Sensors, Observed Properties, Processing Levels, Units, Result Qualifiers, Workspaces, Roles, Permissions, API Keys, Data Sources, and ETL Systems.

Workspace: A scoped collection of resources within HydroServer. Workspaces serve as the highest level for resource management and user collaboration in HydroServer, and access control is handled at the workspace level.

Owner: The primary user account associated with a workspace. All workspaces will have one and only one owner. Owners of workspaces always have full access to resources within the workspace. Ownership can be transferred to another user.

Collaborator: A user account associated with a workspace via a role. A workspace can have any number of collaborators associated with it.

Role: A set of permissions that defines a collaborator’s level of access to resources within a specific workspace. HydroServer will initially support the following roles: editor, admin, and viewer.

Permission: A specific level of access granted to an API key or role, defining an action (e.g., view, edit, create, delete) that can be performed on a type of resource (e.g., Thing, Datastream, etc).

Authentication: The process of verifying the identity of a user accessing HydroServer. Relies on emails/passwords, federated logins, API keys, and/or tokens to ensure a user is who they claim to be.

Authorization: The process of determining whether an authenticated user has permission to perform a specific action on a resource. This ensures that users can only perform approved actions on resources based on their workspace role and associated permissions.

## 3 Requirements


### 3.1 Authentication


- HydroServer must support local authentication (e.g., creating a user account using an email address and password).
- HydroServer must support federated authentication using third-party identity providers including Google, ORCID, and HydroShare. Site administrators must be able to add other identity providers as needed (e.g., UtahID).
- Email addresses used for HydroServer accounts must be verified before a user account is created.
- Each user must be identified by a unique verified email address that serves as the primary identifier for their account.
- HydroServer must allow users to associate multiple federated identities with their account.
- API keys may be used to support limited programmatic access for use with HydroServer’s APIs as an alternative to providing an email/password.
- HydroServer administrators must be able to enable and disable specific signup/login methods.

### 3.2 Accounts


All HydroServer user accounts have an account type. The account type determines site-wide permissions and access and is distinct from a role which determines permissions and access at the workspace level. HydroServer will have the following account types:
- Administrator: HydroServer supports the creation of admin user accounts. One admin user account will be created automatically when a new HydroServer instance is deployed. Additional admin accounts may be created if desired by HydroServer administrators. Admin user accounts primarily serve the following functions:
- Admin users have full read and write access to all HydroServer workspaces and resources. They can perform any action on behalf of any other HydroServer user account.
- Admin users may modify instance-level settings and metadata (e.g., user types, site types, etc).
- Admin users may create other user accounts, and toggle which users are allowed to own workspaces, if not allowed by default.
- Admin users will be able to perform actions both through the Data Management app as well as Django’s built-in admin dashboard.
- Standard: By default, all users who signup via the public signup page will be standard users. Standard user accounts have the following site-wide permissions:
- Standard user accounts can create and own workspaces.
- Standard accounts can be assigned as collaborators on workspaces.
- Limited: HydroServer administrators may optionally configure all new public users to be given limited accounts instead of standard accounts. The primary function of limited accounts is to allow public account creation but restrict the creation and ownership of workspaces to users who have been reviewed and approved by administrators. Limited user accounts have the following site-wide permissions:
- Limited accounts can be assigned as collaborators on workspaces.

### 3.3 Workspaces and Collaboration


A workspace is an organizing concept that will be added to the HydroServer software by this functional specification. Workspaces are a way to group HydroServer resources so that access control can be handled at the workspace level rather than for each HydroServer resource individually. Following are the requirements for HydroServer workspaces:

- Workspaces must serve as the highest level of user-managed resources in HydroServer. All other user-managed resources must belong to a workspace, either explicitly or implicitly through related resources. User managed resources within workspaces include the following:
- Things (sites)
- Locations
- Historical Locations
- Datastreams
- Observations
- Sensors
- Observed Properties
- Units
- Processing Levels
- Result Qualifiers
- Features of Interest (currently unimplemented by HydroServer)
- ETL Systems
- Data Sources
- API Keys
- Each workspace must have one and only one owner.
- Workspace owners always have full access to all resources in the workspace.
- Resource relation to a workspace will be denoted either explicitly by a workspace ID field in HydroServer’s database, or implicitly through relation to an upstream resource having a workspace ID field (e.g., Datastreams belong to the workspace of their related Thing).
- When a user account is disabled/deleted, all workspaces that the user owns that haven’t been transferred to another owner will be disabled/deleted (along with all resources contained within).
- Only the workspace owner may delete, rename, or change the visibility settings of a workspace.
- Owners must have a mechanism for transferring workspace ownership to another user.
- Only owners can transfer ownership. Collaborators cannot transfer ownership of a workspace.
- Owners can request to transfer ownership of a workspace to any active HydroServer user. The user to which the workspace will be transferred does not already need to be a collaborator within the workspace.
- Requests to transfer ownership of a workspace must be accepted by the new owner account before the ownership transfer occurs.
- Workspaces may have multiple collaborators.
- Collaborators must be associated with workspaces via a role.
- Any active HydroServer user can be added as a workspace collaborator.
- Owners and collaborators may add or remove collaborators to a workspace.
- Owners may add/remove editors and viewers.
- Editors may add/remove editors and viewers.
- Viewers may add/remove viewers.
- HydroServer administrators can create the following types of resources outside of a workspace: Sensor, ObservedProperty, Unit, ProcessingLevel, and ResultQualifier. These resources may be used in any HydroServer workspace to help avoid the creation of multiple copies of commonly used metadata across multiple workspaces.
- (Future work) When creating a new workspace, users must be able to select resources from other workspaces they own or collaborate on to copy to the new workspace.
- (Future work) When a user creates an account, a default workspace is automatically created for that account (if workspace creation is enabled for the site).

### 3.4 Roles


- Role-based access must be enforceable across all resource types within a workspace, ensuring consistent access control behavior. The following roles will be supported:
- Owner: Each workspace in HydroServer will have one owner associated with it. Owners have full read and write access to the workspace and all workspace resources. Only the owner of a workspace may rename it, set its visibility as public or private, or delete it. An owner may transfer ownership to another HydroServer user.
- Editor: Each workspace in HydroServer may have any number of editors. Editors have full read and write access to all workspace resources but cannot rename or delete a workspace. Editors can set the visibility of sites and datastreams within a workspace. Only users with edit permissions can execute scheduled jobs using HydroServer’s orchestration system.
- Viewer: Each workspace in HydroServer may have any number of viewers. Viewers have full read access to all workspace resources, regardless of workspace, site, or datastream visibility settings.
- Roles must contain a set of permissions that dictate what actions a user can perform on the workspace’s resources. Initially supported collaborator roles include:
- Editor - Viewer + create, edit, and delete resources within a workspace.
- Viewer - View only permissions for resources within a workspace.

### 3.5 API Keys


- Workspace owners and editors will be able to create API Keys to allow external systems to push data into HydroServer without exposing broader account credentials.
- API Key permissions will be limited to creating new observations in a workspace.
- (Future work) Users must be able to select the specific workspace, sites, or datastreams API Keys can push observations to.
- API Keys must be able to be disabled or deleted at any time, immediately revoking access.
- API Keys must have an optional expiration time. Users should be encouraged but not required to set an expiration for API Keys.
- API Keys must be able to be regenerated with a new key value without deleting and recreating them.

## 4 Information Model


The information model below shows the tables necessary to support HydroServer access control. The Workspace table serves as the link between HydroServer resources and users/collaborators. The following HydroServer tables will have a workspace ID field linking them to a workspace:
- Thing
- Sensor (Optional)
- ObservedProperty (Optional)
- ProcessingLevel (Optional)
- Unit (Optional)
- ResultQualifier (Optional)
- ETLSystem

Locations, HistoricalLocations, Datastreams, Observations, Tags, and Photos all belong to the workspace of their related Thing. DataSources belong to the workspace of their related ETLSystem.

Some metadata tables listed above have an optional workspace ID field and may be referenced in any workspace. Only HydroServer administrator users may create or modify these records without a workspace ID. These are intended to reduce the repetition of commonly used metadata in the database.

Authentication will be primarily handled by the Django AllAuth extension, shown by the purple tables below. Tables in yellow primarily deal with HydroServer resource authorization. Tables in green represent HydroServer SensorThings resources that are directly linked to the Workspace table. Tables in blue represent HydroServer resources used for managing HydroServer extract, transform, load (ETL) capabilities.

Figure 1. Access Control data model. Access control consists of authentication (purple) and authorization (yellow). SensorThings models (green) and ETL models (blue) are considered access-controlled resources in HydroServer.

## 5 Supported Functionality


In order to support HydroServer’s updated access control requirements, several API endpoints and frontend pages and forms will need to be modified or created. All API endpoints and database models (tables) will be developed within Django and Django ORM, or provided by a Django extension. Frontend forms and pages will be developed within HydroServer’s Data Management app using Vue, but certain features may be split across multiple frontend apps in the future.

### 5.1 API Endpoints

​​
All authorization and user profile related functionality will be developed in a Django app called ‘iam’. This app was formerly named ‘accounts’ but will be renamed so as not to be confused with Django AllAuth’s ‘account’ app. The Django AllAuth extension will be used to handle HydroServer authentication and provides the following two apps to do so: ‘account’ and ‘socialaccount’. The API endpoints described below will be developed within HydroServer’s ‘iam’ app or provided by Django AllAuth’s ‘account’ and ‘socialaccount’ apps.

### 5.2 Authentication Endpoints


HydroServer browser authentication will be handled by the Django AllAuth extension. This includes the following endpoints:
- Login
- Signup
- Verify Email
- Reauthenticate
- Logout
- Reset Password
- Federated Login (OAuth2 workflow)

The full AllAuth API specification can be found at the following link:
https://docs.allauth.org/en/dev/headless/openapi-specification/

#### 5.2.1 User


Endpoint: /profile
Methods: GET, PATCH, DELETE
Description:
- GET: Retrieve authenticated user details.
- PATCH: Update user-specific details such as name, organization, or preferences.
- DELETE: Delete the user account, including all owned workspaces and associated data (or deactivate depending on site admin settings).
Note: User creation and authentication are managed via AllAuth API.

#### 5.2.2 Workspaces


Endpoint: /workspaces
Methods: GET, POST
Description:
- GET: Retrieve all workspaces the authenticated user owns, collaborates on, or has been invited to own or collaborate on. Workspaces the user has no association with are excluded.
- POST: Create a new workspace owned by the authenticated user. The request body may include an optional parameter to copy resources from an existing workspace (Future work).
Note: Because workspaces will be used for filtering, the GET Workspaces endpoint must have a filter to return all public workspaces including those the user is not associated with.

#### 5.2.3 Workspace


Endpoint: /workspaces/{workspace_id}
Methods: GET, PATCH, DELETE
Description:
- GET: Retrieve details of a specific workspace, including:
- owner: The user who owns the workspace.
- collaborators: A list of users with role-based (editor, viewer) access to the workspace.
- visibility: The workspace’s visibility status (private, public).
- PATCH: Allow the owner to edit workspace properties such as name or visibility.
- DELETE: Remove the workspace and all associated resources permanently, or disable it temporarily based on HydroServer administrator settings.

#### 5.2.4 TransferWorkspace


Endpoint: /workspaces/{workspace_id}/transfer
Methods: POST
Description:
- POST: Allows the workspace owner to invite another HydroServer user to take ownership of the workspace.
Note: Transfer is not final until the invited user accepts.

#### 5.2.5 AcceptWorkspaceTransfer


Endpoint: /workspaces/{workspace_id}/transfer/accept
Methods: POST
Description:
- POST: Completes workspace ownership transfer. Only the invited user may accept the transfer. Once accepted, the existing workspace owner is replaced by the new owner. The old owner will no longer be associated with the workspace unless invited to collaborate via a role.

#### 5.2.5 RevokeWorkspaceTransfer


Endpoint: /workspaces/{workspace_id}/transfer/revoke
Methods: POST
Description:
- POST: Cancel an in-progress workspace ownership transfer. Either the current owner or the invited owner can perform this action.

#### 5.2.6 Roles


Endpoint: /workspaces/{workspace_id}/roles
Methods: GET
Description:
- GET: Retrieve all roles in a specific workspace along with their associated permissions.

#### 5.2.7 Role


Endpoint: /workspaces/{workspace_id}/roles/{role_id}
Methods: GET
Description:
- GET: Retrieve details of a specific role, including permissions and associated collaborators.

#### 5.2.8 ApplyRole


Endpoint: /workspaces/{workspace_id}/roles/{role_id}/apply
Methods: POST
Description:
- POST: Assign a role to another HydroServer user.

#### 5.2.9 RevokeRole


Endpoint: /workspaces/{workspace_id}/roles/{role_id}/revoke
Methods: POST
Description:
- POST: Allows a workspace owner or authorized collaborator to remove a role from a workspace collaborator.

#### 5.2.10 APIKeys


Endpoint: /workspaces/{workspace_id}/api-keys
Methods: GET, POST
Description:
- GET: Retrieve a list of all API Keys associated with the workspace.
- POST: Create a new API Key for the workspace.

#### 5.2.11 APIKey


Endpoint: /workspaces/{workspace_id}/api-keys/{api_key_id}
Methods: GET, PATCH, DELETE
Description:
- GET: Get details for a specific API Key.
- PATCH: Edit a specific API Key.
- DELETE: Delete an API Key.

#### 5.2.12 RegenerateAPIKey


Endpoint: /workspaces/{workspace_id}/api-key/{api_key_id}/regenerate
Methods: POST
Description:
- POST: Regenerate an API Key. This allows a key to continue to be used with a new key value if the original value is lost or compromised.

### 5.3 User Interfaces


#### 5.3.1 Login Page


HydroServer should include a login form with the following features:
- Provide an email/password form for users to login with.
- Allows users to select a third-party identity provider to login with (e.g., Google, ORCID).
- Users should be given an option to reset their password.

HydroServer’s existing login page meets these requirements, but will need to be updated to interface with the Django AllAuth API. The existing GUI can remain unchanged.

#### 5.3.2 Signup Page


HydroServer should include a signup page with the following features:
- Allows users to create an account by providing an email, password, and contact information.
- Allows users to select a third-party identity provider (e.g., Google, ORCID) to create an account.
- If an account with a given email has already been created, the third-party identity provider should be associated with the existing account.
- New users should go through an email verification flow before their account is created. Unverified emails should not block those emails from being used to sign up.
- New users who are missing required account details (name, user type, etc) will be prompted to fill in these details before they can create or join workspaces. This can sometimes happen while signing up via a third-party identity provider.

HydroServer’s existing signup page meets these requirements, but will need to be updated to interface with the Django AllAuth API. The existing GUI can remain unchanged.

#### 5.3.3 Profile Page


HydroServer should include a profile page with the following features:
- Allows users to edit their contact info or link to other federated identity accounts (e.g., HydroShare).
- Users should also be able to delete their account from this page. Deleted accounts should be marked as inactive for a period of time before being permanently deleted. During this time, users can still login and reactivate their account. HydroServer administrators should be able to set or disable this time window.

HydroServer’s existing profile page meets these requirements but will need to be updated to interface with the updated user profile endpoint described in the previous section. The existing GUI can remain unchanged.

#### 5.3.4 Browse Monitoring Sites Page


HydroServer’s current Browse Monitoring Sites page features filters in the left sidebar. The existing “Organizations” filter will be replaced by a “Workspaces” filter. All public workspaces and workspaces the user owns or collaborates on will be visible in the filter dropdown. Sites and their workspace must both be marked as “public” to appear on this page to unaffiliated users. The rest of this page can remain unchanged.

#### 5.3.5 Site Details Page


A “Workspace” field should be added to the site’s metadata. The “Site Owners” field should be updated to show the workspace owner and collaborators. A privacy toggle button will replace the Access Control button on this page. The rest of this page can remain unchanged.

#### 5.3.6 Site Access Control Form (Modified to Workspace Access Control Form)


Access controls will primarily be managed at the workspace layer. The site access control form will be modified for use at the workspace level. It will include:
- Ability to toggle a workspace to be public or private.
- Ability to transfer ownership of a workspace to a new owner.
- Ability to add collaborators to a workspace and assign them a role.
- Ability to create API keys for a workspace.

Primary ownership and secondary ownership will no longer be applied at the site level and will no longer be managed on this form. Privacy settings for individual sites will be added as a setting to the row for each site on the “Your Sites” page and will also be available as a toggle on the “Site Details” page.

#### 5.3.7 Your Sites Page


Workspaces will be primarily managed from the Your Sites page. The following modifications will be made to Your Sites:
- A “Workspace” dropdown will be added to the top of this page. This dropdown shows all workspaces that a user either owns or collaborates on. Your Sites will only show sites for the selected workspace.
- A button next to the workspace dropdown will allow users to create a new workspace.
- A button next to the workspace dropdown will navigate users to a “Manage Workspace” page where they can view and modify workspace details such as privacy settings, workspace ownership transfers, collaborators, and API keys.
- An option should be added to the sites table to toggle visibility of each site from public to private.

#### 5.3.8 Register Site Form


The first field in this form should be a required “Workspace” dropdown. Options should include workspaces you either own or collaborate on with edit permissions. The rest of this page can remain unchanged.

Note: We may want to consider allowing users to create new workspaces from this form using a combobox field instead of a select field. This could encourage creation of workspaces users don’t need, but it would remove the extra step of going to a separate page to create a workspace. The only required field to create a workspace is its name.

#### 5.3.9 Edit Site Form


An owner or editor may change the workspace of a site to another workspace they are an owner or editor of. Doing so will perform the following actions:
- All metadata referenced by the site will be copied to the new workspace. If this results in duplicate metadata being created in the new workspace, the user will be responsible for cleaning it up.
- The site (including downstream datastreams and observations) will be transferred from the old workspace to the new workspace.
- All references to the old metadata by the site’s datastreams will be updated to point to the copies in the new workspace.

Before performing this action, users should be asked to confirm the transfer and told that the transfer will result in metadata being copied to the new workspace. Users will also be warned that existing ETL workflows may be broken by the action that they will need to resolve manually.

#### 5.3.10 Manage Metadata Page


Metadata should be presented in the context of a specific workspace to avoid confusion. A “workspace” dropdown should be added to the top of this page to select a workspace the user owns or collaborates on. The table will only display metadata associated with one workspace at a time.

A button at the top of the Manage Metadata page will enable an owner or editor of an existing workspace to copy metadata from one workspace to another workspace. Clicking this button will open a form where the user can select the destination workspace and select which metadata to copy (i.e., sensors, observed properties, processing levels, units, and result qualifiers). This functionality will transfer all records for each selected entity into the selected destination workspace.

NOTE: The user should be notified that copying metadata from one workspace to another workspace may result in duplicate metadata records being created.

#### 5.3.11 Add Metadata Forms


Each form used to create new metadata elements (Sensors, Observed Properties, Processing Levels, Units, and Result Qualifiers) should make it clear which workspace the metadata is being created in via information presented at the top of the form. The workspace within which the metadata is being created will be the workspace selected on the Manage Metadata page. Otherwise, these forms will remain unchanged.

#### 5.3.12 Edit Metadata Forms


These forms will remain unchanged other than displaying the selected workspace with which the metadata is associated at the top of the form. The workspace for existing metadata will not be editable. Metadata can be copied from one workspace to another, but the workspace associated with a particular metadata entity instance (units, processing levels, etc.) cannot be changed.

#### 5.3.13 Visualize Data Page


HydroServer’s current Visualize Data page features filters in the left sidebar. A “Workspaces” filter should be added to this sidebar at or near the top that allows users to filter sites by workspace. The rest of this page can remain unchanged.

#### 5.3.14 Manage Data Sources Page


TBD

#### 5.3.16 Manage Workspace Page (New)


HydroServer should include a button to access a page where a user can manage Workspace details. This will allow users to view and manage specific workspaces they own or collaborate on. This page, which will be accessed from the Your Sites page, should provide the following functionality:
- The button to access this page will not be displayed for users who are not owners or collaborators on a workspace.
- Owners will be able to rename, change visibility, transfer ownership of, or delete workspaces.
- This page will show a list of users associated with the workspace, including the owner and all collaborators with their role.
- Owners and collaborators will be able to invite other users to collaborate on the workspace, remove collaborators, or edit collaborator roles.
- This page will not directly list SensorThings or ETL resources associated with the workspace.
- This page will show a list of all API Keys associated with the workspace. Owners and collaborators with an editor role may create new API Keys from here.

#### 5.3.18 API Key Detail Form (New)


New API Keys should have a name and description. For now API keys will only be used to push observations data to a subset of sites that the user selects. The default permissions should be all sites within a workspace.

- Authorized users should be able to view, edit, and delete API Keys with this page.
- API Keys should be restricted to loading observations to one or more datastreams within a workspace.
- Upon creating a new API Key, users should be given an option to view or download the key. They should be told to keep the key secure as they will not be able to view it again after creating it.
- Users should be given an option to regenerate keys if they lost the original key or it was compromised. Users should be warned that old keys will be invalidated and that they will have to update any applications that use those API keys.

NOTE: Best practice is for the user creating the API key to create it and put it somewhere safe so that it can be given to other developers if needed. Otherwise another developer may have to regenerate the key, which may break existing jobs that use the old key.
Appendix A
Permissions Associated with HydroServer Roles

The following table lists HydroServer functionality and which HydroServer user roles will have permissions for each function. An “X” indicates that the user role will have access to perform the listed function.

Table A-1. Permissions associated with HydroServer user roles.

Action
Any User
Website Admin
Owner
Editor
Viewer
Notes
Modify sitewide HydroServer settings as part of deployment

X

Create site admin accounts

X

Override or reset access control for any user

X

Disable creation of workspaces

X

Disable creation of user accounts

X

Disable identity providers for account creation as part of deployment

X

Browse public monitoring sites
X

X
X
X

Browse private monitoring sites

X
X
X

Create a new workspace
X

Unless this capability is disabled by a Site Admin. The creating user becomes the owner.
Rename a workspace

X

Delete a workspace

X

Set access control for a workspace

X
X
X
Users may add other users to a workspace at their same permission level.
Make a workspace public or private

X

View public sites within a workspace (via Browse Sites and site landing pages)
X

X
X
X

View a list of all sites within a workspace (public and private)

X
X
X

View a landing page for a private site

X
X
X

View a landing page for a public site
X

X
X
X

Create a new site within a workspace

X
X

Edit metadata for an existing site within a workspace

X
X

Delete a site within a workspace

X
X

Make a site within a workspace public or private

X
X

Create a new datastream for a site within a workspace

X
X

Edit metadata for a datastream for a site within a workspace

X
X

View public metadata for a datastream for a site
X

X
X
X
This is overridden if the site or workspace is private.
View private metadata for a datastream for a site

X
X
X

View public data for a datastream (via site landing page and visualize data page)
X

X
X
X

View private data for a datastream (via site landing page and visualize data page)

X
X
X

Made metadata for a datastream public or private

X
X

Make data for a datastream public or private

X
X

Insert data for a datastream

X
X

Also API keys
Edit data for a datastream (insert, update, delete)

X
X

Create an API key for a workspace

X
X

Configure HydroShare archival for a site

X
X

Download data as CSV for a public datastream
X

X
X
X

Download data as CSV for a private datastream

X
X
X

Delete a datastream

X
X

View metadata resources for a workspace

X
X
X

Create new metadata resource within a workspace

X
X

Edit metadata resource within a workspace

X
X

Delete metadata resource from a workspace

X
X

View data sources within a workspace for loading data

X
X
X

Create a data source within a workspace for loading data

X
X

Edit a data source within a workspace for loading data

X
X

Delete a data source from a workspace

X
X

Link data sources to datastreams within a workspace for loading data

X
X

View data loaders within a workspace

X
X
X

Manage data loaders within a workspace (create, edit, or delete)

X
X
