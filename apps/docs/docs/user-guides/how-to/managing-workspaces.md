# Managing Workspaces

A workspace is a primary organizer of content in HydroServer. Think of it as a shared space or folder within which you can create monitoring sites, metadata, and observational data. Workspaces can represent a user, a group of users, a geographic area like a watershed, an observatory site, project, etc. 

Workspaces are used to organize content and to control access to data and metadata. To create a workspace in HydroServer, you must first be logged in.

**NOTE**: By default, workspace creation is enabled for all users when HydroServer is deployed. If needed, a HydroServer administrator can disable workspace creation entirely - e.g., in the case of a HydroServer that represents data for a particular organization like the [Logan River Observatory](https://lro.hydroserver.org) for which creation of new workspaces is not required or desired. Or an administrator can enable workspace creation for certain users.

## Creating a New Workspace

Click **Manage workspaces** in the main navigation at the top of the page. The page lists the workspaces you own or collaborate on in a sidebar on the left. Selecting a workspace shows its details in tabs: **Overview**, **Collaborators**, **Service accounts**, **Metadata**, **Privacy**, and, for the owner, **Ownership**.

<img src="/data-management-app/manage-workspaces.png" alt="Manage workspaces" class="img-white-bg">

Click the **Add workspace** (+) button at the top of the workspaces sidebar. Give your workspace a meaningful name that is descriptive of what it will contain. You can also check 'Make this workspace private'. Click the 'Save' button to create the workspace.

<img src="/data-management-app/create-workspace.png" alt="Create workspace dialog" class="img-white-bg">

**NOTE**: Making your workspace private means that only you and specific HydroServer users that you add to the workspace as collaborators will be able to see any of the content within that workspace. 

Your new workspace now appears in the workspaces sidebar. To rename it later, click the pencil button next to its name in the sidebar. To change its privacy, select the workspace and open the **Privacy** tab.