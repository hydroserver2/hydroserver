# Part 2: Creating Your First Datastream

Now that your site is created, we'll next define a new datastream to specify what kind of data we'll be loading in the next step. If you're not already on the site details page of your new site, open **Browse monitoring sites**, select your site in the panel, and click **View details**.

Near the bottom of the site details page, there will be an empty datastreams table which will work the same as the sites table you saw before. Click 'Add new datastream' to open the datastream creation modal.

<img src="/hydroserver-101/datastream-table.png" alt="datastream table" class="img-white-bg">

## Create linked metadata

Fill out the new datastream form starting with the 'Linked metadata' fields. For the 'Method' and 'Observed Property' fields, click the green plus + button to the right and populate the fields for the new modal that displays on screen. Submitting this form will create new workspace metadata that can be reused for any datastream in this workspace.

If you'd like to follow along exactly, we'll be creating a datastream that represents an Onset HOBO air temperature sensor which collects the daily high temperature. Fill the form out with the following fields:

**Method**

- Type:
  Instrument Deployment
- Name:
  Onset HOBO SD-TEMP
- Definition:
  _leave blank_
- Code:
  hobo-sd-temp
- Description:
  Temperature sensor capable of measuring air temperature (°C), compatible with HOBO dataloggers.
- Sensor Model Manufacturer:
  Onset HOBO
- Sensor Model:
  SD‑TEMP
- Sensor Model Definition:
  https://www.onsetcomp.com/products/sensors/tmcx-hd

**Observed Property**

- name: Temperature
- definition: http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=VariableNameCV
- description: Originally from the CUAHSI HIS VariableNameCV. See: http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=VariableNameCV.
- type: Hydrology
- code: temp

<img src="/hydroserver-101/sensor-form.png" alt="sensor form" class="img-white-bg">

## Specify datastream metadata

Next, for 'Unit' and 'Processing Level', we'll use variables that were defined at the system level by an admin of playground.hydroserver.org. These values are available for all workspaces within the Playground instance because they were defined by an administrator as system-level metadata. For unit, type in 'degree celsius' and find it in the list. For processing level, select level-0, Raw Data.

For the rest of the fields, we'll do the following:

- Medium: Air
- Status: Complete
- Aggregation Statistic: Maximum
- No Data Value: -9999
- Time Aggregation Interval: 1 day
- Intended Time Spacing: 1 day

After filling out all fields except the name and description, click the two 'auto-fill from form' buttons to generate a name and description from the other fields in the form. Then, click 'Create Datastream'.

<img src="/hydroserver-101/new-datastream.png" alt="new datastream" class="img-white-bg">

Your new datastream will appear on the site datastreams table. You've now finished creating the metadata for a datastream, and we're now ready to load some data into this datastream!
