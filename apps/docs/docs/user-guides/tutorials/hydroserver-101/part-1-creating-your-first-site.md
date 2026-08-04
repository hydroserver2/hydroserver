# Part 1: Creating Your First Site

## Create an account on our playground instance

Go to [`https://playground.hydroserver.org`](https://playground.hydroserver.org).

Click the 'Sign up' button on the top right of the page to create a user account for Playground. Note that user information is public. Everyone else on playground will see your account information, so choose information you're OK with sharing.

## Create a workspace

After verifying your email address, open **Manage workspaces** from the main navigation.

Before creating your first site, you'll need to create a workspace for that site to go in. Most of HydroServer's access control happens at the workspace level, so resources like sites and datastreams belong to a workspace.

Click 'Add workspace' and give your workspace a name. Make it unique since everyone's workspace will be visible. If you don't want other users to see your workspace, you can check the 'Make this workspace private' button. This will hide the workspace and everything in it from all public users of HydroServer.

<img src="/hydroserver-101/add-workspace.png" alt="Modal for adding workspace" class="img-white-bg">

## Create your site

After the workspace is successfully created, open **Browse monitoring sites** from the main navigation. Expand the monitoring-sites panel if it is collapsed, then click the **Register a monitoring site** (+) button. Choose the workspace where the site should be registered.

The button opens the Register/Edit a site modal window. Click anywhere on the map and it will create a new map marker and automatically populate the location form fields. You can also type values into the 'Site Location' fields if you know them already. Fill out the rest of the form with the metadata for your site and click save.

<img src="/hydroserver-101/site-form.png" alt="Site form" class="img-white-bg">

On the **Browse monitoring sites** page, your new site will appear on the map and in the sites panel. You can search by its name or site code, or filter the list by workspace, site type, and additional metadata.

Select the new site in the panel, then click **View details**. The Site Details page is where you can edit the site's information and access control, delete it, or add new datastreams as you'll see in the next part of this tutorial.

<img src="/hydroserver-101/site-details.png" alt="site details page" class="img-white-bg">
