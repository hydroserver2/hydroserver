# Job Orchestration System
## Data Transformation Tasks
## 1. Create an Aggregation Task

Aggregation tasks are used to summarize high-frequency data into lower-frequency data. For example, an aggregation task can convert hourly or subdaily discharge data into daily average discharge values. This is useful when users want to reduce detailed time-series data into a simpler summary datastream for reporting, analysis, or visualization.

Before creating an aggregation task, make sure the output datastream already exists. The aggregation task needs a place to save the processed results. For example, if the goal is to convert 15-minute discharge data into daily average discharge data, create a new datastream first for the daily average discharge output.

<img src="/Aggregation/1OutputDatastream.png" alt="Output datastream created for daily average discharge" width="550">

After the output datastream is ready, go to the **Job Orchestration** page and select **Aggregations & products** from the left menu. Click **Aggregation** to create a new aggregation task.

<img src="/Aggregation/2Aggregation.png" alt="Open the Aggregations and products section and add an aggregation task" width="550">

Aggregation tasks are used to summarize higher-frequency data into lower-frequency data. In this example, the input datastream contains discharge observations recorded every 15 minutes, and the task calculates one daily average discharge value. The input datastream is `BC_CONF_A Discharge (cfs) - Provisional data`, and the output datastream is `Discharge at BC_CONF_A with average daily discharge`.

In the task form, enter a clear task name, such as `BC_CONF_A Discharge (15 mins to daily average)`. Then choose whether the task should run manually or on a schedule. In this example, the task is scheduled to run every `1 Hour`. The schedule controls how often HydroServer checks and runs the task, but it does not control the output time interval.

<img src="/Aggregation/3AggregationTask.png" alt="Create an aggregation task to calculate daily average discharge" width="550">

Next, select the input and output datastreams. The input datastream is the original 15-minute discharge datastream, and the output datastream is the new daily average discharge datastream. Under **Aggregation Settings**, set the aggregation method to `Mean`. This tells HydroServer to average the available discharge values within each daily time bucket. If you click the drop down button then you will see other methods that you can choose from, which includes Sum, Min, Max, First and Last. You should use whatever option you want to use.

Here, the output interval is set to `1 Day` so HydroServer writes one aggregated value for each day. In this example, the minimum values per bucket is set to `90`, which allows a small number of missing values but prevents HydroServer from creating a daily average when too much data are missing. The timezone is set to `UTC (Default)`, so the daily buckets are calculated using UTC day boundaries.

After the settings are complete, click **Create aggregation task**. The task will appear in the Aggregations & products task list. To test the task immediately, click **Run now**.

<img src="/Aggregation/4Green.png" alt="Run the aggregation task manually" width="550">

After the aggregation task runs successfully, return to the site datastream page and check the output datastream. The new datastream should contain the aggregated daily average values created by the task.

---

## 2. Create an Expression Task

Expression tasks are used to create a new datastream by applying a formula to values from **one existing input datastream**. This is useful when the original data are already stored in HydroServer, but the values need to be converted, adjusted, or recalculated before being used for analysis or reporting. For example, an expression task can be used to convert discharge values from cubic feet per second (`cfs`) to cubic meters per second (`cms`).

An expression task is best for a **one-input, one-output** calculation. It uses the same time spacing as the input datastream, so it is appropriate for simple transformations such as unit conversions. Before creating an expression task, make sure the output datastream already exists in the workspace. The expression task needs a target datastream where HydroServer can save the calculated results. In this example, the input datastream contains daily average discharge values in `cfs`, and the output datastream is created to store the converted daily discharge values in `cms`.

To create an expression task, go to the **Job Orchestration** page and select **Aggregations & products** from the left menu. Then click **Expression**. The expression task form will open.

<img src="/Expression/1Exp_Tab.png" alt="Open the expression task form" width="550">

In the task form, enter a clear task name that describes what the expression will do. In this example, the task is named `Discharge data from cfs to cms` because the task converts discharge values from cubic feet per second to cubic meters per second.

Next, configure the task schedule. In this example, the task is scheduled to run every `1 Day`. The schedule controls how often HydroServer checks for new input data and runs the expression. It does not change the time interval of the data itself.

Select the input datastream and output datastream. The input datastream is the datastream HydroServer will read from, and the output datastream is where HydroServer will write the calculated values.

In this example:

```text
Input datastream: Discharge at BC_CONF_A with average daily discharge
Output datastream: Discharge at BC_CONF_A with daily discharge in cms
```

In the formula section, HydroServer represents each input value as the variable `x`. Since `1 cfs = 0.0283168 cms`, the formula is written as:

```text
x*0.0283168
```

<img src="/Expression/2Exp_Fillup.png" alt="Expression task form filled out" width="550">

> **Note:** If a calculation requires more than one input datastream, use a **Derivation** task instead of an Expression task.

---

## 3. Create a Derivation Task

Derivation tasks are used when a calculated output depends on **multiple input datastreams**. Each input datastream is assigned a variable name, such as `a`, `b`, or `c`, and those variables are used together in a formula.

For example, a derivation task can be used to calculate the difference between two temperature datastreams, combine measurements from multiple sensors, or calculate a basin sum from several streamflow datastreams.

