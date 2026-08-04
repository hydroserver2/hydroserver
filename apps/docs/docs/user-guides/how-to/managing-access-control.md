# Managing Access Control

HydroServer's access control is role-based and set at the Workspace level. The person who creates the workspace is automatically the owner. That user can then share the workspace with any other HydroServer user as a collaborator. Unless workspace creation has been disabled by a HydroServer administrator, users can create multiple workspaces and can be a collaborator on any number of workspaces.

## Workspace and Content Ownership

Ownership of resources in HydroServer is user-centric, meaning that individual user accounts own the sites, metadata, and datastreams within a workspace. A user may be associated with an organization, but it is the user's account that maintains ownership of and control over the data. 

All resources in HydroServer (monitoring sites, metadata, datastreams, observations) are handled within the context of a workspace. When you want to create a new site, you first have to decide which workspace it will belong to. It will inherit all of the permissions of that workspace.

## User Roles

Each collaborator on a workspace is assigned a role. A role is a set of permissions configurable at the resource level. By default, HydroServer deploys with owner, editor, and viewer roles, but an administrator can configure additional roles if needed. The following table gives an overview of permissions associated with HydroServer's primary roles:

| Permission                                              | Owner | Editor | Viewer |
| ------------------------------------------------------- | ----- | ------ | ------ |
| Rename, transfer, edit privacy of workspace             | Yes   | No     | No     |
| Invite new workspace collaborators                      | Yes   | Yes    | No     |
| Create, update, delete sites, datastreams, and metadata | Yes   | Yes    | No     |
| Set up SDL to stream observations to datastreams        | Yes   | Yes    | No     |
| Set up Job Orchestration System tasks                   | Yes   | Yes    | No     |
| View public and private data within workspace           | Yes   | Yes    | Yes    |

## Adding Collaborators to a Workspace

To add a collaborator, open **Manage workspaces**, select the workspace, and open the **Collaborators** tab.

<img src="/data-management-app/workspace-access-control.png" alt="Workspace access control dialog" class="img-white-bg">

If your workspace is new and you are the owner, you will be the only member. Click **Add collaborator**, enter the collaborator's email address, choose an available role, and click **Add collaborator** again to save.

**NOTE**: A person must have a HydroServer user account affiliated with their email address before you can add them as a collaborator on a workspace.

Use the actions in a collaborator's row to edit their role or remove them from the workspace.

## Service Accounts and API Keys

Sometimes you want to provide access to a workspace without using a person's username and password. HydroServer uses service accounts for these automated clients. Each service account has its own API key and receives permissions through a workspace role.

API keys are unique secrets that let remote systems connect to HydroServer. Assign the service account the minimum permissions it needs, such as the Data Loader role for uploading observations.

To create one, open **Manage workspaces**, select the workspace, choose **Service accounts**, and click **Create service account**. Give it a name and description, assign a role, and save.

<img src="/data-management-app/api-keys.png" alt="Create API key" class="img-white-bg">

The generated API key is shown once. Copy it immediately and store it securely. If it is lost, regenerate the service account's key; the previous key will stop working.

<img src="/data-management-app/api-key-created.png" alt="Created API key" class="img-white-bg">

## Granular Data Visibility

In addition to HydroServer's workspace level, role-based access control, workspace collaborators can control several visibility settings that control what public HydroServer users see. Public users are those who are not logged in or those who are logged in but not a collaborator on a workspace.

By default, workspaces, sites, and datastreams are public. However, each has a visibility setting that can make them private.

1. **Workspace Privacy**: This setting determines whether a workspace is private or public. If your workspace is private, all sites, datastreams, and associated metadata will only be accessible to the workspace owner and collaborators. You can set the privacy of your workspace when it is created or using the 'Workspace access control' window accessed by clicking on the blue lock icon next to the workspace in the manage workspaces table.

2. **Site Privacy**: This setting determines whether your monitoring site is private or public. If you set your site to private, it means that only the workspace owners and collaborators can view the site and all associated datastreams through the website or API. This is like having a closed folder that only selected people can open. This allows users to set some sites as public and others as private within a public workspace. Site privacy can be set when creating a site or by clicking the 'Access control' button on the site's landing page.

3. **Datastream Privacy**: This setting is about who can see a specific datastream at your site. Even if your site is public, you might want to keep certain datastreams of that site private. When this setting is on, it means that only the workspace owners and collaborators can view this particular datastream's details and data. Datastream privacy can be set using the buttons to the right of the datastream on the site's landing page.

4. **Datastream Data Visibility**: This is a convenience setting for controlling visibility of data in the Data Management Web Application. When a datastream is public, its metadata will be visible to the public. However this setting enables datastream observations to be hidden. **Note**: Observations can still be retrieved by anyone through the SensorThings API regardless of this setting.

These privacy settings work in a hierarchical, conditional manner:

If you set the **Site Privacy** to private (thing.is_private), then both **Datastream Visibility** (datastream.is_visible) and **Datastream Data Visibility** (datastream.is_data_visible) will automatically be set to private as well. However, if the site is public, you can still control the visibility of each datastream and its data individually.
