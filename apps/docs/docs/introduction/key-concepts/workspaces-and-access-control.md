# Workspaces and Access Control

HydroServer is built to handle not only multiple users with varying permission levels for one organization, but multiple organizations that may be sharing the same instance of HydroServer. This is accomplished primarily through workspaces.

## Workspaces

Think of a workspace as Google Drive or Microsoft OneDrive folder. The person who creates the folder is automatically the owner. They can then share the folder with anyone they want and give them either edit or view only permissions. Any one person can have different permissions for various folders shared with them.

Ownership within the HydroServer system is user-centric, meaning individual user accounts, rather than organizations, own the sites, datastreams, and metadata contained within a Workspace. Each user's account is the central point of control and responsibility for their associated hydrologic data. Organization information, when present, acts as an extension of the user's information. A user may be associated with an organization, but it is the user's account that maintains ownership and control over the data.

All resources in HydroServer (monitoring sites, datastreams, etc.) are handled within the context of a workspace. When you create a new site, you'll first decide which workspace it belongs to. It then inherits all the permissions of that workspace.

## User Roles

Each collaborator in a workspace is assigned a role. A role is a set of permissions configurable at the resource level. For example, you can give a role read only access to the monitoring sites in a workspace, but give it full edit access to the datastreams of a workspace. By default, HydroServer ships with owner, editor, and viewer roles, but you can configure your own as an admininstrative option.

The following table is a comparison of permissions for the owners, editors, and viewers of a workspace.

| Permission                                              | Owner | Editor | Viewer | Data Loader |
|---------------------------------------------------------| ----- | ------ | ------ |-------------|
| Rename, transfer, edit privacy of workspace             | Yes   | No     | No     | No          |
| Invite new workspace collaborators                      | Yes   | Yes    | No     | No          |
| Create, update, delete sites, datastreams, and metadata | Yes   | Yes    | No     | No          |
| Stream observations into datastreams                    | Yes   | Yes    | No     | Yes         |
| Set up Job Orchestration System tasks                   | Yes   | Yes    | No     | Yes         |
| View public and private data within workspace           | Yes   | Yes    | Yes    | Yes         |

## API Keys

Remote systems code or applications may need to authenticate with HydroServer in whatever data loading, retrieval, or analysis workflows you build. Giving your username and password to these systems is risky since they'll have _all_ the permissions you do - including deleting your account and data. It's better to create an API key that has the minimum permissions required for the external system to do its job. API keys are assigned roles the same as collaborators. API keys can be designated with "Data Loader", "Editor", and "Viewer" permissions.

## Data Visibility

It's assumed in a HydroServer setup that you want your data to be publicly viewable. By default, when you load data to a datastream, any guest of your site will be able to view that data and all related metadata. These visibility setting can be changed at the workspace, site, and datastream levels.

1. **Workspace Privacy**: This setting determines whether a workspace is private or public. If your workspace is private, all sites, datastreams, and associated metadata will only be accesible to the workspace owner and collaborators.

2. **Site Privacy**: This setting determines whether your site is private or public. If you set your site to private, it means that only the workspace owners and collaborators can view the site and all associated datastreams through the website or API. This is like having a closed folder that only selected people can open. This allows users to set some sites as public and others as private within a public workspace.

3. **Datastream Privacy**: This setting is about who can see a specific datastream at your site. Even if your site is public, you might want to keep certain datastreams of that site private. When this setting is on, it means that only the workspace owners and collaborators can view this particular datastream's details and data.

4. **Datastream Data Visibility**: This is a convenience setting for controlling visibility of data in the Data Management Web Application. The datastream is considered public and its metadata will be visible to the public, but datastream observations will be hidden. Note: Observations can still be retrieved by anyone through the SensorThings API regardless of this setting.

These privacy settings work in a hierarchical, conditional manner:

If you set the **Site Privacy** to private (thing.is_private), then both **Datastream Visibility** (datastream.is_visible) and **Datastream Data Visibility** (datastream.is_data_visible) will automatically be set to private as well. However, if the site is public, you can still control the visibility of each datastream and its data individually.