Derivation tasks are handled differently from expression tasks because the input datastreams may not have the same timestamps or time spacing. For this reason, HydroServer snaps the output to a user-defined fixed interval and may interpolate input values when needed. Before creating a derivation task, make sure the output datastream already exists in the workspace. The derivation task needs a target datastream where HydroServer can save the calculated results.

To create a derivation task, go to the **Job Orchestration** page and select **Aggregations & products** from the left menu. Then click **Derivation**. The derivation task form will open.

<img src="/Derivation/1Derivation_Task.png" alt="Create a derivation task form" width="550">

In the task form, enter a clear task name that describes what the derivation will calculate. Then choose whether the task should run manually or on a schedule. The schedule controls how often HydroServer checks for new input data and runs the derivation. Next, select the output datastream. This is the datastream where HydroServer will write the calculated results.

Then select the input datastreams that will be used in the formula. Each input datastream must be assigned a variable name. For example, the first input datastream can be assigned the variable `a`, and the second input datastream can be assigned the variable `b`. Additional input datastreams can be added by clicking **Add input**. This allows the formula to use more than two variables if needed.

In the formula section, use the assigned variables to define the calculation. For example, if the goal is to calculate the difference between two input datastreams, the formula could be written as:

```text
a-b
```

In this example:

```text
a = first input datastream
b = second input datastream
a-b = calculated output value
```
---
## 4. Creating a Rating Curve

A rating curve task is used to calculate discharge from water level, stage, or gage-height data. In many monitoring sites, the sensor may measure water level directly, but users may also need discharge values for analysis, visualization, or reporting. A rating curve provides the relationship between water level and discharge, and HydroServer uses this relationship to estimate discharge from the input water-level datastream.

The general workflow is:

```text
stage / gage height → rating curve → discharge
```

Before creating a rating curve task, make sure the required datastreams already exist in the workspace. The input datastream should contain the water level, stage, or gage-height values. The output datastream should be the datastream where HydroServer will save the calculated discharge values. To create a rating curve task, go to the **Job Orchestration** page and select **Aggregations & products** from the left menu. Then click **Rating curve**. This will open the rating curve task form.

<img src="/Rating_Curve/2RC_Task.png" alt="Open the expression task form" width="550">

In the rating curve task form, first enter a clear task name. The task name should describe what the rating curve task will calculate. In this example, the task is named `Rating Curve for BC_CONF_A`.

Next, configure the schedule. The task can be run manually or on a schedule. The schedule controls how often HydroServer checks the input datastream and applies the rating curve. For testing, it may be helpful to run the task manually first and then enable the schedule after confirming that the task works correctly.

After setting the schedule, select the input datastream. The input datastream should be the datastream that contains the water level, stage, or gage-height values. In this example, the input datastream is `BC_CONF_A_WaterLevel_Data`. Then select the output datastream. The output datastream is where HydroServer will save the calculated discharge values from the rating curve. The output datastream should already be created before setting up the rating curve task. In this example, the output datastream is `Rating Curve`.

The next step is to select or create the rating curve. If a rating curve already exists in HydroServer, choose **Select existing rating curve** and select the rating curve that should be used. If a rating curve has not been created yet, choose **Create new rating curve**. When creating a new rating curve, a CSV file must be uploaded. This CSV file provides the reference values HydroServer uses to build the rating curve. The CSV file should contain paired values, usually one column for water level, stage, or gage height, and one column for discharge.

For example, the CSV file may look like this:

<img src="/Rating_Curve/1csv.png" alt="Open the expression task form" width="300">

In this example, `water_level` is the input value and `Discharge` is the output value. HydroServer uses these paired values as the reference relationship between water level and discharge. Based on the uploaded CSV file and the selected fitting method, HydroServer creates a rating curve and applies it to the input datastream.

When preparing the CSV file, make sure the input values are unique. For example, the same `water_level` value should not be repeated in the input column. If duplicate input values are included, HydroServer may show an error such as `Duplicate input_value in points`.

<img src="/Rating_Curve/3Error.png" alt="Open the expression task form" width="550">

If this error appears, edit the CSV file and remove duplicate values from the input column before uploading it again. One way to do this is to open the CSV file in Excel, select the water-level or stage column, and use **Data → Remove Duplicates**. Make sure only the input column is selected when removing duplicates. Then save the file again as a CSV and upload it again.

After uploading the CSV file, enter a rating curve name and description. The rating curve name should clearly describe the site or purpose of the curve. The description can explain what the curve is used for, such as estimating discharge from water-level data. Next, select the fitting method. HydroServer provides multiple fitting method options, so choose the method that best fits the relationship in the CSV file. In this example, the fitting method is set to `Power law`.

After the task name, schedule, input datastream, output datastream, rating curve CSV file, rating curve name, description, and fitting method are complete, click **Create rating curve task**. Once the task runs successfully, go to the output datastream and open **Visualize data** to view the calculated rating curve output. The plot shows the discharge values calculated from the input water-level or gage-height data using the rating curve.

<img src="/Rating_Curve/4RC.png" alt="Open the expression task form" width="550">







