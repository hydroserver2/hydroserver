# HydroServer Web Application

The `HydroServer Web Application` is designed to allow a user to conveniently define, load, and manage their hydrologic data stored in HydroServer as well as view and download public data provided by other users. This page acts as a guide of how to navigate the website and setup your first [`site.`](terminology.md#sites)

The [playground instance](getting-started.md#explore-our-playground-instance) is live at:

https://beta.hydroserver2.org

## Browse Public Sites

Publicly available sites can be found at the [`Browse Monitoring Sites`](https://beta.hydroserver2.org/browse) page. There you'll see a map with markers pointing to their locations. Selecting a marker will populate an info window with some basic information and allow you to navigate to the `Site Details` page for that site where you'll see the associated [`metadata`](terminology.md#site-metadata), [`datastreams`](terminology.md#datastreams), and [`observations`](terminology.md#observations) (data) in sparkline plots.

## Creating An Account

All of the software for HydroServer is free and open source, so creating an account is as simple as inputting and email and password along with some information that allows users to contact one another in order to facilitate better collaboration, and [`organization information`](terminology.md#site-ownership) if the user would like be associated with one.

::: tip
All information you put in the account form will be visible to the other users of this system, so make sure you're only disclosing information you're comfortable sharing.
:::

## Registering a New Site

After creating an account and verifying your email, you'll be able to navigate to the [`My Sites`](https://beta.hydroserver2.org/sites) page, where you'll see an empty map that will be populated with your sites as you create them. You'll see a button labeled `+ REGISTER A NEW SITE` which will open a modal window for inputting the location and details of your site.

### Manage Your Sites

Once a site is created, you'll be able to navigate to the `Site Details` page either from clicking the newly created marker on the map, or the entry in the `My Registered Sites` table. From there, you'll see various buttons for managing the site details, access control, and datastreams for the site.

## Adding a Datastream to Your Site

From the `Site Details` page of your newly created site, click the `+ Add New Datastream` button. This will open a form allowing you to specify [`the metadata`](terminology.md#1-direct-metadata) for the new [`datastream`](terminology.md#datastreams).

::: tip
If you plan on creating a large number of sites and datastreams, it may be faster to first navigate to the [`Data Management -> Manage Metadata `](https://beta.hydroserver2.org/metadata) page and define all of the [`Units, Sensors, Observed Properties, etc.`](terminology.md#2-linked-metadata) you plan on using up front.
:::

Repeat this process for as many datastreams you need to accurately define your site and as many sites as you need to describe your data. In the following [`Loading Data`](loading-data.md) section, you'll learn how to download and configure the `Streaming Data Loader Desktop App` in order to automatically upload data into your newly created datastreams.

## Managing Your Datastreams

All datastream management is done through the `Actions` column of the `Datastreams Available at this Site Table` on the `Site Details` page of the site you'd like to manage the datastreams for.
Selecting the actions icon of a specific datastream will allow you to edit or delete the datastream, or download its data in CSV format.
