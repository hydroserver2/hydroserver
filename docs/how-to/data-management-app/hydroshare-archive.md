# How to Archive Data to HydroShare

Data archival to HydroShare is available at the site level from the details page of each site. By default, all buttons related to HydroShare are disabled. To enable HydroShare archival, a site admin must enable HydroShare OAuth logins on the HydroServer instance. Next, navigate to the profile page and connect your HydroServer account to HydroShare via OAuth by clicking the `Connect to HydroShare` button. The button will only appear if HydroShare is registered as an OAuth provider on the server.

Once your accounts have been linked, you'll see a new `Configure HydroShare Archival` button on the site details page of each site you own just below the site map. Clicking that will open up a form which will allow you to either create a new HydroShare resource or link your site to an existing resource.

::: warning File Overwriting
Each time the archival process is triggered for a site, HydroShare will overwrite existing resource files with the same names in the HydroServer directory. For example if you archive Datastream_1 and Datastream_2, then go back and only archive Datastream_1 again, the current Datastream_1 file in HydroShare will be overwritten, but the Datastream_2 file will remain as it was.  
:::

### What Gets Archived and How

When a site is archived to HydroShare, the system generates a CSV file for each selected datastream for that site and saves it in a directory with the name specified on the HydroShare archival form (HydroShare by default). The file structure is as follows:

```plaintext
HydroShare Resource/
└── Site folder name (default: "HydroServer")/
    ├── Processing Level 1 ("Raw Data")/
    │   ├── Datastream 1.csv
    │   └── Datastream 2.csv
    └── Processing Level 2 ("Quality Controlled Data")/
        ├── Datastream 3.csv
        └── Datastream 4.csv
```

Each datastream.csv file will contain all metadata related to the datastream in a comment block followed by the time series data of that datastream.
